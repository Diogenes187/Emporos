INSERT INTO src_locator(source_work_id,source_artifact_id,locator_type,heading_path,display_citation)
SELECT a.source_work_id,a.source_artifact_id,'heading',v.heading,
 CASE w.work_code WHEN 'cepheus-engine.ogn' THEN 'Cepheus Engine SRD, Space Combat: '||v.label
 ELSE 'Cepheus Engine v9.1, Space Combat: '||v.label END
FROM src_artifact a JOIN src_work w USING(source_work_id)
CROSS JOIN (VALUES ('Space Combat > Reactions','Reactions'),('Space Combat > Reactions > Dodge Incoming Fire','Dodge Incoming Fire')) v(heading,label)
WHERE (w.work_code='cepheus-engine.ogn' AND a.source_uri LIKE '%cepheus-engine-space-combat/')
 OR (w.work_code='cepheus-engine.github-v9.1' AND a.source_uri='src/book2/space-combat.md') ON CONFLICT DO NOTHING;
WITH p AS (SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine')
INSERT INTO rule_rule(content_package_id,rule_code,name,rule_category,rule_status,description)
SELECT content_package_id,v.code,v.name,'combat','approved',v.description FROM p CROSS JOIN (VALUES
 ('combat.space.reactions','Space Combat Reactions','Initiative-banded vessel reaction economy.'),
 ('combat.space.dodge','Dodge Incoming Fire','Pilot reaction imposing an attack penalty on success.')
) v(code,name,description);
CREATE TABLE rule_space_combat_reaction_system(
 rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),targeted_beam_allows_reaction boolean NOT NULL,
 incoming_missile_allows_reaction boolean NOT NULL,attempted_boarding_allows_reaction boolean NOT NULL,
 initiative_determines_limit boolean NOT NULL
);
INSERT INTO rule_space_combat_reaction_system SELECT rule_id,true,true,true,true FROM rule_rule WHERE rule_code='combat.space.reactions';
CREATE TABLE rule_space_combat_reaction_limit(
 reaction_rule_id bigint NOT NULL REFERENCES rule_space_combat_reaction_system(rule_id),minimum_initiative integer NOT NULL,
 maximum_initiative integer,maximum_reactions smallint NOT NULL CHECK(maximum_reactions BETWEEN 1 AND 4),
 PRIMARY KEY(reaction_rule_id,minimum_initiative),CHECK(maximum_initiative IS NULL OR maximum_initiative>=minimum_initiative)
);
INSERT INTO rule_space_combat_reaction_limit SELECT r.rule_id,v.minimum,v.maximum,v.reactions
FROM rule_rule r CROSS JOIN (VALUES(0,4,1),(5,8,2),(9,12,3),(13,NULL::integer,4)) v(minimum,maximum,reactions)
WHERE r.rule_code='combat.space.reactions';
CREATE TABLE rule_space_combat_dodge(
 rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),skill_rule_id bigint NOT NULL REFERENCES rule_skill(rule_id),
 difficulty_rule_id bigint NOT NULL REFERENCES rule_difficulty(rule_id),success_attack_modifier smallint NOT NULL CHECK(success_attack_modifier=-2),
 failure_attack_modifier smallint NOT NULL CHECK(failure_attack_modifier=0),reaction_consumed_on_failure boolean NOT NULL
);
INSERT INTO rule_space_combat_dodge SELECT dodge.rule_id,pilot.rule_id,difficulty.rule_id,-2,0,true
FROM rule_rule dodge CROSS JOIN rule_rule pilot CROSS JOIN rule_rule difficulty
WHERE dodge.rule_code='combat.space.dodge' AND pilot.rule_code='skill.piloting' AND difficulty.rule_code='difficulty.average';
INSERT INTO src_record_provenance(rule_id,content_package_id,source_locator_id,provenance_class,is_primary_citation)
SELECT r.rule_id,r.content_package_id,l.source_locator_id,CASE w.work_code WHEN 'cepheus-engine.ogn' THEN 'direct' ELSE 'corroborating' END,w.work_code='cepheus-engine.ogn'
FROM rule_rule r JOIN src_locator l ON l.heading_path=CASE r.rule_code WHEN 'combat.space.reactions' THEN 'Space Combat > Reactions' ELSE 'Space Combat > Reactions > Dodge Incoming Fire' END
JOIN src_work w USING(source_work_id) WHERE r.rule_code IN('combat.space.reactions','combat.space.dodge')
 AND w.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1');

