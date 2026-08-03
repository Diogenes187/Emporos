CREATE TABLE senc_damage_location_hit_receipt (
    damage_location_hit_receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    mount_attack_declaration_id bigint NOT NULL,
    group_order smallint NOT NULL,
    hit_order smallint NOT NULL CHECK (hit_order BETWEEN 1 AND 3),
    target_ship_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    routing_column text NOT NULL CHECK (routing_column IN ('external','internal','small-craft')),
    rolled_location text NOT NULL,
    applied_location text NOT NULL,
    system_instance smallint,
    effect_code text NOT NULL,
    hull_before smallint NOT NULL,
    hull_after smallint NOT NULL,
    structure_before smallint NOT NULL,
    structure_after smallint NOT NULL,
    armor_before smallint NOT NULL,
    armor_after smallint NOT NULL,
    ship_version_before bigint NOT NULL,
    ship_version_after bigint NOT NULL CHECK (ship_version_after=ship_version_before+1),
    system_hits_before smallint,
    system_hits_after smallint,
    secondary_resolution_required boolean NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (mount_attack_declaration_id,group_order,hit_order),
    FOREIGN KEY (mount_attack_declaration_id,group_order)
        REFERENCES senc_damage_location_group_roll(mount_attack_declaration_id,group_order),
    FOREIGN KEY (target_ship_id,campaign_id) REFERENCES ship_ship(ship_id,campaign_id),
    CHECK (hull_after BETWEEN 0 AND hull_before),
    CHECK (structure_after BETWEEN 0 AND structure_before),
    CHECK (armor_after BETWEEN 0 AND armor_before),
    CHECK ((system_hits_before IS NULL)=(system_hits_after IS NULL)),
    CHECK (system_instance IS NULL OR system_instance>0)
);

CREATE FUNCTION senc_apply_next_damage_location_hit(
    p_mount_attack_declaration_id bigint,
    p_system_instance smallint DEFAULT NULL
) RETURNS bigint LANGUAGE plpgsql AS $$
DECLARE
    final senc_mount_damage_final_receipt%ROWTYPE; roll_row record; ship_row record;
    location_row rule_space_combat_hit_location%ROWTYPE; state_row record;
    expected_group smallint; expected_hit smallint; route text; rolled text; applied text;
    effect text; overflow text; instance_value smallint; state_before smallint; state_after smallint;
    hull_after smallint; structure_after smallint; armor_after smallint; secondary boolean:=false;
    receipt_id bigint; damage_id bigint; new_status text; new_attack_dm smallint:=0; new_sensor_dm smallint:=0;
