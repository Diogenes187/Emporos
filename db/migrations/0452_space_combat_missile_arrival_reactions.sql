CREATE TABLE senc_missile_arrival_receipt(
 missile_arrival_receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,missile_salvo_id bigint NOT NULL REFERENCES senc_missile_salvo(missile_salvo_id),
 space_combat_round_id bigint NOT NULL,engagement_id bigint NOT NULL,campaign_id bigint NOT NULL,target_vessel_id bigint NOT NULL,arrival_round integer NOT NULL,
 missiles_at_arrival smallint NOT NULL CHECK(missiles_at_arrival>0),arrival_status text NOT NULL DEFAULT 'open' CHECK(arrival_status IN('open','closed')),
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),FOREIGN KEY(space_combat_round_id,engagement_id,campaign_id) REFERENCES senc_round(space_combat_round_id,engagement_id,campaign_id),
 FOREIGN KEY(target_vessel_id,engagement_id,campaign_id) REFERENCES senc_vessel(senc_vessel_id,engagement_id,campaign_id),UNIQUE(missile_salvo_id,arrival_round));
CREATE FUNCTION senc_validate_missile_arrival() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE salvo senc_missile_salvo%ROWTYPE; actual_round integer; expected_round integer; BEGIN
 SELECT * INTO STRICT salvo FROM senc_missile_salvo WHERE missile_salvo_id=NEW.missile_salvo_id FOR UPDATE;
 SELECT round_number INTO STRICT actual_round FROM senc_round WHERE space_combat_round_id=NEW.space_combat_round_id;
 SELECT coalesce((SELECT final.next_attack_round FROM senc_missile_impact_final_receipt final JOIN senc_missile_impact_attempt attempt USING(missile_impact_attempt_id)
  WHERE attempt.missile_salvo_id=NEW.missile_salvo_id ORDER BY attempt.attempt_order DESC LIMIT 1),salvo.impact_round) INTO expected_round;
 IF salvo.engagement_id<>NEW.engagement_id OR salvo.campaign_id<>NEW.campaign_id OR salvo.target_vessel_id<>NEW.target_vessel_id
  OR salvo.salvo_status<>'in_flight' OR salvo.missiles_remaining<>NEW.missiles_at_arrival OR actual_round<>NEW.arrival_round OR NEW.arrival_round<>expected_round THEN
  RAISE EXCEPTION 'Missile arrival must match the scheduled in-flight salvo and current round' USING ERRCODE='23514'; END IF; RETURN NEW; END $$;
CREATE TRIGGER senc_missile_arrival_valid BEFORE INSERT ON senc_missile_arrival_receipt FOR EACH ROW EXECUTE FUNCTION senc_validate_missile_arrival();

