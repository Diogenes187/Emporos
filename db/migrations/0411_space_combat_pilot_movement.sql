INSERT INTO src_locator(source_work_id,source_artifact_id,locator_type,heading_path,display_citation)
SELECT a.source_work_id,a.source_artifact_id,'heading',v.heading,
 CASE w.work_code WHEN 'cepheus-engine.ogn' THEN 'Cepheus Engine SRD, Space Combat: '||v.label
 ELSE 'Cepheus Engine v9.1, Space Combat: '||v.label END
FROM src_artifact a JOIN src_work w USING(source_work_id)
CROSS JOIN (VALUES
 ('Space Combat > Minor Actions > Adjust Speed','Adjust Speed'),
 ('Space Combat > Minor Actions > Maintain Course','Maintain Course')
) v(heading,label)
WHERE (w.work_code='cepheus-engine.ogn' AND a.source_uri LIKE '%cepheus-engine-space-combat/')
 OR (w.work_code='cepheus-engine.github-v9.1' AND a.source_uri='src/book2/space-combat.md')
ON CONFLICT DO NOTHING;

WITH p AS (SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine')
INSERT INTO rule_rule(content_package_id,rule_code,name,rule_category,rule_status,description)
SELECT content_package_id,'combat.space.pilot-movement','Space Combat Pilot Movement','combat','approved',
 'Minor Pilot actions for Thrust-bounded speed adjustment or unchanged course maintenance.' FROM p;
CREATE TABLE rule_space_combat_pilot_movement(
 rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
 adjust_speed_action_code text NOT NULL REFERENCES rule_space_combat_action(action_code) CHECK(adjust_speed_action_code='adjust-speed'),
 maintain_course_action_code text NOT NULL REFERENCES rule_space_combat_action(action_code) CHECK(maintain_course_action_code='maintain-course'),
 speed_change_limited_by_thrust boolean NOT NULL,minimum_speed numeric NOT NULL CHECK(minimum_speed=0),
 adjust_requires_check boolean NOT NULL,maintain_requires_check boolean NOT NULL,
 maintain_preserves_speed boolean NOT NULL,both_are_minor_actions boolean NOT NULL
);
INSERT INTO rule_space_combat_pilot_movement
SELECT rule_id,'adjust-speed','maintain-course',true,0,false,false,true,true
FROM rule_rule WHERE rule_code='combat.space.pilot-movement';
INSERT INTO src_record_provenance(rule_id,content_package_id,source_locator_id,provenance_class,is_primary_citation)
SELECT r.rule_id,r.content_package_id,l.source_locator_id,CASE w.work_code WHEN 'cepheus-engine.ogn' THEN 'direct' ELSE 'corroborating' END,w.work_code='cepheus-engine.ogn'
FROM rule_rule r CROSS JOIN src_locator l JOIN src_work w USING(source_work_id)
WHERE r.rule_code='combat.space.pilot-movement'
 AND l.heading_path IN('Space Combat > Minor Actions > Adjust Speed','Space Combat > Minor Actions > Maintain Course')
 AND w.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1');

CREATE TABLE senc_pilot_movement_receipt(
 pilot_movement_receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 engagement_id bigint NOT NULL,campaign_id bigint NOT NULL,space_combat_round_id bigint NOT NULL,
 round_number integer NOT NULL CHECK(round_number>0),senc_vessel_id bigint NOT NULL,
 action_id bigint NOT NULL UNIQUE,pilot_assignment_id bigint NOT NULL,pilot_ship_id bigint NOT NULL,
 movement_kind text NOT NULL CHECK(movement_kind IN('adjust-speed','maintain-course')),
 speed_before numeric NOT NULL CHECK(speed_before>=0),speed_after numeric NOT NULL CHECK(speed_after>=0),
 thrust_snapshot smallint NOT NULL CHECK(thrust_snapshot>=0),recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(space_combat_round_id,engagement_id,campaign_id) REFERENCES senc_round(space_combat_round_id,engagement_id,campaign_id),
 FOREIGN KEY(senc_vessel_id,engagement_id,campaign_id) REFERENCES senc_vessel(senc_vessel_id,engagement_id,campaign_id),
 FOREIGN KEY(action_id,engagement_id,campaign_id) REFERENCES senc_action(space_combat_action_id,engagement_id,campaign_id),
 FOREIGN KEY(pilot_assignment_id,pilot_ship_id,campaign_id) REFERENCES ship_crew_assignment(crew_assignment_id,ship_id,campaign_id),
 CHECK((movement_kind='adjust-speed' AND abs(speed_after-speed_before)<=thrust_snapshot)
  OR (movement_kind='maintain-course' AND speed_after=speed_before))
);
CREATE FUNCTION senc_apply_pilot_movement() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE action_row record; vessel senc_vessel%ROWTYPE; actual_round integer;
BEGIN
 SELECT action.action_code,action.space_combat_round_id,turn.senc_vessel_id,turn.crew_assignment_id,
  assignment.ship_id,assignment.duty_status,definition.position_code INTO action_row
 FROM senc_action action JOIN senc_crew_turn turn USING(crew_turn_id)
 JOIN ship_crew_assignment assignment USING(crew_assignment_id)
 JOIN ship_crew_position position_state USING(ship_crew_position_id)
 JOIN ship_crew_position_definition definition USING(crew_position_rule_id)
 WHERE action.space_combat_action_id=NEW.action_id;
 SELECT * INTO STRICT vessel FROM senc_vessel WHERE senc_vessel_id=NEW.senc_vessel_id FOR UPDATE;
 SELECT round_number INTO actual_round FROM senc_round WHERE space_combat_round_id=NEW.space_combat_round_id;
 IF action_row.action_code<>NEW.movement_kind OR action_row.space_combat_round_id<>NEW.space_combat_round_id
  OR action_row.senc_vessel_id<>NEW.senc_vessel_id OR action_row.crew_assignment_id<>NEW.pilot_assignment_id
  OR action_row.ship_id<>NEW.pilot_ship_id OR action_row.duty_status<>'active' OR action_row.position_code<>'pilot'
  OR vessel.speed_current<>NEW.speed_before OR vessel.thrust_current<>NEW.thrust_snapshot
  OR actual_round<>NEW.round_number THEN
  RAISE EXCEPTION 'Pilot movement receipt does not match its active Pilot action and vessel state' USING ERRCODE='23514';
 END IF;
 UPDATE senc_vessel SET speed_current=NEW.speed_after WHERE senc_vessel_id=NEW.senc_vessel_id;
 RETURN NEW;
END $$;
CREATE TRIGGER senc_pilot_movement_valid BEFORE INSERT ON senc_pilot_movement_receipt
FOR EACH ROW EXECUTE FUNCTION senc_apply_pilot_movement();
CREATE FUNCTION senc_reject_pilot_movement_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Pilot movement receipts are immutable'; END $$;
CREATE TRIGGER senc_pilot_movement_immutable BEFORE UPDATE OR DELETE ON senc_pilot_movement_receipt
FOR EACH ROW EXECUTE FUNCTION senc_reject_pilot_movement_mutation();
