CREATE TABLE senc_offensive_sand_damage_receipt (
    mount_weapon_attack_check_id bigint PRIMARY KEY REFERENCES senc_mount_weapon_attack_check(mount_weapon_attack_check_id),
    target_ship_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    fixed_damage smallint NOT NULL CHECK (fixed_damage=1),
    armor_snapshot smallint NOT NULL CHECK (armor_snapshot>=0),
    post_armor_damage smallint NOT NULL CHECK (post_armor_damage BETWEEN 0 AND 1),
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    FOREIGN KEY (target_ship_id,campaign_id) REFERENCES ship_ship(ship_id,campaign_id)
);

CREATE FUNCTION senc_validate_offensive_sand_damage() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE attack record; target record; special rule_space_combat_special_weapon%ROWTYPE;
BEGIN
 SELECT check_row.hit,check_row.weapon_rule_id,declaration.target_vessel_id,declaration.campaign_id,declaration.range_band_code
 INTO STRICT attack FROM senc_mount_weapon_attack_check check_row
 JOIN senc_mount_attack_declaration declaration USING(mount_attack_declaration_id)
 WHERE check_row.mount_weapon_attack_check_id=NEW.mount_weapon_attack_check_id;
 SELECT row.* INTO STRICT special FROM rule_space_combat_special_weapon row
 JOIN rule_rule rule ON rule.rule_id=row.rule_id
 WHERE rule.rule_code='combat.space.special-weapons' AND row.weapon_rule_id=attack.weapon_rule_id;
 SELECT ship.ship_id,ship.armor_current INTO STRICT target FROM senc_vessel vessel
 JOIN ship_ship ship USING(ship_id) WHERE vessel.senc_vessel_id=attack.target_vessel_id;
 IF NOT attack.hit OR special.offensive_fixed_damage IS NULL
  OR attack.range_band_code<>special.offensive_maximum_range
  OR NEW.target_ship_id<>target.ship_id OR NEW.campaign_id<>attack.campaign_id
  OR NEW.fixed_damage<>special.offensive_fixed_damage OR NEW.armor_snapshot<>target.armor_current
  OR NEW.post_armor_damage<>greatest(0,special.offensive_fixed_damage-target.armor_current) THEN
  RAISE EXCEPTION 'Offensive sand damage must match a successful Close-range sandcaster hit, fixed damage, target, and armor' USING ERRCODE='23514';
 END IF; RETURN NEW;
END $$;
CREATE TRIGGER senc_offensive_sand_damage_valid BEFORE INSERT ON senc_offensive_sand_damage_receipt
FOR EACH ROW EXECUTE FUNCTION senc_validate_offensive_sand_damage();

CREATE OR REPLACE FUNCTION senc_validate_mount_damage_final() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE expected_count integer; actual_count integer; total integer; singles integer; doubles integer; triples integer; excess integer;
BEGIN
 SELECT count(*) INTO expected_count FROM senc_mount_weapon_attack_check check_row
 JOIN ship_weapon_definition weapon USING(weapon_rule_id)
 WHERE check_row.mount_attack_declaration_id=NEW.mount_attack_declaration_id AND check_row.hit
  AND (weapon.damage_dice_count IS NOT NULL OR weapon.weapon_kind='sandcaster');
 SELECT count(*),coalesce(sum(source.post_armor_damage),0) INTO actual_count,total FROM (
  SELECT final.post_armor_damage FROM senc_mount_weapon_attack_check check_row
  JOIN senc_weapon_damage_final_receipt final USING(mount_weapon_attack_check_id)
  WHERE check_row.mount_attack_declaration_id=NEW.mount_attack_declaration_id
  UNION ALL
  SELECT sand.post_armor_damage FROM senc_mount_weapon_attack_check check_row
  JOIN senc_offensive_sand_damage_receipt sand USING(mount_weapon_attack_check_id)
  WHERE check_row.mount_attack_declaration_id=NEW.mount_attack_declaration_id
 ) source;
 IF NEW.net_damage<=44 THEN SELECT single_hit_groups,double_hit_groups,triple_hit_groups INTO singles,doubles,triples
  FROM rule_space_combat_damage_band WHERE damage_range @> NEW.net_damage;
 ELSE excess:=NEW.net_damage-44; singles:=floor(excess/3); doubles:=floor(excess/6); triples:=2; END IF;
 IF expected_count<>actual_count OR total<>NEW.post_armor_damage_total OR NEW.screen_reduction<>0
  OR NEW.single_hit_groups<>singles OR NEW.double_hit_groups<>doubles OR NEW.triple_hit_groups<>triples THEN
  RAISE EXCEPTION 'Mount damage final receipt fails complete weapon aggregation or damage-band recomputation' USING ERRCODE='23514';
 END IF; RETURN NEW;