BEGIN
    SELECT * INTO STRICT final FROM senc_mount_damage_final_receipt
    WHERE mount_attack_declaration_id=p_mount_attack_declaration_id FOR UPDATE;
    IF final.damage_status<>'queued' OR NOT EXISTS (
        SELECT 1 FROM senc_damage_location_roll_set_receipt
        WHERE mount_attack_declaration_id=p_mount_attack_declaration_id
    ) THEN RAISE EXCEPTION 'Location hits require a complete queued location-roll set' USING ERRCODE='23514'; END IF;

    SELECT groups.group_order,
           count(receipt.damage_location_hit_receipt_id)::smallint+1
    INTO expected_group,expected_hit
    FROM senc_damage_location_group_roll groups
    LEFT JOIN senc_damage_location_hit_receipt receipt
      ON receipt.mount_attack_declaration_id=groups.mount_attack_declaration_id
     AND receipt.group_order=groups.group_order
    WHERE groups.mount_attack_declaration_id=p_mount_attack_declaration_id
    GROUP BY groups.group_order,groups.hit_multiplicity
    HAVING count(receipt.damage_location_hit_receipt_id)<groups.hit_multiplicity
    ORDER BY groups.group_order LIMIT 1;
    IF expected_group IS NULL THEN RAISE EXCEPTION 'All location hits are already applied' USING ERRCODE='23514'; END IF;

    SELECT * INTO STRICT roll_row FROM senc_damage_location_group_roll
    WHERE mount_attack_declaration_id=p_mount_attack_declaration_id AND group_order=expected_group;
    SELECT ship.*,class.hull_tons INTO STRICT ship_row
    FROM senc_mount_attack_declaration declaration
    JOIN senc_vessel vessel ON vessel.senc_vessel_id=declaration.target_vessel_id
    JOIN ship_ship ship USING (ship_id)
    JOIN ship_class class USING (ship_class_rule_id)
    WHERE declaration.mount_attack_declaration_id=p_mount_attack_declaration_id FOR UPDATE OF ship;
    SELECT * INTO STRICT location_row FROM rule_space_combat_hit_location WHERE roll_total=roll_row.roll_total;

    IF ship_row.hull_tons<100 THEN route:='small-craft'; rolled:=location_row.small_craft_location;
    ELSIF ship_row.hull_current>0 THEN route:='external'; rolled:=location_row.external_vessel_location;
    ELSE route:='internal'; rolled:=location_row.internal_vessel_location; END IF;
    applied:=rolled;
    IF applied='hull' AND ship_row.hull_current=0 THEN applied:=location_row.internal_vessel_location; route:='internal'; END IF;
    IF applied='armor' AND ship_row.armor_current=0 THEN
        applied:='hull';
        IF ship_row.hull_current=0 THEN applied:=location_row.internal_vessel_location; route:='internal'; END IF;
    END IF;

    hull_after:=ship_row.hull_current; structure_after:=ship_row.structure_current; armor_after:=ship_row.armor_current;
    instance_value:=CASE WHEN applied IN ('turret','bay') THEN coalesce(p_system_instance,1) ELSE 1 END;
    state_before:=NULL; state_after:=NULL;

    IF applied IN ('turret','bay','j-drive','m-drive','power-plant','sensors','bridge','fuel','hold') THEN
        SELECT hit_count INTO state_before FROM senc_ship_system_damage_state
        WHERE ship_id=ship_row.ship_id AND system_code=applied AND system_instance=instance_value FOR UPDATE;
        state_before:=coalesce(state_before,0);
        IF state_before>=3 THEN
            SELECT overflow_location_code INTO STRICT overflow FROM rule_space_combat_location_effect effect_row
            JOIN rule_rule rule ON rule.rule_id=effect_row.hit_location_rule_id
            WHERE rule.rule_code='combat.space.hit-locations' AND location_code=applied AND hit_ordinal=4;
            applied:=overflow; state_after:=state_before;
        ELSE state_after:=state_before+1; END IF;
    END IF;

    IF applied='hull' THEN
        IF hull_after>0 THEN hull_after:=hull_after-1; effect:='reduce-hull';
        ELSE applied:=location_row.internal_vessel_location; route:='internal'; END IF;
    END IF;
    IF applied='structure' THEN structure_after:=greatest(0,structure_after-1); effect:='reduce-structure'; END IF;
    IF applied='armor' THEN armor_after:=greatest(0,armor_after-1); effect:='reduce-armor'; END IF;
    IF effect IS NULL AND applied='crew' THEN effect:='roll-crew-damage'; secondary:=true; END IF;
    IF effect IS NULL THEN
        SELECT effect_code,attack_dm,sensor_dm INTO STRICT effect,new_attack_dm,new_sensor_dm
        FROM rule_space_combat_location_effect effect_row JOIN rule_rule rule ON rule.rule_id=effect_row.hit_location_rule_id
        WHERE rule.rule_code='combat.space.hit-locations' AND location_code=applied
          AND hit_ordinal=least(coalesce(state_after,1),4);
        secondary:=effect IN ('crew-normal-hit','crew-radiation-hit','minor-leak-1d6-tons-hour','destroy-1d6-times-10-percent');
    END IF;

    UPDATE ship_ship SET hull_current=hull_after,structure_current=structure_after,armor_current=armor_after,
      concurrency_version=ship_row.concurrency_version+1,
      lifecycle_status=CASE WHEN structure_after=0 THEN 'destroyed' ELSE lifecycle_status END,
      ended_at=CASE WHEN structure_after=0 THEN coalesce(ended_at,clock_timestamp()) ELSE ended_at END
    WHERE ship_id=ship_row.ship_id;
    IF state_before IS NOT NULL AND state_after>state_before THEN
        new_status:=CASE state_after WHEN 1 THEN 'damaged' WHEN 2 THEN 'disabled' ELSE 'destroyed' END;
        INSERT INTO senc_ship_system_damage_state(ship_id,campaign_id,system_code,system_instance,hit_count,system_status,attack_dm,sensor_dm)
        VALUES(ship_row.ship_id,ship_row.campaign_id,rolled,instance_value,state_after,new_status,new_attack_dm,new_sensor_dm)
        ON CONFLICT(ship_id,system_code,system_instance) DO UPDATE SET hit_count=EXCLUDED.hit_count,system_status=EXCLUDED.system_status,
          attack_dm=CASE WHEN EXCLUDED.hit_count=1 THEN EXCLUDED.attack_dm ELSE senc_ship_system_damage_state.attack_dm END,
          sensor_dm=CASE WHEN EXCLUDED.hit_count=1 THEN EXCLUDED.sensor_dm ELSE senc_ship_system_damage_state.sensor_dm END,
          concurrency_version=senc_ship_system_damage_state.concurrency_version+1,updated_at=clock_timestamp();
    END IF;
    IF hull_after<ship_row.hull_current THEN INSERT INTO ship_damage(ship_id,campaign_id,target_kind,damage_points,description)
      VALUES(ship_row.ship_id,ship_row.campaign_id,'hull',1,'Space combat location hit') RETURNING ship_damage_id INTO damage_id; END IF;
    IF structure_after<ship_row.structure_current THEN INSERT INTO ship_damage(ship_id,campaign_id,target_kind,damage_points,description)
      VALUES(ship_row.ship_id,ship_row.campaign_id,'structure',1,'Space combat location hit') RETURNING ship_damage_id INTO damage_id; END IF;

    INSERT INTO senc_damage_location_hit_receipt(mount_attack_declaration_id,group_order,hit_order,target_ship_id,campaign_id,
      routing_column,rolled_location,applied_location,system_instance,effect_code,hull_before,hull_after,structure_before,structure_after,
      armor_before,armor_after,ship_version_before,ship_version_after,system_hits_before,system_hits_after,secondary_resolution_required)
    VALUES(p_mount_attack_declaration_id,expected_group,expected_hit,ship_row.ship_id,ship_row.campaign_id,route,rolled,applied,
      CASE WHEN rolled IN('turret','bay') THEN instance_value END,effect,ship_row.hull_current,hull_after,ship_row.structure_current,structure_after,
      ship_row.armor_current,armor_after,ship_row.concurrency_version,ship_row.concurrency_version+1,state_before,state_after,secondary)
    RETURNING damage_location_hit_receipt_id INTO receipt_id;
    RETURN receipt_id;
END $$;

CREATE FUNCTION senc_reject_damage_location_hit_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Applied damage location hit receipts are immutable'; END $$;
CREATE TRIGGER senc_damage_location_hit_immutable BEFORE UPDATE OR DELETE ON senc_damage_location_hit_receipt
FOR EACH ROW EXECUTE FUNCTION senc_reject_damage_location_hit_mutation();
