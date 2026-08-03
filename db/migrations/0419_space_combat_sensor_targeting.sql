INSERT INTO src_locator(source_work_id,source_artifact_id,locator_type,heading_path,display_citation)
SELECT a.source_work_id,a.source_artifact_id,'heading','Space Combat > Significant Actions > Sensor Targeting',
 CASE w.work_code WHEN 'cepheus-engine.ogn' THEN 'Cepheus Engine SRD, Space Combat: Sensor Targeting'
 ELSE 'Cepheus Engine v9.1, Space Combat: Sensor Targeting' END
FROM src_artifact a JOIN src_work w USING(source_work_id)
WHERE (w.work_code='cepheus-engine.ogn' AND a.source_uri LIKE '%cepheus-engine-space-combat/')
 OR (w.work_code='cepheus-engine.github-v9.1' AND a.source_uri='src/book2/space-combat.md') ON CONFLICT DO NOTHING;
WITH p AS (SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine')
INSERT INTO rule_rule(content_package_id,rule_code,name,rule_category,rule_status,description)
SELECT content_package_id,'combat.space.sensor-targeting','Sensor Targeting','combat','approved',
 'Sensors Operator provides target-specific current-turn fire-control bonuses.' FROM p;
CREATE TABLE rule_space_combat_sensor_targeting(
 rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),skill_rule_id bigint NOT NULL REFERENCES rule_skill(rule_id),
 characteristic_rule_id bigint NOT NULL REFERENCES rule_characteristic(rule_id),success_attack_bonus smallint NOT NULL CHECK(success_attack_bonus=1),
 exceptional_effect_threshold smallint NOT NULL CHECK(exceptional_effect_threshold=6),exceptional_attack_bonus smallint NOT NULL CHECK(exceptional_attack_bonus=2),
 applies_to_all_gunners boolean NOT NULL,applies_current_round_only boolean NOT NULL,target_specific boolean NOT NULL,
 missile_launch_check_benefits boolean NOT NULL,missile_impact_roll_benefits boolean NOT NULL,smart_missiles_benefit boolean NOT NULL
);
INSERT INTO rule_space_combat_sensor_targeting
SELECT r.rule_id,s.rule_id,c.rule_id,1,6,2,true,true,true,true,false,false
FROM rule_rule r CROSS JOIN rule_rule s CROSS JOIN rule_rule c
WHERE r.rule_code='combat.space.sensor-targeting' AND s.rule_code='skill.comms' AND c.rule_code='characteristic.education';
INSERT INTO src_record_provenance(rule_id,content_package_id,source_locator_id,provenance_class,is_primary_citation)
SELECT r.rule_id,r.content_package_id,l.source_locator_id,CASE w.work_code WHEN 'cepheus-engine.ogn' THEN 'direct' ELSE 'corroborating' END,w.work_code='cepheus-engine.ogn'
FROM rule_rule r CROSS JOIN src_locator l JOIN src_work w USING(source_work_id)
WHERE r.rule_code='combat.space.sensor-targeting' AND l.heading_path='Space Combat > Significant Actions > Sensor Targeting'
 AND w.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1');
CREATE TABLE senc_sensor_targeting_receipt(
 sensor_targeting_receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 action_id bigint NOT NULL UNIQUE,engagement_id bigint NOT NULL,campaign_id bigint NOT NULL,
 space_combat_round_id bigint NOT NULL,round_number integer NOT NULL CHECK(round_number>0),
 senc_vessel_id bigint NOT NULL,target_vessel_id bigint NOT NULL,
 operator_assignment_id bigint NOT NULL,operator_ship_id bigint NOT NULL,
 target_electronics_code text NOT NULL REFERENCES rule_ship_electronics_suite(electronics_code),
 target_sensor_jamming_rating smallint NOT NULL,task_command_id bigint NOT NULL UNIQUE REFERENCES cmd_actor_task_receipt(command_id),
 task_effect smallint NOT NULL,task_succeeded boolean NOT NULL,attack_bonus smallint NOT NULL CHECK(attack_bonus IN(0,1,2)),
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(action_id,engagement_id,campaign_id) REFERENCES senc_action(space_combat_action_id,engagement_id,campaign_id),
 FOREIGN KEY(space_combat_round_id,engagement_id,campaign_id) REFERENCES senc_round(space_combat_round_id,engagement_id,campaign_id),
 FOREIGN KEY(senc_vessel_id,engagement_id,campaign_id) REFERENCES senc_vessel(senc_vessel_id,engagement_id,campaign_id),
 FOREIGN KEY(target_vessel_id,engagement_id,campaign_id) REFERENCES senc_vessel(senc_vessel_id,engagement_id,campaign_id),
 FOREIGN KEY(operator_assignment_id,operator_ship_id,campaign_id) REFERENCES ship_crew_assignment(crew_assignment_id,ship_id,campaign_id),
 UNIQUE(engagement_id,senc_vessel_id,target_vessel_id,round_number),
 CHECK(senc_vessel_id<>target_vessel_id),
 CHECK(attack_bonus=CASE WHEN NOT task_succeeded THEN 0 WHEN task_effect>=6 THEN 2 ELSE 1 END)
);
CREATE FUNCTION senc_validate_sensor_targeting_receipt() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE a record; t cmd_actor_task_receipt%ROWTYPE; actual_round integer; comms bigint; education bigint; target_electronics record;
BEGIN
 SELECT action.action_code,action.target_vessel_id action_target,action.space_combat_round_id,turn.senc_vessel_id,
  turn.crew_assignment_id,assignment.ship_id,assignment.actor_id,assignment.duty_status,definition.position_code INTO a
 FROM senc_action action JOIN senc_crew_turn turn USING(crew_turn_id) JOIN ship_crew_assignment assignment USING(crew_assignment_id)
 JOIN ship_crew_position position_state USING(ship_crew_position_id) JOIN ship_crew_position_definition definition USING(crew_position_rule_id)
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
  OR a.duty_status<>'active' OR a.position_code<>'sensors-operator' OR t.actor_id<>a.actor_id
  OR t.skill_rule_id<>comms OR t.characteristic_rule_id<>education OR t.effect<>NEW.task_effect OR t.succeeded<>NEW.task_succeeded
  OR actual_round<>NEW.round_number OR target_electronics.electronics_code<>NEW.target_electronics_code
  OR target_electronics.communications_dm<>NEW.target_sensor_jamming_rating THEN
  RAISE EXCEPTION 'Sensor Targeting receipt does not match its target, active Sensors Operator, Comms check, and jamming snapshot' USING ERRCODE='23514';
 END IF; RETURN NEW;
END $$;
CREATE TRIGGER senc_sensor_targeting_valid BEFORE INSERT ON senc_sensor_targeting_receipt FOR EACH ROW EXECUTE FUNCTION senc_validate_sensor_targeting_receipt();
CREATE FUNCTION senc_reject_sensor_targeting_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Sensor Targeting receipts are immutable'; END $$;
CREATE TRIGGER senc_sensor_targeting_immutable BEFORE UPDATE OR DELETE ON senc_sensor_targeting_receipt FOR EACH ROW EXECUTE FUNCTION senc_reject_sensor_targeting_mutation();