END $$;

CREATE FUNCTION senc_require_forced_internal_route() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF EXISTS (SELECT 1 FROM senc_damage_location_group_roll group_row
  WHERE group_row.mount_attack_declaration_id=NEW.mount_attack_declaration_id
   AND group_row.group_order=NEW.group_order AND group_row.forced_internal)
  AND NEW.routing_column<>'internal' THEN
  RAISE EXCEPTION 'Meson damage must use the internal vessel location column' USING ERRCODE='23514';
 END IF; RETURN NEW;
END $$;
CREATE TRIGGER senc_damage_location_forced_internal_guard BEFORE INSERT ON senc_damage_location_hit_receipt
FOR EACH ROW EXECUTE FUNCTION senc_require_forced_internal_route();

CREATE FUNCTION senc_apply_next_forced_internal_damage_hit(
 p_mount_attack_declaration_id bigint,p_system_instance smallint DEFAULT NULL
) RETURNS bigint LANGUAGE plpgsql AS $$
DECLARE final senc_mount_damage_final_receipt%ROWTYPE; group_row record; ship_row ship_ship%ROWTYPE;
 location_row rule_space_combat_hit_location%ROWTYPE; group_value smallint; hit_value smallint;
 rolled text; applied text; effect text; overflow text; instance_value smallint;
 state_before smallint; state_after smallint; structure_after smallint; secondary boolean:=false;
 attack_dm smallint:=0; sensor_dm smallint:=0; status text; receipt_id bigint; damage_id bigint;