ALTER TABLE senc_reaction ALTER COLUMN triggering_action_id DROP NOT NULL;
ALTER TABLE senc_reaction ADD COLUMN triggering_missile_arrival_id bigint REFERENCES senc_missile_arrival_receipt(missile_arrival_receipt_id);
ALTER TABLE senc_reaction ADD CONSTRAINT senc_reaction_one_trigger CHECK(num_nonnulls(triggering_action_id,triggering_missile_arrival_id)=1);
CREATE UNIQUE INDEX senc_reaction_missile_arrival_order_uq ON senc_reaction(triggering_missile_arrival_id,reaction_order) WHERE triggering_missile_arrival_id IS NOT NULL;
CREATE OR REPLACE FUNCTION senc_validate_reaction_budget() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE trigger_target bigint; trigger_round bigint; reacting_row record; initiative integer; reaction_limit integer; used integer;
BEGIN
 IF NEW.triggering_action_id IS NOT NULL THEN SELECT target_vessel_id,space_combat_round_id INTO trigger_target,trigger_round FROM senc_action WHERE space_combat_action_id=NEW.triggering_action_id;
 ELSE SELECT target_vessel_id,space_combat_round_id INTO trigger_target,trigger_round FROM senc_missile_arrival_receipt WHERE missile_arrival_receipt_id=NEW.triggering_missile_arrival_id AND arrival_status='open'; END IF;
 SELECT turn.senc_vessel_id,action.space_combat_round_id,action.action_code INTO reacting_row FROM senc_action action JOIN senc_crew_turn turn USING(crew_turn_id) WHERE action.space_combat_action_id=NEW.reacting_action_id;
 SELECT initiative_snapshot INTO initiative FROM senc_vessel_turn_order_receipt WHERE space_combat_round_id=reacting_row.space_combat_round_id AND senc_vessel_id=reacting_row.senc_vessel_id;
 SELECT maximum_reactions INTO reaction_limit FROM rule_space_combat_reaction_limit limit_row WHERE initiative>=minimum_initiative AND (maximum_initiative IS NULL OR initiative<=maximum_initiative);
 SELECT count(*) INTO used FROM senc_reaction reaction JOIN senc_action action ON action.space_combat_action_id=reaction.reacting_action_id JOIN senc_crew_turn turn USING(crew_turn_id)
 WHERE action.space_combat_round_id=reacting_row.space_combat_round_id AND turn.senc_vessel_id=reacting_row.senc_vessel_id;
 IF trigger_target<>reacting_row.senc_vessel_id OR trigger_round<>reacting_row.space_combat_round_id OR used>=reaction_limit THEN RAISE EXCEPTION 'Space combat reaction target, round, or Initiative budget is invalid' USING ERRCODE='23514'; END IF; RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION senc_validate_point_defense_sequence() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE rr record; salvo senc_missile_salvo%ROWTYPE; installed_kind text; class_id bigint; BEGIN
 SELECT reaction.triggering_action_id,reaction.triggering_missile_arrival_id,reacting_action.action_code,reacting_action.space_combat_round_id,
  turn.senc_vessel_id,turn.crew_assignment_id,assignment.ship_id,assignment.duty_status,definition.position_code INTO rr FROM senc_reaction reaction
 JOIN senc_action reacting_action ON reacting_action.space_combat_action_id=reaction.reacting_action_id JOIN senc_crew_turn turn USING(crew_turn_id)
 JOIN ship_crew_assignment assignment USING(crew_assignment_id) JOIN ship_crew_position ps USING(ship_crew_position_id) JOIN ship_crew_position_definition definition USING(crew_position_rule_id)
 WHERE reaction.reaction_id=NEW.reaction_id;
 SELECT * INTO STRICT salvo FROM senc_missile_salvo WHERE missile_salvo_id=NEW.missile_salvo_id FOR UPDATE; SELECT weapon_kind INTO installed_kind FROM ship_weapon_definition WHERE weapon_rule_id=NEW.laser_weapon_rule_id; SELECT ship_class_rule_id INTO class_id FROM ship_ship WHERE ship_id=NEW.gunner_ship_id;
 IF rr.action_code<>'point-defense' OR rr.space_combat_round_id<>NEW.space_combat_round_id OR rr.senc_vessel_id<>NEW.senc_vessel_id OR rr.crew_assignment_id<>NEW.gunner_assignment_id
  OR rr.ship_id<>NEW.gunner_ship_id OR rr.duty_status<>'active' OR rr.position_code<>'gunner' OR salvo.target_vessel_id<>NEW.senc_vessel_id OR salvo.missiles_remaining<>NEW.missiles_before
  OR installed_kind<>'laser' OR NOT EXISTS(SELECT 1 FROM ship_class_weapon WHERE ship_class_rule_id=class_id AND weapon_rule_id=NEW.laser_weapon_rule_id)
  OR NOT ((rr.triggering_missile_arrival_id IS NOT NULL AND EXISTS(SELECT 1 FROM senc_missile_arrival_receipt WHERE missile_arrival_receipt_id=rr.triggering_missile_arrival_id AND missile_salvo_id=NEW.missile_salvo_id))
   OR (rr.triggering_action_id IS NOT NULL AND EXISTS(SELECT 1 FROM senc_action WHERE space_combat_action_id=rr.triggering_action_id AND target_vessel_id=NEW.senc_vessel_id))) THEN
  RAISE EXCEPTION 'Point Defense requires matching incoming salvo, active Gunner, and installed turret laser' USING ERRCODE='23514'; END IF; RETURN NEW; END $$;

