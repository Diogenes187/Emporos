CREATE OR REPLACE FUNCTION senc_validate_vessel_initiative_receipt()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    vessel senc_vessel%ROWTYPE;
    hostile_max smallint;
    expected_tactics smallint:=0;
    tactics_scope text;
    tactics_force bigint;
    tactics_vessel bigint;
    pilot_position text;
    pilot_duty text;
    pilot_actor bigint;
    dex_rule bigint;
    dex_value smallint;
    dex_modifier smallint;
BEGIN
    SELECT * INTO STRICT vessel FROM senc_vessel
    WHERE senc_vessel_id=NEW.senc_vessel_id;
    SELECT max(hostile.thrust_current) INTO hostile_max
    FROM senc_vessel hostile
    WHERE hostile.engagement_id=NEW.engagement_id
      AND hostile.force_id<>vessel.force_id
      AND hostile.vessel_status='engaged';
    IF vessel.engagement_id<>NEW.engagement_id
       OR vessel.campaign_id<>NEW.campaign_id
       OR vessel.force_id<>NEW.force_id OR vessel.ship_id<>NEW.ship_id
       OR hostile_max IS NULL
       OR NEW.vessel_thrust_snapshot<>vessel.thrust_current
       OR NEW.highest_hostile_thrust_snapshot<>hostile_max
       OR NEW.higher_thrust_modifier<>(
          CASE WHEN vessel.thrust_current>hostile_max THEN 1 ELSE 0 END
       ) THEN
        RAISE EXCEPTION 'Vessel initiative hostile-Thrust snapshot is inconsistent'
            USING ERRCODE='23514';
    END IF;
    IF NEW.tactics_initiative_receipt_id IS NOT NULL THEN
        SELECT tactics_effect,scope_kind,force_id,senc_vessel_id
        INTO expected_tactics,tactics_scope,tactics_force,tactics_vessel
        FROM senc_tactics_initiative_receipt
        WHERE tactics_initiative_receipt_id=NEW.tactics_initiative_receipt_id;
        IF tactics_force<>NEW.force_id
           OR (tactics_scope='vessel' AND tactics_vessel<>NEW.senc_vessel_id) THEN
            RAISE EXCEPTION 'Initiative Tactics scope is inconsistent'
                USING ERRCODE='23514';
        END IF;
    END IF;
    IF NEW.tactics_effect<>expected_tactics THEN
        RAISE EXCEPTION 'Initiative Tactics Effect snapshot is inconsistent'
            USING ERRCODE='23514';
    END IF;
    IF NEW.aware_at_start THEN
        SELECT definition.position_code,assignment.duty_status,assignment.actor_id
        INTO pilot_position,pilot_duty,pilot_actor
        FROM ship_crew_assignment assignment
        JOIN ship_crew_position position_state USING(ship_crew_position_id)
        JOIN ship_crew_position_definition definition USING(crew_position_rule_id)
        WHERE assignment.crew_assignment_id=NEW.pilot_assignment_id;
        SELECT rule_id INTO STRICT dex_rule FROM rule_rule
        WHERE rule_code='characteristic.dexterity';
        SELECT current_value INTO dex_value FROM actor_characteristic
        WHERE actor_id=pilot_actor AND characteristic_rule_id=dex_rule;
        SELECT modifier INTO dex_modifier
        FROM rule_characteristic_modifier_band
        WHERE characteristic_rule_id=dex_rule
          AND score_range @> dex_value::integer;
        IF pilot_position<>'pilot' OR pilot_duty<>'active'
           OR dex_value IS NULL OR NEW.pilot_dexterity_value<>dex_value
           OR NEW.pilot_dexterity_modifier<>dex_modifier THEN
            RAISE EXCEPTION 'Aware initiative requires the active pilot Dexterity snapshot'
                USING ERRCODE='23514';
        END IF;
    END IF;
    UPDATE senc_vessel SET initiative_current=NEW.initiative_total
    WHERE senc_vessel_id=NEW.senc_vessel_id;
    RETURN NEW;
END $$;