BEGIN
 SELECT * INTO STRICT final FROM senc_mount_damage_final_receipt
 WHERE mount_attack_declaration_id=p_mount_attack_declaration_id FOR UPDATE;
 IF final.damage_status<>'queued' OR NOT EXISTS(SELECT 1 FROM senc_damage_location_roll_set_receipt
  WHERE mount_attack_declaration_id=p_mount_attack_declaration_id) THEN
  RAISE EXCEPTION 'Forced-internal hits require a complete queued location-roll set' USING ERRCODE='23514'; END IF;
 SELECT groups.group_order,count(hit.damage_location_hit_receipt_id)::smallint+1
 INTO group_value,hit_value FROM senc_damage_location_group_roll groups
 LEFT JOIN senc_damage_location_hit_receipt hit ON hit.mount_attack_declaration_id=groups.mount_attack_declaration_id
  AND hit.group_order=groups.group_order
 WHERE groups.mount_attack_declaration_id=p_mount_attack_declaration_id
 GROUP BY groups.group_order,groups.hit_multiplicity,groups.forced_internal
 HAVING count(hit.damage_location_hit_receipt_id)<groups.hit_multiplicity
 ORDER BY groups.group_order LIMIT 1;
 IF group_value IS NULL THEN RAISE EXCEPTION 'All location hits are already applied' USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT group_row FROM senc_damage_location_group_roll
 WHERE mount_attack_declaration_id=p_mount_attack_declaration_id AND group_order=group_value;
 IF NOT group_row.forced_internal THEN RAISE EXCEPTION 'The next damage group is not forced internal' USING ERRCODE='23514'; END IF;
 SELECT ship.* INTO STRICT ship_row FROM senc_mount_attack_declaration declaration
 JOIN senc_vessel vessel ON vessel.senc_vessel_id=declaration.target_vessel_id
 JOIN ship_ship ship USING(ship_id) WHERE declaration.mount_attack_declaration_id=p_mount_attack_declaration_id FOR UPDATE OF ship;
 SELECT * INTO STRICT location_row FROM rule_space_combat_hit_location WHERE roll_total=group_row.roll_total;
 rolled:=location_row.internal_vessel_location; applied:=rolled; structure_after:=ship_row.structure_current;
 instance_value:=CASE WHEN applied='bay' THEN coalesce(p_system_instance,1) ELSE 1 END;
 IF applied IN('bay','j-drive','power-plant','bridge','hold') THEN
  SELECT hit_count INTO state_before FROM senc_ship_system_damage_state
  WHERE ship_id=ship_row.ship_id AND system_code=applied AND system_instance=instance_value FOR UPDATE;
  state_before:=coalesce(state_before,0);
  IF state_before>=3 THEN SELECT overflow_location_code INTO STRICT overflow
   FROM rule_space_combat_location_effect location_effect JOIN rule_rule rule ON rule.rule_id=location_effect.hit_location_rule_id
   WHERE rule.rule_code='combat.space.hit-locations' AND location_code=applied AND hit_ordinal=4;
   applied:=overflow; state_after:=state_before;
  ELSE
   state_after:=state_before+1;
   SELECT effect_code,location_effect.attack_dm,location_effect.sensor_dm INTO STRICT effect,attack_dm,sensor_dm
   FROM rule_space_combat_location_effect location_effect JOIN rule_rule rule ON rule.rule_id=location_effect.hit_location_rule_id
   WHERE rule.rule_code='combat.space.hit-locations' AND location_code=applied AND hit_ordinal=state_after;
  END IF;
 END IF;
 IF applied='structure' THEN structure_after:=greatest(0,structure_after-1); effect:='reduce-structure'; END IF;
 IF effect IS NULL AND applied='crew' THEN effect:='roll-crew-damage'; secondary:=true; END IF;
 IF effect IS NULL THEN SELECT effect_code INTO STRICT effect FROM rule_space_combat_location_effect location_effect
  JOIN rule_rule rule ON rule.rule_id=location_effect.hit_location_rule_id
  WHERE rule.rule_code='combat.space.hit-locations' AND location_code=applied AND hit_ordinal=1; END IF;
 UPDATE ship_ship SET structure_current=structure_after,concurrency_version=ship_row.concurrency_version+1,
  lifecycle_status=CASE WHEN structure_after=0 THEN 'destroyed' ELSE lifecycle_status END,
  ended_at=CASE WHEN structure_after=0 THEN coalesce(ended_at,clock_timestamp()) ELSE ended_at END
 WHERE ship_id=ship_row.ship_id;
 IF state_before IS NOT NULL AND state_after>state_before THEN
  status:=CASE state_after WHEN 1 THEN 'damaged' WHEN 2 THEN 'disabled' ELSE 'destroyed' END;
  INSERT INTO senc_ship_system_damage_state(ship_id,campaign_id,system_code,system_instance,hit_count,system_status,attack_dm,sensor_dm)
  VALUES(ship_row.ship_id,ship_row.campaign_id,rolled,instance_value,state_after,status,attack_dm,sensor_dm)
  ON CONFLICT(ship_id,system_code,system_instance) DO UPDATE SET hit_count=EXCLUDED.hit_count,system_status=EXCLUDED.system_status,
   attack_dm=CASE WHEN EXCLUDED.hit_count=1 THEN EXCLUDED.attack_dm ELSE senc_ship_system_damage_state.attack_dm END,
   sensor_dm=CASE WHEN EXCLUDED.hit_count=1 THEN EXCLUDED.sensor_dm ELSE senc_ship_system_damage_state.sensor_dm END,
   concurrency_version=senc_ship_system_damage_state.concurrency_version+1,updated_at=clock_timestamp();
 END IF;
 IF structure_after<ship_row.structure_current THEN INSERT INTO ship_damage(ship_id,campaign_id,target_kind,damage_points,description)
  VALUES(ship_row.ship_id,ship_row.campaign_id,'structure',1,'Meson forced-internal location hit') RETURNING ship_damage_id INTO damage_id; END IF;
 INSERT INTO senc_damage_location_hit_receipt(mount_attack_declaration_id,group_order,hit_order,target_ship_id,campaign_id,
  routing_column,rolled_location,applied_location,system_instance,effect_code,hull_before,hull_after,structure_before,structure_after,
  armor_before,armor_after,ship_version_before,ship_version_after,system_hits_before,system_hits_after,secondary_resolution_required)
 VALUES(p_mount_attack_declaration_id,group_value,hit_value,ship_row.ship_id,ship_row.campaign_id,'internal',rolled,applied,
  CASE WHEN rolled='bay' THEN instance_value END,effect,ship_row.hull_current,ship_row.hull_current,ship_row.structure_current,structure_after,
  ship_row.armor_current,ship_row.armor_current,ship_row.concurrency_version,ship_row.concurrency_version+1,state_before,state_after,secondary)
 RETURNING damage_location_hit_receipt_id INTO receipt_id;
 RETURN receipt_id;
END $$;

CREATE TRIGGER senc_offensive_sand_damage_immutable BEFORE UPDATE OR DELETE ON senc_offensive_sand_damage_receipt
FOR EACH ROW EXECUTE FUNCTION senc_reject_special_weapon_mutation();
