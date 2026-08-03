CREATE FUNCTION senc_validate_pursuit_action_receipt()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE p senc_pursuit%ROWTYPE; a record; ta record; tb record; expected_win boolean;
BEGIN
 SELECT * INTO STRICT p FROM senc_pursuit WHERE pursuit_id=NEW.pursuit_id FOR UPDATE;
 SELECT action.action_code,turn.senc_vessel_id,action.target_vessel_id,
        assignment.actor_id,assignment.duty_status,definition.position_code
 INTO a FROM senc_action action JOIN senc_crew_turn turn USING(crew_turn_id)
 JOIN ship_crew_assignment assignment USING(crew_assignment_id)
 JOIN ship_crew_position position_state USING(ship_crew_position_id)
 JOIN ship_crew_position_definition definition USING(crew_position_rule_id)
 WHERE action.space_combat_action_id=NEW.action_id;
 IF a.position_code<>'pilot' OR a.duty_status<>'active'
    OR a.senc_vessel_id<>NEW.acting_vessel_id
    OR a.target_vessel_id<>NEW.opposing_vessel_id
    OR (NEW.action_kind='establish' AND a.action_code<>'pursuit')
    OR (NEW.action_kind='maintain' AND a.action_code<>'pursuit')
    OR (NEW.action_kind='break' AND a.action_code<>'break-pursuit') THEN
   RAISE EXCEPTION 'Pursuit receipt requires the matching active pilot action' USING ERRCODE='23514';
 END IF;
 IF NEW.action_kind IN('establish','break') THEN
   SELECT actor_id,effect INTO ta FROM cmd_actor_task_receipt WHERE command_id=NEW.acting_task_command_id;
   SELECT actor_id,effect INTO tb FROM cmd_actor_task_receipt WHERE command_id=NEW.opposing_task_command_id;
   expected_win:=CASE WHEN NEW.acting_effect>NEW.opposing_effect THEN true
     WHEN NEW.acting_effect<NEW.opposing_effect THEN false
     WHEN NEW.acting_characteristic_value>NEW.opposing_characteristic_value THEN true
     WHEN NEW.acting_characteristic_value<NEW.opposing_characteristic_value THEN false
     ELSE false END;
   IF ta.actor_id<>a.actor_id OR ta.effect<>NEW.acting_effect OR tb.effect<>NEW.opposing_effect
      OR NEW.acting_won<>expected_win THEN
     RAISE EXCEPTION 'Pursuit opposed Piloting result is inconsistent' USING ERRCODE='23514';
   END IF;
 END IF;
 IF NEW.action_kind='establish' THEN
   IF p.pursuing_vessel_id<>NEW.acting_vessel_id OR p.target_vessel_id<>NEW.opposing_vessel_id
      OR p.established_round<>NEW.round_number OR p.consecutive_maintained_turns<>1
      OR p.attack_modifier<>0 OR NOT NEW.acting_won
      OR NEW.range_band_snapshot<>ALL(ARRAY['close','short'])
      OR NEW.acting_speed_snapshot<>NEW.opposing_speed_snapshot THEN
     RAISE EXCEPTION 'Pursuit establishment eligibility is inconsistent' USING ERRCODE='23514';
   END IF;
   INSERT INTO senc_pursuit_transition_receipt
    (pursuit_id,engagement_id,campaign_id,round_number,transition_kind,reason,attack_modifier_before,attack_modifier_after)
   VALUES(p.pursuit_id,p.engagement_id,p.campaign_id,NEW.round_number,'established','action',NULL,0);
 ELSIF NEW.action_kind='maintain' THEN
   IF p.pursuit_status<>'active' OR p.pursuing_vessel_id<>NEW.acting_vessel_id
      OR p.target_vessel_id<>NEW.opposing_vessel_id
      OR NEW.round_number<>p.last_maintained_round+1
      OR NEW.attack_modifier_before<>p.attack_modifier
      OR NEW.attack_modifier_after<>least(p.attack_modifier+1,4) THEN
     RAISE EXCEPTION 'Pursuit maintenance sequence is inconsistent' USING ERRCODE='23514';
   END IF;
   UPDATE senc_pursuit SET last_maintained_round=NEW.round_number,
     consecutive_maintained_turns=consecutive_maintained_turns+1,
     attack_modifier=NEW.attack_modifier_after WHERE pursuit_id=p.pursuit_id;
   INSERT INTO senc_pursuit_transition_receipt
    (pursuit_id,engagement_id,campaign_id,round_number,transition_kind,reason,attack_modifier_before,attack_modifier_after)
   VALUES(p.pursuit_id,p.engagement_id,p.campaign_id,NEW.round_number,'maintained','action',p.attack_modifier,NEW.attack_modifier_after);
 ELSE
   IF p.pursuit_status<>'active' OR p.target_vessel_id<>NEW.acting_vessel_id
      OR p.pursuing_vessel_id<>NEW.opposing_vessel_id THEN
     RAISE EXCEPTION 'Break Pursuit participants are inconsistent' USING ERRCODE='23514';
   END IF;
   IF NEW.acting_won THEN
     UPDATE senc_pursuit SET pursuit_status='broken',ended_round=NEW.round_number,
       ended_reason='break-action',attack_modifier=0 WHERE pursuit_id=p.pursuit_id;
     INSERT INTO senc_pursuit_transition_receipt
      (pursuit_id,engagement_id,campaign_id,round_number,transition_kind,reason,attack_modifier_before,attack_modifier_after)
     VALUES(p.pursuit_id,p.engagement_id,p.campaign_id,NEW.round_number,'broken','break-action',p.attack_modifier,0);
   END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER senc_pursuit_action_valid BEFORE INSERT ON senc_pursuit_action_receipt
FOR EACH ROW EXECUTE FUNCTION senc_validate_pursuit_action_receipt();