CREATE OR REPLACE FUNCTION senc_validate_dodge_receipt() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE reaction_row record; task record; pilot bigint; average bigint; actual_round integer; trigger_target bigint; trigger_round bigint;
BEGIN
 SELECT reaction.triggering_action_id,reaction.triggering_missile_arrival_id,reacting_action.action_code,turn.senc_vessel_id,turn.crew_assignment_id,
  assignment.ship_id,assignment.actor_id,assignment.duty_status,definition.position_code INTO reaction_row FROM senc_reaction reaction
 JOIN senc_action reacting_action ON reacting_action.space_combat_action_id=reaction.reacting_action_id JOIN senc_crew_turn turn ON turn.crew_turn_id=reacting_action.crew_turn_id
 JOIN ship_crew_assignment assignment USING(crew_assignment_id) JOIN ship_crew_position ps USING(ship_crew_position_id) JOIN ship_crew_position_definition definition USING(crew_position_rule_id) WHERE reaction.reaction_id=NEW.reaction_id;
 IF reaction_row.triggering_action_id IS NOT NULL THEN SELECT target_vessel_id,space_combat_round_id INTO trigger_target,trigger_round FROM senc_action WHERE space_combat_action_id=reaction_row.triggering_action_id;
 ELSE SELECT target_vessel_id,space_combat_round_id INTO trigger_target,trigger_round FROM senc_missile_arrival_receipt WHERE missile_arrival_receipt_id=reaction_row.triggering_missile_arrival_id; END IF;
 SELECT actor_id,skill_rule_id,difficulty_rule_id,effect,succeeded INTO task FROM cmd_actor_task_receipt WHERE command_id=NEW.task_command_id;
 SELECT rule_id INTO pilot FROM rule_rule WHERE rule_code='skill.piloting'; SELECT rule_id INTO average FROM rule_rule WHERE rule_code='difficulty.average'; SELECT round_number INTO actual_round FROM senc_round WHERE space_combat_round_id=NEW.space_combat_round_id;
 IF reaction_row.action_code<>'dodge' OR trigger_round<>NEW.space_combat_round_id OR trigger_target<>NEW.senc_vessel_id OR reaction_row.senc_vessel_id<>NEW.senc_vessel_id
  OR reaction_row.crew_assignment_id<>NEW.pilot_assignment_id OR reaction_row.ship_id<>NEW.pilot_ship_id OR reaction_row.actor_id<>task.actor_id OR reaction_row.duty_status<>'active'
  OR reaction_row.position_code<>'pilot' OR task.skill_rule_id<>pilot OR task.difficulty_rule_id<>average OR task.effect<>NEW.task_effect OR task.succeeded<>NEW.task_succeeded OR actual_round<>NEW.round_number THEN
  RAISE EXCEPTION 'Dodge receipt does not match its reaction and active Pilot check' USING ERRCODE='23514'; END IF; RETURN NEW; END $$;

CREATE TABLE senc_missile_arrival_close_receipt(
 missile_arrival_receipt_id bigint PRIMARY KEY REFERENCES senc_missile_arrival_receipt(missile_arrival_receipt_id),missile_salvo_id bigint NOT NULL,
 missiles_after_point_defense smallint NOT NULL CHECK(missiles_after_point_defense>=0),dodge_modifier smallint NOT NULL CHECK(dodge_modifier<=0),
 base_target_number smallint NOT NULL,effective_target_number smallint NOT NULL CHECK(effective_target_number=base_target_number-dodge_modifier),closed_at timestamptz NOT NULL DEFAULT clock_timestamp());
CREATE FUNCTION senc_close_missile_arrival() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE arrival senc_missile_arrival_receipt%ROWTYPE; salvo senc_missile_salvo%ROWTYPE; expected_dodge integer; base_target integer;
BEGIN SELECT * INTO STRICT arrival FROM senc_missile_arrival_receipt WHERE missile_arrival_receipt_id=NEW.missile_arrival_receipt_id FOR UPDATE;
 SELECT * INTO STRICT salvo FROM senc_missile_salvo WHERE missile_salvo_id=arrival.missile_salvo_id FOR UPDATE;
 SELECT coalesce(sum(dodge.attack_modifier),0) INTO expected_dodge FROM senc_reaction reaction JOIN senc_dodge_receipt dodge USING(reaction_id) WHERE reaction.triggering_missile_arrival_id=arrival.missile_arrival_receipt_id;
 SELECT launch.impact_target_number INTO STRICT base_target FROM senc_missile_launch_receipt launch WHERE launch.missile_launch_receipt_id=salvo.launch_receipt_id;
 IF arrival.arrival_status<>'open' OR NEW.missile_salvo_id<>arrival.missile_salvo_id OR NEW.missiles_after_point_defense<>salvo.missiles_remaining
  OR NEW.dodge_modifier<>expected_dodge OR NEW.base_target_number<>base_target OR NEW.effective_target_number<>base_target-expected_dodge THEN
  RAISE EXCEPTION 'Missile arrival close receipt must snapshot all Point Defense and Dodge results' USING ERRCODE='23514'; END IF;
 UPDATE senc_missile_arrival_receipt SET arrival_status='closed' WHERE missile_arrival_receipt_id=arrival.missile_arrival_receipt_id; RETURN NEW; END $$;