CREATE FUNCTION senc_validate_reaction_budget() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE trigger_row record; reacting_row record; initiative integer; reaction_limit integer; used integer;
BEGIN
 SELECT action.target_vessel_id,action.space_combat_round_id INTO trigger_row FROM senc_action action WHERE action.space_combat_action_id=NEW.triggering_action_id;
 SELECT turn.senc_vessel_id,action.space_combat_round_id,action.action_code INTO reacting_row
 FROM senc_action action JOIN senc_crew_turn turn USING(crew_turn_id) WHERE action.space_combat_action_id=NEW.reacting_action_id;
 SELECT initiative_snapshot INTO initiative FROM senc_vessel_turn_order_receipt WHERE space_combat_round_id=reacting_row.space_combat_round_id AND senc_vessel_id=reacting_row.senc_vessel_id;
 SELECT maximum_reactions INTO reaction_limit FROM rule_space_combat_reaction_limit limit_row
 WHERE initiative>=minimum_initiative AND (maximum_initiative IS NULL OR initiative<=maximum_initiative);
 SELECT count(*) INTO used FROM senc_reaction reaction JOIN senc_action action ON action.space_combat_action_id=reaction.reacting_action_id
 JOIN senc_crew_turn turn USING(crew_turn_id) WHERE action.space_combat_round_id=reacting_row.space_combat_round_id AND turn.senc_vessel_id=reacting_row.senc_vessel_id;
 IF trigger_row.target_vessel_id<>reacting_row.senc_vessel_id OR trigger_row.space_combat_round_id<>reacting_row.space_combat_round_id
  OR used>=reaction_limit THEN RAISE EXCEPTION 'Space combat reaction target, round, or Initiative budget is invalid' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER senc_reaction_budget_valid BEFORE INSERT ON senc_reaction FOR EACH ROW EXECUTE FUNCTION senc_validate_reaction_budget();

CREATE TABLE senc_dodge_receipt(
 dodge_receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,reaction_id bigint NOT NULL UNIQUE REFERENCES senc_reaction(reaction_id),
 engagement_id bigint NOT NULL,campaign_id bigint NOT NULL,space_combat_round_id bigint NOT NULL,round_number integer NOT NULL CHECK(round_number>0),
 senc_vessel_id bigint NOT NULL,pilot_assignment_id bigint NOT NULL,pilot_ship_id bigint NOT NULL,
 task_command_id bigint NOT NULL UNIQUE REFERENCES cmd_actor_task_receipt(command_id),task_effect smallint NOT NULL,task_succeeded boolean NOT NULL,
 attack_modifier smallint NOT NULL CHECK(attack_modifier IN(-2,0)),recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(space_combat_round_id,engagement_id,campaign_id) REFERENCES senc_round(space_combat_round_id,engagement_id,campaign_id),
 FOREIGN KEY(senc_vessel_id,engagement_id,campaign_id) REFERENCES senc_vessel(senc_vessel_id,engagement_id,campaign_id),
 FOREIGN KEY(pilot_assignment_id,pilot_ship_id,campaign_id) REFERENCES ship_crew_assignment(crew_assignment_id,ship_id,campaign_id),
 CHECK(attack_modifier=CASE WHEN task_succeeded THEN -2 ELSE 0 END)
);
CREATE FUNCTION senc_validate_dodge_receipt() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE reaction_row record; task record; pilot bigint; average bigint; actual_round integer;
BEGIN
 SELECT trigger_action.space_combat_round_id,trigger_action.target_vessel_id,reacting_action.action_code,
  turn.senc_vessel_id,turn.crew_assignment_id,assignment.ship_id,assignment.actor_id,assignment.duty_status,definition.position_code INTO reaction_row
 FROM senc_reaction reaction JOIN senc_action trigger_action ON trigger_action.space_combat_action_id=reaction.triggering_action_id
 JOIN senc_action reacting_action ON reacting_action.space_combat_action_id=reaction.reacting_action_id
 JOIN senc_crew_turn turn ON turn.crew_turn_id=reacting_action.crew_turn_id JOIN ship_crew_assignment assignment USING(crew_assignment_id)
 JOIN ship_crew_position ps USING(ship_crew_position_id) JOIN ship_crew_position_definition definition USING(crew_position_rule_id)
 WHERE reaction.reaction_id=NEW.reaction_id;
 SELECT actor_id,skill_rule_id,difficulty_rule_id,effect,succeeded INTO task FROM cmd_actor_task_receipt WHERE command_id=NEW.task_command_id;
 SELECT rule_id INTO pilot FROM rule_rule WHERE rule_code='skill.piloting'; SELECT rule_id INTO average FROM rule_rule WHERE rule_code='difficulty.average';
 SELECT round_number INTO actual_round FROM senc_round WHERE space_combat_round_id=NEW.space_combat_round_id;
 IF reaction_row.action_code<>'dodge' OR reaction_row.space_combat_round_id<>NEW.space_combat_round_id
  OR reaction_row.target_vessel_id<>NEW.senc_vessel_id OR reaction_row.senc_vessel_id<>NEW.senc_vessel_id
  OR reaction_row.crew_assignment_id<>NEW.pilot_assignment_id OR reaction_row.ship_id<>NEW.pilot_ship_id
  OR reaction_row.actor_id<>task.actor_id OR reaction_row.duty_status<>'active' OR reaction_row.position_code<>'pilot'
  OR task.skill_rule_id<>pilot OR task.difficulty_rule_id<>average OR task.effect<>NEW.task_effect
  OR task.succeeded<>NEW.task_succeeded OR actual_round<>NEW.round_number THEN
  RAISE EXCEPTION 'Dodge receipt does not match its reaction and active Pilot check' USING ERRCODE='23514'; END IF; RETURN NEW;
END $$;
CREATE TRIGGER senc_dodge_valid BEFORE INSERT ON senc_dodge_receipt FOR EACH ROW EXECUTE FUNCTION senc_validate_dodge_receipt();
CREATE FUNCTION senc_reject_dodge_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Dodge receipts are immutable'; END $$;
CREATE TRIGGER senc_dodge_immutable BEFORE UPDATE OR DELETE ON senc_dodge_receipt FOR EACH ROW EXECUTE FUNCTION senc_reject_dodge_mutation();
