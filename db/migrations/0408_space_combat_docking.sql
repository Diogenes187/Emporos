INSERT INTO src_locator(source_work_id,source_artifact_id,locator_type,heading_path,display_citation)
SELECT artifact.source_work_id,artifact.source_artifact_id,'heading',
 'Space Combat > Significant Actions > Dock with Another Vessel',
 CASE work.work_code WHEN 'cepheus-engine.ogn' THEN 'Cepheus Engine SRD, Space Combat: Dock with Another Vessel'
 ELSE 'Cepheus Engine v9.1, Space Combat: Dock with Another Vessel' END
FROM src_artifact artifact JOIN src_work work USING(source_work_id)
WHERE (work.work_code='cepheus-engine.ogn' AND artifact.source_uri LIKE '%cepheus-engine-space-combat/')
 OR (work.work_code='cepheus-engine.github-v9.1' AND artifact.source_uri='src/book2/space-combat.md')
ON CONFLICT DO NOTHING;

WITH package AS (SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine')
INSERT INTO rule_rule(content_package_id,rule_code,name,rule_category,rule_status,description)
SELECT content_package_id,'combat.space.docking','Space Combat Docking','combat','approved',
 'Adjacent vessel docking, including unresisted and opposed Piloting resolution.' FROM package;

CREATE TABLE rule_space_combat_docking(
 rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
 skill_rule_id bigint NOT NULL REFERENCES rule_skill(rule_id),
 unresisted_difficulty_rule_id bigint NOT NULL REFERENCES rule_difficulty(rule_id),
 resisted_docking_modifier smallint NOT NULL CHECK(resisted_docking_modifier=-2),
 required_start_range_code text NOT NULL REFERENCES rule_space_range_band(range_band_code)
  CHECK(required_start_range_code='adjacent'),
 success_range_code text NOT NULL REFERENCES rule_space_range_band(range_band_code)
  CHECK(success_range_code='docked'),
 opposed_tie_uses_characteristic boolean NOT NULL,
 full_tie_requires_reroll boolean NOT NULL,
 success_allows_boarding boolean NOT NULL
);
INSERT INTO rule_space_combat_docking
SELECT action.rule_id,skill.rule_id,difficulty.rule_id,-2,'adjacent','docked',true,true,true
FROM rule_rule action CROSS JOIN rule_rule skill CROSS JOIN rule_rule difficulty
WHERE action.rule_code='combat.space.docking' AND skill.rule_code='skill.piloting'
 AND difficulty.rule_code='difficulty.average';

INSERT INTO rule_interpretation(rule_id,interpretation_type,decision_register_entry,rationale)
SELECT rule_id,'agreed_interpretation','CE-SC-004',
 'Combat docking may be attempted only from Adjacent range; successful docking atomically changes the authoritative pairwise range to Docked.'
FROM rule_rule WHERE rule_code='combat.space.docking';

INSERT INTO src_record_provenance(rule_id,content_package_id,source_locator_id,provenance_class,is_primary_citation)
SELECT rule.rule_id,rule.content_package_id,locator.source_locator_id,
 CASE work.work_code WHEN 'cepheus-engine.ogn' THEN 'direct' ELSE 'corroborating' END,
 work.work_code='cepheus-engine.ogn'
FROM rule_rule rule CROSS JOIN src_locator locator JOIN src_work work USING(source_work_id)
WHERE rule.rule_code='combat.space.docking'
 AND locator.heading_path='Space Combat > Significant Actions > Dock with Another Vessel'
 AND work.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1');

CREATE TABLE senc_docking_receipt(
 docking_receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 engagement_id bigint NOT NULL,campaign_id bigint NOT NULL,
 space_combat_round_id bigint NOT NULL,round_number integer NOT NULL CHECK(round_number>0),
 docking_vessel_id bigint NOT NULL,target_vessel_id bigint NOT NULL,
 action_id bigint NOT NULL UNIQUE,docking_pilot_assignment_id bigint NOT NULL,
 docking_pilot_ship_id bigint NOT NULL,resisted boolean NOT NULL,
 docking_task_command_id bigint NOT NULL UNIQUE REFERENCES cmd_actor_task_receipt(command_id),
 opposing_task_command_id bigint UNIQUE REFERENCES cmd_actor_task_receipt(command_id),
 docking_effect smallint NOT NULL,opposing_effect smallint,
 docking_characteristic_value smallint NOT NULL,opposing_characteristic_value smallint,
 resolution_status text NOT NULL CHECK(resolution_status IN('succeeded','failed','reroll-required')),
 range_band_before text NOT NULL REFERENCES rule_space_range_band(range_band_code),
 range_band_after text NOT NULL REFERENCES rule_space_range_band(range_band_code),
 range_version_before bigint NOT NULL CHECK(range_version_before>0),
 range_version_after bigint NOT NULL CHECK(range_version_after>0),
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(space_combat_round_id,engagement_id,campaign_id) REFERENCES senc_round(space_combat_round_id,engagement_id,campaign_id),
 FOREIGN KEY(docking_vessel_id,engagement_id,campaign_id) REFERENCES senc_vessel(senc_vessel_id,engagement_id,campaign_id),
 FOREIGN KEY(target_vessel_id,engagement_id,campaign_id) REFERENCES senc_vessel(senc_vessel_id,engagement_id,campaign_id),
 FOREIGN KEY(action_id,engagement_id,campaign_id) REFERENCES senc_action(space_combat_action_id,engagement_id,campaign_id),
 FOREIGN KEY(docking_pilot_assignment_id,docking_pilot_ship_id,campaign_id)
  REFERENCES ship_crew_assignment(crew_assignment_id,ship_id,campaign_id),
 CHECK(docking_vessel_id<>target_vessel_id),
 CHECK((resisted AND opposing_task_command_id IS NOT NULL AND opposing_effect IS NOT NULL
   AND opposing_characteristic_value IS NOT NULL)
  OR (NOT resisted AND opposing_task_command_id IS NULL AND opposing_effect IS NULL
   AND opposing_characteristic_value IS NULL)),
 CHECK(range_band_before='adjacent'),
 CHECK((resolution_status='succeeded' AND range_band_after='docked' AND range_version_after=range_version_before+1)
  OR (resolution_status IN('failed','reroll-required') AND range_band_after=range_band_before
   AND range_version_after=range_version_before))
);

CREATE FUNCTION senc_validate_docking_receipt() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE range_row senc_vessel_range%ROWTYPE; action_row record; docking_task record;
 opposing_task record; opposing_pilot bigint; piloting bigint; average bigint;
 actual_round integer; expected_status text;
BEGIN
 SELECT * INTO STRICT range_row FROM senc_vessel_range WHERE engagement_id=NEW.engagement_id
  AND first_vessel_id=least(NEW.docking_vessel_id,NEW.target_vessel_id)
  AND second_vessel_id=greatest(NEW.docking_vessel_id,NEW.target_vessel_id) FOR UPDATE;
 SELECT action.action_code,action.target_vessel_id,action.space_combat_round_id,turn.senc_vessel_id,
  turn.crew_assignment_id,assignment.ship_id,assignment.actor_id,assignment.duty_status,
  definition.position_code INTO action_row
 FROM senc_action action JOIN senc_crew_turn turn USING(crew_turn_id)
 JOIN ship_crew_assignment assignment USING(crew_assignment_id)
 JOIN ship_crew_position position_state USING(ship_crew_position_id)
 JOIN ship_crew_position_definition definition USING(crew_position_rule_id)
 WHERE action.space_combat_action_id=NEW.action_id;
 SELECT actor_id,skill_rule_id,difficulty_rule_id,effect,succeeded,circumstance_modifier
 INTO docking_task FROM cmd_actor_task_receipt WHERE command_id=NEW.docking_task_command_id;
 SELECT rule_id INTO STRICT piloting FROM rule_rule WHERE rule_code='skill.piloting';
 SELECT rule_id INTO STRICT average FROM rule_rule WHERE rule_code='difficulty.average';
 SELECT round_number INTO actual_round FROM senc_round WHERE space_combat_round_id=NEW.space_combat_round_id;
 IF action_row.action_code<>'dock' OR action_row.target_vessel_id<>NEW.target_vessel_id
  OR action_row.space_combat_round_id<>NEW.space_combat_round_id
  OR action_row.senc_vessel_id<>NEW.docking_vessel_id
  OR action_row.crew_assignment_id<>NEW.docking_pilot_assignment_id
  OR action_row.ship_id<>NEW.docking_pilot_ship_id OR action_row.actor_id<>docking_task.actor_id
  OR action_row.duty_status<>'active' OR action_row.position_code<>'pilot'
  OR docking_task.skill_rule_id<>piloting OR docking_task.effect<>NEW.docking_effect
  OR actual_round<>NEW.round_number OR range_row.range_band_code<>'adjacent'
  OR range_row.range_version<>NEW.range_version_before THEN
  RAISE EXCEPTION 'Docking receipt does not match its adjacent active Pilot action' USING ERRCODE='23514';
 END IF;
 IF NOT NEW.resisted THEN
  IF docking_task.difficulty_rule_id<>average OR docking_task.circumstance_modifier<>0 THEN
   RAISE EXCEPTION 'Unresisted docking requires an Average Piloting check' USING ERRCODE='23514';
  END IF;
  expected_status:=CASE WHEN docking_task.succeeded THEN 'succeeded' ELSE 'failed' END;
 ELSE
  SELECT assignment.actor_id INTO opposing_pilot FROM senc_vessel vessel
  JOIN ship_crew_assignment assignment ON assignment.ship_id=vessel.ship_id AND assignment.duty_status='active'
  JOIN ship_crew_position position_state USING(ship_crew_position_id)
  JOIN ship_crew_position_definition definition USING(crew_position_rule_id)
  WHERE vessel.senc_vessel_id=NEW.target_vessel_id AND definition.position_code='pilot';
  SELECT actor_id,skill_rule_id,effect INTO opposing_task FROM cmd_actor_task_receipt
  WHERE command_id=NEW.opposing_task_command_id;
  IF docking_task.circumstance_modifier<>-2 OR opposing_task.actor_id<>opposing_pilot
   OR opposing_task.skill_rule_id<>piloting OR opposing_task.effect<>NEW.opposing_effect THEN
   RAISE EXCEPTION 'Resisted docking requires opposed Piloting and docking DM-2' USING ERRCODE='23514';
  END IF;
  expected_status:=CASE WHEN NEW.docking_effect>NEW.opposing_effect THEN 'succeeded'
   WHEN NEW.docking_effect<NEW.opposing_effect THEN 'failed'
   WHEN NEW.docking_characteristic_value>NEW.opposing_characteristic_value THEN 'succeeded'
   WHEN NEW.docking_characteristic_value<NEW.opposing_characteristic_value THEN 'failed'
   ELSE 'reroll-required' END;
 END IF;
 IF NEW.resolution_status<>expected_status THEN
  RAISE EXCEPTION 'Docking resolution is inconsistent with its task receipt(s)' USING ERRCODE='23514';
 END IF;
 IF expected_status='succeeded' THEN
  UPDATE senc_vessel_range SET range_band_code='docked',range_version=NEW.range_version_after,
   updated_at=clock_timestamp() WHERE engagement_id=NEW.engagement_id
   AND first_vessel_id=range_row.first_vessel_id AND second_vessel_id=range_row.second_vessel_id;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER senc_docking_valid BEFORE INSERT ON senc_docking_receipt
FOR EACH ROW EXECUTE FUNCTION senc_validate_docking_receipt();
CREATE FUNCTION senc_reject_docking_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Docking receipts are immutable'; END $$;
CREATE TRIGGER senc_docking_immutable BEFORE UPDATE OR DELETE ON senc_docking_receipt
FOR EACH ROW EXECUTE FUNCTION senc_reject_docking_mutation();