CREATE TRIGGER senc_missile_arrival_close_valid BEFORE INSERT ON senc_missile_arrival_close_receipt FOR EACH ROW EXECUTE FUNCTION senc_close_missile_arrival();
ALTER TABLE senc_missile_impact_attempt DROP CONSTRAINT senc_missile_impact_attempt_target_number_check;
ALTER TABLE senc_missile_impact_attempt ADD CONSTRAINT senc_missile_impact_attempt_target_number_positive CHECK(target_number>0);
ALTER TABLE senc_missile_impact_attempt ADD COLUMN missile_arrival_receipt_id bigint NOT NULL REFERENCES senc_missile_arrival_close_receipt(missile_arrival_receipt_id);
CREATE OR REPLACE FUNCTION senc_validate_missile_impact_attempt() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE salvo senc_missile_salvo%ROWTYPE; close_row senc_missile_arrival_close_receipt%ROWTYPE; actual_round integer; prior_count integer; expected_attempt_round integer;
BEGIN SELECT * INTO STRICT salvo FROM senc_missile_salvo WHERE missile_salvo_id=NEW.missile_salvo_id FOR UPDATE;
 SELECT * INTO STRICT close_row FROM senc_missile_arrival_close_receipt WHERE missile_arrival_receipt_id=NEW.missile_arrival_receipt_id;
 SELECT round_number INTO STRICT actual_round FROM senc_round WHERE space_combat_round_id=NEW.space_combat_round_id; SELECT count(*) INTO prior_count FROM senc_missile_impact_attempt WHERE missile_salvo_id=NEW.missile_salvo_id;
 IF prior_count=0 THEN expected_attempt_round:=salvo.impact_round; ELSE SELECT final.next_attack_round INTO STRICT expected_attempt_round FROM senc_missile_impact_final_receipt final JOIN senc_missile_impact_attempt attempt USING(missile_impact_attempt_id) WHERE attempt.missile_salvo_id=NEW.missile_salvo_id ORDER BY attempt.attempt_order DESC LIMIT 1; END IF;
 IF close_row.missile_salvo_id<>NEW.missile_salvo_id OR salvo.engagement_id<>NEW.engagement_id OR salvo.campaign_id<>NEW.campaign_id OR actual_round<>NEW.attempt_round
  OR salvo.salvo_status<>'in_flight' OR salvo.missiles_remaining<>NEW.missiles_before OR close_row.missiles_after_point_defense<>NEW.missiles_before OR NEW.attempt_order<>prior_count+1
  OR NEW.attempt_round<>expected_attempt_round OR NEW.target_number<>close_row.effective_target_number OR NEW.smart_missiles<>salvo.smart_missiles
  OR NEW.endurance_expires_after_round<>salvo.launched_round+(SELECT endurance_turns FROM rule_space_combat_missile_behavior) THEN RAISE EXCEPTION 'Missile impact attempt requires a closed scheduled arrival and current surviving salvo' USING ERRCODE='23514'; END IF; RETURN NEW; END $$;
CREATE FUNCTION senc_reject_missile_arrival_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
 IF TG_TABLE_NAME='senc_missile_arrival_receipt' AND TG_OP='UPDATE' AND OLD.arrival_status='open' AND NEW.arrival_status='closed' AND (to_jsonb(OLD)-'arrival_status')=(to_jsonb(NEW)-'arrival_status') THEN RETURN NEW; END IF;
 RAISE EXCEPTION 'Missile arrival receipts are immutable'; END $$;
CREATE TRIGGER senc_missile_arrival_immutable BEFORE UPDATE OR DELETE ON senc_missile_arrival_receipt FOR EACH ROW EXECUTE FUNCTION senc_reject_missile_arrival_mutation();
CREATE TRIGGER senc_missile_arrival_close_immutable BEFORE UPDATE OR DELETE ON senc_missile_arrival_close_receipt FOR EACH ROW EXECUTE FUNCTION senc_reject_missile_arrival_mutation();
