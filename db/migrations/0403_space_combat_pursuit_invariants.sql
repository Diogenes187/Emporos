CREATE FUNCTION senc_validate_pursuit_opposed_tasks()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE acting_actor bigint; opposing_actor bigint; acting_skill bigint; opposing_skill bigint; pilot_skill bigint;
BEGIN
 IF NEW.action_kind='maintain' THEN RETURN NEW; END IF;
 SELECT assignment.actor_id INTO acting_actor
 FROM senc_action action JOIN senc_crew_turn turn USING(crew_turn_id)
 JOIN ship_crew_assignment assignment USING(crew_assignment_id)
 WHERE action.space_combat_action_id=NEW.action_id;
 SELECT assignment.actor_id INTO opposing_actor
 FROM senc_vessel vessel
 JOIN ship_crew_assignment assignment ON assignment.ship_id=vessel.ship_id AND assignment.duty_status='active'
 JOIN ship_crew_position position_state USING(ship_crew_position_id)
 JOIN ship_crew_position_definition definition USING(crew_position_rule_id)
 WHERE vessel.senc_vessel_id=NEW.opposing_vessel_id AND definition.position_code='pilot';
 SELECT skill_rule_id INTO acting_skill FROM cmd_actor_task_receipt
 WHERE command_id=NEW.acting_task_command_id AND actor_id=acting_actor;
 SELECT skill_rule_id INTO opposing_skill FROM cmd_actor_task_receipt
 WHERE command_id=NEW.opposing_task_command_id AND actor_id=opposing_actor;
 SELECT rule_id INTO STRICT pilot_skill FROM rule_rule WHERE rule_code='skill.piloting';
 IF acting_skill IS DISTINCT FROM pilot_skill OR opposing_skill IS DISTINCT FROM pilot_skill THEN
   RAISE EXCEPTION 'Pursuit opposed checks require the active pilots and Piloting skill' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER senc_pursuit_opposed_tasks_valid
BEFORE INSERT ON senc_pursuit_action_receipt
FOR EACH ROW EXECUTE FUNCTION senc_validate_pursuit_opposed_tasks();

CREATE FUNCTION senc_validate_pursuit_state_insert()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE pursuer senc_vessel%ROWTYPE; target senc_vessel%ROWTYPE; band text;
BEGIN
 SELECT * INTO STRICT pursuer FROM senc_vessel WHERE senc_vessel_id=NEW.pursuing_vessel_id;
 SELECT * INTO STRICT target FROM senc_vessel WHERE senc_vessel_id=NEW.target_vessel_id;
 SELECT range_band_code INTO band FROM senc_vessel_range
 WHERE engagement_id=NEW.engagement_id
   AND first_vessel_id=least(NEW.pursuing_vessel_id,NEW.target_vessel_id)
   AND second_vessel_id=greatest(NEW.pursuing_vessel_id,NEW.target_vessel_id);
 IF pursuer.force_id=target.force_id OR pursuer.speed_current<>target.speed_current
    OR band<>ALL(ARRAY['close','short']) OR NEW.pursuit_status<>'active'
    OR NEW.established_round<>NEW.last_maintained_round
    OR NEW.consecutive_maintained_turns<>1 OR NEW.attack_modifier<>0 THEN
   RAISE EXCEPTION 'Initial Pursuit state is ineligible' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER senc_pursuit_initial_state_valid BEFORE INSERT ON senc_pursuit
FOR EACH ROW EXECUTE FUNCTION senc_validate_pursuit_state_insert();
