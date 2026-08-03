INSERT INTO src_locator(source_work_id,source_artifact_id,locator_type,heading_path,display_citation)
SELECT artifact.source_work_id,artifact.source_artifact_id,'heading',
       'Space Combat > Significant Actions > Evasive Maneuvers',
       CASE work.work_code WHEN 'cepheus-engine.ogn'
         THEN 'Cepheus Engine SRD, Space Combat: Evasive Maneuvers'
         ELSE 'Cepheus Engine v9.1, Space Combat: Evasive Maneuvers' END
FROM src_artifact artifact JOIN src_work work USING(source_work_id)
WHERE (work.work_code='cepheus-engine.ogn' AND artifact.source_uri LIKE '%cepheus-engine-space-combat/')
   OR (work.work_code='cepheus-engine.github-v9.1' AND artifact.source_uri='src/book2/space-combat.md')
ON CONFLICT DO NOTHING;

WITH package AS (SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine')
INSERT INTO rule_rule(content_package_id,rule_code,name,rule_category,rule_status,description)
SELECT content_package_id,'combat.space.evasive-maneuvers','Space Combat Evasive Maneuvers',
       'combat','approved','Pilot maneuver imposing an attack penalty against the vessel for the current combat round.'
FROM package;

CREATE TABLE rule_space_combat_evasive_maneuvers(
 rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
 skill_rule_id bigint NOT NULL REFERENCES rule_skill(rule_id),
 difficulty_rule_id bigint NOT NULL REFERENCES rule_difficulty(rule_id),
 success_attack_penalty smallint NOT NULL CHECK(success_attack_penalty=-1),
 exceptional_effect_threshold smallint NOT NULL CHECK(exceptional_effect_threshold=6),
 exceptional_attack_penalty smallint NOT NULL CHECK(exceptional_attack_penalty=-2),
 applies_to_attacks_targeting_vessel boolean NOT NULL,
 applies_current_round_only boolean NOT NULL,
 failure_consumes_action boolean NOT NULL
);
INSERT INTO rule_space_combat_evasive_maneuvers
SELECT action.rule_id,skill.rule_id,difficulty.rule_id,-1,6,-2,true,true,true
FROM rule_rule action CROSS JOIN rule_rule skill CROSS JOIN rule_rule difficulty
WHERE action.rule_code='combat.space.evasive-maneuvers'
  AND skill.rule_code='skill.piloting'
  AND difficulty.rule_code='difficulty.average';

INSERT INTO src_record_provenance(rule_id,content_package_id,source_locator_id,provenance_class,is_primary_citation)
SELECT rule.rule_id,rule.content_package_id,locator.source_locator_id,
       CASE work.work_code WHEN 'cepheus-engine.ogn' THEN 'direct' ELSE 'corroborating' END,
       work.work_code='cepheus-engine.ogn'
FROM rule_rule rule CROSS JOIN src_locator locator JOIN src_work work USING(source_work_id)
WHERE rule.rule_code='combat.space.evasive-maneuvers'
  AND locator.heading_path='Space Combat > Significant Actions > Evasive Maneuvers'
  AND work.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1');

CREATE TABLE senc_evasive_maneuver_receipt(
 evasive_maneuver_receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 engagement_id bigint NOT NULL,
 campaign_id bigint NOT NULL,
 space_combat_round_id bigint NOT NULL,
 round_number integer NOT NULL CHECK(round_number>0),
 senc_vessel_id bigint NOT NULL,
 action_id bigint NOT NULL UNIQUE,
 pilot_assignment_id bigint NOT NULL,
 pilot_ship_id bigint NOT NULL,
 task_command_id bigint NOT NULL UNIQUE REFERENCES cmd_actor_task_receipt(command_id),
 task_effect smallint NOT NULL,
 task_succeeded boolean NOT NULL,
 attack_penalty smallint NOT NULL CHECK(attack_penalty IN(-2,-1,0)),
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(space_combat_round_id,engagement_id,campaign_id)
  REFERENCES senc_round(space_combat_round_id,engagement_id,campaign_id),
 FOREIGN KEY(senc_vessel_id,engagement_id,campaign_id)
  REFERENCES senc_vessel(senc_vessel_id,engagement_id,campaign_id),
 FOREIGN KEY(action_id,engagement_id,campaign_id)
  REFERENCES senc_action(space_combat_action_id,engagement_id,campaign_id),
 FOREIGN KEY(pilot_assignment_id,pilot_ship_id,campaign_id)
  REFERENCES ship_crew_assignment(crew_assignment_id,ship_id,campaign_id),
 UNIQUE(engagement_id,senc_vessel_id,round_number),
 CHECK(attack_penalty=CASE WHEN NOT task_succeeded THEN 0 WHEN task_effect>=6 THEN -2 ELSE -1 END)
);

CREATE FUNCTION senc_validate_evasive_maneuver_receipt()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE action_row record; task_row record; actual_round integer; piloting bigint; average bigint;
BEGIN
 SELECT action.action_code,action.space_combat_round_id,turn.senc_vessel_id,
        turn.crew_assignment_id,assignment.ship_id,assignment.actor_id,
        assignment.duty_status,definition.position_code
 INTO action_row
 FROM senc_action action JOIN senc_crew_turn turn USING(crew_turn_id)
 JOIN ship_crew_assignment assignment USING(crew_assignment_id)
 JOIN ship_crew_position position_state USING(ship_crew_position_id)
 JOIN ship_crew_position_definition definition USING(crew_position_rule_id)
 WHERE action.space_combat_action_id=NEW.action_id;
 SELECT actor_id,skill_rule_id,difficulty_rule_id,effect,succeeded INTO task_row
 FROM cmd_actor_task_receipt WHERE command_id=NEW.task_command_id;
 SELECT rule_id INTO STRICT piloting FROM rule_rule WHERE rule_code='skill.piloting';
 SELECT rule_id INTO STRICT average FROM rule_rule WHERE rule_code='difficulty.average';
 SELECT round_number INTO actual_round FROM senc_round WHERE space_combat_round_id=NEW.space_combat_round_id;
 IF action_row.action_code<>'evasive-maneuvers'
    OR action_row.space_combat_round_id<>NEW.space_combat_round_id
    OR action_row.senc_vessel_id<>NEW.senc_vessel_id
    OR action_row.crew_assignment_id<>NEW.pilot_assignment_id
    OR action_row.ship_id<>NEW.pilot_ship_id
    OR action_row.duty_status<>'active' OR action_row.position_code<>'pilot'
    OR task_row.actor_id<>action_row.actor_id
    OR task_row.skill_rule_id<>piloting OR task_row.difficulty_rule_id<>average
    OR task_row.effect<>NEW.task_effect OR task_row.succeeded<>NEW.task_succeeded
    OR actual_round<>NEW.round_number THEN
   RAISE EXCEPTION 'Evasive Maneuvers receipt does not match its active Pilot action and Piloting check'
     USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER senc_evasive_maneuver_valid BEFORE INSERT ON senc_evasive_maneuver_receipt
FOR EACH ROW EXECUTE FUNCTION senc_validate_evasive_maneuver_receipt();

CREATE FUNCTION senc_reject_evasive_maneuver_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Evasive Maneuvers receipts are immutable'; END $$;
CREATE TRIGGER senc_evasive_maneuver_immutable
BEFORE UPDATE OR DELETE ON senc_evasive_maneuver_receipt
FOR EACH ROW EXECUTE FUNCTION senc_reject_evasive_maneuver_mutation();
