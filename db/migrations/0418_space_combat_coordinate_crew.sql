INSERT INTO src_locator(source_work_id,source_artifact_id,locator_type,heading_path,display_citation)
SELECT a.source_work_id,a.source_artifact_id,'heading','Space Combat > Significant Actions > Coordinate Crew',
 CASE w.work_code WHEN 'cepheus-engine.ogn' THEN 'Cepheus Engine SRD, Space Combat: Coordinate Crew'
 ELSE 'Cepheus Engine v9.1, Space Combat: Coordinate Crew' END
FROM src_artifact a JOIN src_work w USING(source_work_id)
WHERE (w.work_code='cepheus-engine.ogn' AND a.source_uri LIKE '%cepheus-engine-space-combat/')
 OR (w.work_code='cepheus-engine.github-v9.1' AND a.source_uri='src/book2/space-combat.md')
ON CONFLICT DO NOTHING;

WITH p AS (SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine')
INSERT INTO rule_rule(content_package_id,rule_code,name,rule_category,rule_status,description)
SELECT content_package_id,'combat.space.coordinate-crew','Coordinate Crew','combat','approved',
 'Captain creates a current-turn Leadership pool allocated as check DMs to individual crewmembers.' FROM p;
CREATE TABLE rule_space_combat_coordinate_crew(
 rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
 skill_rule_id bigint NOT NULL REFERENCES rule_skill(rule_id),
 difficulty_rule_id bigint NOT NULL REFERENCES rule_difficulty(rule_id),
 minimum_pool_points smallint NOT NULL CHECK(minimum_pool_points=1),
 points_per_effect smallint NOT NULL CHECK(points_per_effect=1),
 modifier_per_point smallint NOT NULL CHECK(modifier_per_point=1),
 individual_crew_allocations boolean NOT NULL,
 current_round_only boolean NOT NULL
);
INSERT INTO rule_space_combat_coordinate_crew
SELECT r.rule_id,s.rule_id,d.rule_id,1,1,1,true,true FROM rule_rule r CROSS JOIN rule_rule s CROSS JOIN rule_rule d
WHERE r.rule_code='combat.space.coordinate-crew' AND s.rule_code='skill.leadership' AND d.rule_code='difficulty.average';
INSERT INTO src_record_provenance(rule_id,content_package_id,source_locator_id,provenance_class,is_primary_citation)
SELECT r.rule_id,r.content_package_id,l.source_locator_id,
 CASE w.work_code WHEN 'cepheus-engine.ogn' THEN 'direct' ELSE 'corroborating' END,w.work_code='cepheus-engine.ogn'
FROM rule_rule r CROSS JOIN src_locator l JOIN src_work w USING(source_work_id)
WHERE r.rule_code='combat.space.coordinate-crew'
 AND l.heading_path='Space Combat > Significant Actions > Coordinate Crew'
 AND w.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1');

CREATE TABLE senc_coordinate_crew_receipt(
 coordinate_crew_receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 action_id bigint NOT NULL UNIQUE,engagement_id bigint NOT NULL,campaign_id bigint NOT NULL,
 space_combat_round_id bigint NOT NULL,round_number integer NOT NULL CHECK(round_number>0),
 senc_vessel_id bigint NOT NULL,captain_assignment_id bigint NOT NULL,captain_ship_id bigint NOT NULL,
 task_command_id bigint NOT NULL UNIQUE REFERENCES cmd_actor_task_receipt(command_id),
 task_effect smallint NOT NULL,pool_points smallint NOT NULL CHECK(pool_points=greatest(1,task_effect)),
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(action_id,engagement_id,campaign_id) REFERENCES senc_action(space_combat_action_id,engagement_id,campaign_id),
 FOREIGN KEY(space_combat_round_id,engagement_id,campaign_id) REFERENCES senc_round(space_combat_round_id,engagement_id,campaign_id),
 FOREIGN KEY(senc_vessel_id,engagement_id,campaign_id) REFERENCES senc_vessel(senc_vessel_id,engagement_id,campaign_id),
 FOREIGN KEY(captain_assignment_id,captain_ship_id,campaign_id) REFERENCES ship_crew_assignment(crew_assignment_id,ship_id,campaign_id),
 UNIQUE(engagement_id,senc_vessel_id,round_number)
);
CREATE TABLE senc_coordinate_crew_allocation(
 coordinate_crew_allocation_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 coordinate_crew_receipt_id bigint NOT NULL REFERENCES senc_coordinate_crew_receipt(coordinate_crew_receipt_id),
 recipient_assignment_id bigint NOT NULL,recipient_ship_id bigint NOT NULL,campaign_id bigint NOT NULL,
 points smallint NOT NULL CHECK(points>0),recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(recipient_assignment_id,recipient_ship_id,campaign_id) REFERENCES ship_crew_assignment(crew_assignment_id,ship_id,campaign_id),
 UNIQUE(coordinate_crew_receipt_id,recipient_assignment_id)
);
CREATE FUNCTION senc_validate_coordinate_crew_receipt() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE a record; t cmd_actor_task_receipt%ROWTYPE; actual_round integer; leadership bigint; average bigint;
BEGIN
 SELECT action.action_code,action.space_combat_round_id,turn.senc_vessel_id,turn.crew_assignment_id,
  assignment.ship_id,assignment.actor_id,assignment.duty_status,definition.position_code INTO a
 FROM senc_action action JOIN senc_crew_turn turn USING(crew_turn_id)
 JOIN ship_crew_assignment assignment USING(crew_assignment_id)
 JOIN ship_crew_position position_state USING(ship_crew_position_id)
 JOIN ship_crew_position_definition definition USING(crew_position_rule_id)
 WHERE action.space_combat_action_id=NEW.action_id;
 SELECT * INTO STRICT t FROM cmd_actor_task_receipt WHERE command_id=NEW.task_command_id;
 SELECT rule_id INTO STRICT leadership FROM rule_rule WHERE rule_code='skill.leadership';
 SELECT rule_id INTO STRICT average FROM rule_rule WHERE rule_code='difficulty.average';
 SELECT round_number INTO actual_round FROM senc_round WHERE space_combat_round_id=NEW.space_combat_round_id;
 IF a.action_code<>'coordinate-crew' OR a.space_combat_round_id<>NEW.space_combat_round_id
  OR a.senc_vessel_id<>NEW.senc_vessel_id OR a.crew_assignment_id<>NEW.captain_assignment_id
  OR a.ship_id<>NEW.captain_ship_id OR a.duty_status<>'active' OR a.position_code<>'master'
  OR t.actor_id<>a.actor_id OR t.skill_rule_id<>leadership OR t.difficulty_rule_id<>average
  OR t.effect<>NEW.task_effect OR actual_round<>NEW.round_number THEN
  RAISE EXCEPTION 'Coordinate Crew receipt does not match its active Captain action and Average Leadership check' USING ERRCODE='23514';
 END IF; RETURN NEW;
END $$;
CREATE TRIGGER senc_coordinate_crew_receipt_valid BEFORE INSERT ON senc_coordinate_crew_receipt
FOR EACH ROW EXECUTE FUNCTION senc_validate_coordinate_crew_receipt();
CREATE FUNCTION senc_validate_coordinate_crew_allocation() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE r senc_coordinate_crew_receipt%ROWTYPE; allocated integer; recipient_vessel bigint;
BEGIN
 SELECT * INTO STRICT r FROM senc_coordinate_crew_receipt WHERE coordinate_crew_receipt_id=NEW.coordinate_crew_receipt_id FOR UPDATE;
 SELECT coalesce(sum(points),0) INTO allocated FROM senc_coordinate_crew_allocation WHERE coordinate_crew_receipt_id=NEW.coordinate_crew_receipt_id;
 SELECT vessel.senc_vessel_id INTO recipient_vessel FROM ship_crew_assignment assignment
 JOIN senc_vessel vessel ON vessel.ship_id=assignment.ship_id AND vessel.engagement_id=r.engagement_id
 WHERE assignment.crew_assignment_id=NEW.recipient_assignment_id AND assignment.duty_status='active';
 IF NEW.campaign_id<>r.campaign_id OR NEW.recipient_ship_id<>r.captain_ship_id
  OR recipient_vessel<>r.senc_vessel_id OR allocated+NEW.points>r.pool_points THEN
  RAISE EXCEPTION 'Coordinate Crew allocation exceeds its pool or leaves the active vessel crew' USING ERRCODE='23514';
 END IF; RETURN NEW;
END $$;
CREATE TRIGGER senc_coordinate_crew_allocation_valid BEFORE INSERT ON senc_coordinate_crew_allocation
FOR EACH ROW EXECUTE FUNCTION senc_validate_coordinate_crew_allocation();
CREATE FUNCTION senc_reject_coordinate_crew_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Coordinate Crew receipts and allocations are immutable'; END $$;
CREATE TRIGGER senc_coordinate_crew_receipt_immutable BEFORE UPDATE OR DELETE ON senc_coordinate_crew_receipt
FOR EACH ROW EXECUTE FUNCTION senc_reject_coordinate_crew_mutation();
CREATE TRIGGER senc_coordinate_crew_allocation_immutable BEFORE UPDATE OR DELETE ON senc_coordinate_crew_allocation
FOR EACH ROW EXECUTE FUNCTION senc_reject_coordinate_crew_mutation();
