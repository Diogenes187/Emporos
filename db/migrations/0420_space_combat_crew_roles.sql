CREATE TABLE rule_space_combat_crew_role(
 crew_role text PRIMARY KEY CHECK(btrim(crew_role)<>''),
 role_name text NOT NULL UNIQUE CHECK(btrim(role_name)<>''),
 maximum_per_vessel smallint CHECK(maximum_per_vessel>0)
);
INSERT INTO rule_space_combat_crew_role VALUES
 ('captain','Captain',1),('security_or_marine','Chief Security Officer or Marine',NULL),
 ('damage_control','Damage Control',NULL),('gunner','Gunner',NULL),('navigator','Navigator',NULL),
 ('pilot','Pilot',1),('sensors_operator','Sensors Operator',NULL),('anyone','Anyone',NULL);
ALTER TABLE rule_space_combat_action ADD CONSTRAINT rule_space_combat_action_crew_role_fkey
 FOREIGN KEY(crew_role) REFERENCES rule_space_combat_crew_role(crew_role);
CREATE TABLE senc_crew_role_assignment(
 crew_role_assignment_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 engagement_id bigint NOT NULL,campaign_id bigint NOT NULL,senc_vessel_id bigint NOT NULL,
 crew_assignment_id bigint NOT NULL,ship_id bigint NOT NULL,crew_role text NOT NULL REFERENCES rule_space_combat_crew_role(crew_role),
 assigned_at timestamptz NOT NULL DEFAULT clock_timestamp(),ended_at timestamptz,
 FOREIGN KEY(senc_vessel_id,engagement_id,campaign_id) REFERENCES senc_vessel(senc_vessel_id,engagement_id,campaign_id),
 FOREIGN KEY(crew_assignment_id,ship_id,campaign_id) REFERENCES ship_crew_assignment(crew_assignment_id,ship_id,campaign_id),
 UNIQUE(engagement_id,crew_assignment_id,crew_role),CHECK(crew_role<>'anyone')
);
CREATE UNIQUE INDEX senc_one_active_limited_crew_role ON senc_crew_role_assignment(engagement_id,senc_vessel_id,crew_role)
 WHERE ended_at IS NULL AND crew_role IN('captain','pilot');
CREATE FUNCTION senc_validate_crew_role_assignment() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE vessel_ship bigint; active_status text;
BEGIN
 SELECT ship_id INTO vessel_ship FROM senc_vessel WHERE senc_vessel_id=NEW.senc_vessel_id AND engagement_id=NEW.engagement_id AND campaign_id=NEW.campaign_id;
 SELECT duty_status INTO active_status FROM ship_crew_assignment WHERE crew_assignment_id=NEW.crew_assignment_id;
 IF vessel_ship<>NEW.ship_id OR active_status<>'active' THEN RAISE EXCEPTION 'Space combat role requires active crew aboard the assigned vessel' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER senc_crew_role_assignment_valid BEFORE INSERT OR UPDATE ON senc_crew_role_assignment FOR EACH ROW EXECUTE FUNCTION senc_validate_crew_role_assignment();

CREATE OR REPLACE FUNCTION senc_validate_sensor_targeting_receipt() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE a record; t cmd_actor_task_receipt%ROWTYPE; actual_round integer; comms bigint; education bigint; target_electronics record;
BEGIN
 SELECT action.action_code,action.target_vessel_id action_target,action.space_combat_round_id,turn.senc_vessel_id,
  turn.crew_assignment_id,assignment.ship_id,assignment.actor_id,assignment.duty_status INTO a
 FROM senc_action action JOIN senc_crew_turn turn USING(crew_turn_id) JOIN ship_crew_assignment assignment USING(crew_assignment_id)
 WHERE action.space_combat_action_id=NEW.action_id;
 SELECT * INTO STRICT t FROM cmd_actor_task_receipt WHERE command_id=NEW.task_command_id;
 SELECT rule_id INTO STRICT comms FROM rule_rule WHERE rule_code='skill.comms';
 SELECT rule_id INTO STRICT education FROM rule_rule WHERE rule_code='characteristic.education';
 SELECT round_number INTO actual_round FROM senc_round WHERE space_combat_round_id=NEW.space_combat_round_id;
 SELECT selected.electronics_code,suite.communications_dm INTO target_electronics
 FROM senc_vessel vessel JOIN ship_ship ship USING(ship_id) JOIN ship_class_electronics selected USING(ship_class_rule_id)
 JOIN rule_ship_electronics_suite suite USING(electronics_code) WHERE vessel.senc_vessel_id=NEW.target_vessel_id;
 IF a.action_code<>'sensor-targeting' OR a.action_target<>NEW.target_vessel_id OR a.space_combat_round_id<>NEW.space_combat_round_id
  OR a.senc_vessel_id<>NEW.senc_vessel_id OR a.crew_assignment_id<>NEW.operator_assignment_id OR a.ship_id<>NEW.operator_ship_id
  OR a.duty_status<>'active' OR NOT EXISTS(SELECT 1 FROM senc_crew_role_assignment role WHERE role.engagement_id=NEW.engagement_id
    AND role.senc_vessel_id=NEW.senc_vessel_id AND role.crew_assignment_id=NEW.operator_assignment_id
    AND role.crew_role='sensors_operator' AND role.ended_at IS NULL)
  OR t.actor_id<>a.actor_id OR t.skill_rule_id<>comms OR t.characteristic_rule_id<>education OR t.effect<>NEW.task_effect
  OR t.succeeded<>NEW.task_succeeded OR actual_round<>NEW.round_number OR target_electronics.electronics_code<>NEW.target_electronics_code
  OR target_electronics.communications_dm<>NEW.target_sensor_jamming_rating THEN
  RAISE EXCEPTION 'Sensor Targeting receipt does not match its target, active Sensors Operator, Comms check, and jamming snapshot' USING ERRCODE='23514';
 END IF; RETURN NEW;
END $$;
