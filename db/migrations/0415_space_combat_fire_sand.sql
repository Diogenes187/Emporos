INSERT INTO src_locator(source_work_id,source_artifact_id,locator_type,heading_path,display_citation)
SELECT a.source_work_id,a.source_artifact_id,'heading','Space Combat > Reactions > Fire Sand',
 CASE w.work_code WHEN 'cepheus-engine.ogn' THEN 'Cepheus Engine SRD, Space Combat: Fire Sand'
 ELSE 'Cepheus Engine v9.1, Space Combat: Fire Sand' END FROM src_artifact a JOIN src_work w USING(source_work_id)
WHERE (w.work_code='cepheus-engine.ogn' AND a.source_uri LIKE '%cepheus-engine-space-combat/')
 OR (w.work_code='cepheus-engine.github-v9.1' AND a.source_uri='src/book2/space-combat.md') ON CONFLICT DO NOTHING;
WITH p AS (SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine')
INSERT INTO rule_rule(content_package_id,rule_code,name,rule_category,rule_status,description)
SELECT content_package_id,'combat.space.fire-sand','Fire Sand','combat','approved','Sandcaster reaction against beams or boarding parties.' FROM p;
CREATE TABLE rule_space_combat_fire_sand(
 rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),skill_rule_id bigint NOT NULL REFERENCES rule_skill(rule_id),
 difficulty_rule_id bigint NOT NULL REFERENCES rule_difficulty(rule_id),canisters_per_reaction smallint NOT NULL CHECK(canisters_per_reaction=1),
 beam_reduction_dice_per_beam smallint NOT NULL CHECK(beam_reduction_dice_per_beam=1),beam_reduction_die_sides smallint NOT NULL CHECK(beam_reduction_die_sides=6),
 resolve_each_beam_separately boolean NOT NULL,boarding_damage_dice smallint NOT NULL CHECK(boarding_damage_dice=8),
 boarding_damage_die_sides smallint NOT NULL CHECK(boarding_damage_die_sides=6),ammunition_consumed_on_failure boolean NOT NULL
);
INSERT INTO rule_space_combat_fire_sand SELECT fire.rule_id,skill.rule_id,difficulty.rule_id,1,1,6,true,8,6,true
FROM rule_rule fire CROSS JOIN rule_rule skill CROSS JOIN rule_rule difficulty
WHERE fire.rule_code='combat.space.fire-sand' AND skill.rule_code='skill.turret-weapons' AND difficulty.rule_code='difficulty.average';
INSERT INTO src_record_provenance(rule_id,content_package_id,source_locator_id,provenance_class,is_primary_citation)
SELECT r.rule_id,r.content_package_id,l.source_locator_id,CASE w.work_code WHEN 'cepheus-engine.ogn' THEN 'direct' ELSE 'corroborating' END,w.work_code='cepheus-engine.ogn'
FROM rule_rule r CROSS JOIN src_locator l JOIN src_work w USING(source_work_id) WHERE r.rule_code='combat.space.fire-sand'
 AND l.heading_path='Space Combat > Reactions > Fire Sand' AND w.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1');

CREATE TABLE senc_fire_sand_attempt_receipt(
 fire_sand_attempt_receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,reaction_id bigint NOT NULL UNIQUE REFERENCES senc_reaction(reaction_id),
 engagement_id bigint NOT NULL,campaign_id bigint NOT NULL,space_combat_round_id bigint NOT NULL,round_number integer NOT NULL CHECK(round_number>0),
 senc_vessel_id bigint NOT NULL,gunner_assignment_id bigint NOT NULL,gunner_ship_id bigint NOT NULL,
 task_command_id bigint NOT NULL UNIQUE REFERENCES cmd_actor_task_receipt(command_id),task_effect smallint NOT NULL,task_succeeded boolean NOT NULL,
 incoming_beam_count smallint NOT NULL CHECK(incoming_beam_count>0),sand_before numeric NOT NULL CHECK(sand_before>=1),sand_after numeric NOT NULL CHECK(sand_after=sand_before-1),
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),FOREIGN KEY(space_combat_round_id,engagement_id,campaign_id) REFERENCES senc_round(space_combat_round_id,engagement_id,campaign_id),
 FOREIGN KEY(senc_vessel_id,engagement_id,campaign_id) REFERENCES senc_vessel(senc_vessel_id,engagement_id,campaign_id),
 FOREIGN KEY(gunner_assignment_id,gunner_ship_id,campaign_id) REFERENCES ship_crew_assignment(crew_assignment_id,ship_id,campaign_id)
);
CREATE TABLE senc_fire_sand_ammo_receipt(
 fire_sand_attempt_receipt_id bigint PRIMARY KEY REFERENCES senc_fire_sand_attempt_receipt(fire_sand_attempt_receipt_id),
 resource_movement_id bigint NOT NULL UNIQUE REFERENCES ship_resource_movement(resource_movement_id)
);
CREATE TABLE senc_fire_sand_reduction_die(
 fire_sand_attempt_receipt_id bigint NOT NULL REFERENCES senc_fire_sand_attempt_receipt(fire_sand_attempt_receipt_id),
 beam_order smallint NOT NULL CHECK(beam_order>0),result smallint NOT NULL CHECK(result BETWEEN 1 AND 6),
 PRIMARY KEY(fire_sand_attempt_receipt_id,beam_order)
);
CREATE TABLE senc_fire_sand_final_receipt(
 fire_sand_attempt_receipt_id bigint PRIMARY KEY REFERENCES senc_fire_sand_attempt_receipt(fire_sand_attempt_receipt_id),
 total_beam_damage_reduction smallint NOT NULL CHECK(total_beam_damage_reduction>=0),recorded_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE FUNCTION senc_validate_fire_sand_attempt() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE reaction_row record; task record; skill bigint; average bigint; sand numeric; class_id bigint; movement bigint; actual_round integer;
BEGIN
 SELECT trigger_action.action_code AS trigger_code,trigger_action.space_combat_round_id,trigger_action.target_vessel_id,
  reacting_action.action_code,turn.senc_vessel_id,turn.crew_assignment_id,assignment.ship_id,assignment.actor_id,
  assignment.duty_status,definition.position_code INTO reaction_row FROM senc_reaction reaction
 JOIN senc_action trigger_action ON trigger_action.space_combat_action_id=reaction.triggering_action_id
 JOIN senc_action reacting_action ON reacting_action.space_combat_action_id=reaction.reacting_action_id
 JOIN senc_crew_turn turn ON turn.crew_turn_id=reacting_action.crew_turn_id JOIN ship_crew_assignment assignment USING(crew_assignment_id)
 JOIN ship_crew_position ps USING(ship_crew_position_id) JOIN ship_crew_position_definition definition USING(crew_position_rule_id)
 WHERE reaction.reaction_id=NEW.reaction_id;
 SELECT actor_id,skill_rule_id,difficulty_rule_id,effect,succeeded INTO task FROM cmd_actor_task_receipt WHERE command_id=NEW.task_command_id;
 SELECT rule_id INTO skill FROM rule_rule WHERE rule_code='skill.turret-weapons'; SELECT rule_id INTO average FROM rule_rule WHERE rule_code='difficulty.average';
 SELECT class.ship_class_rule_id INTO class_id FROM ship_ship class WHERE ship_id=NEW.gunner_ship_id;
 SELECT current_quantity INTO sand FROM ship_resource WHERE ship_id=NEW.gunner_ship_id AND resource_type_code='sand' FOR UPDATE;
 SELECT round_number INTO actual_round FROM senc_round WHERE space_combat_round_id=NEW.space_combat_round_id;
 IF reaction_row.trigger_code<>'attack' OR reaction_row.action_code<>'fire-sand' OR reaction_row.space_combat_round_id<>NEW.space_combat_round_id
  OR reaction_row.target_vessel_id<>NEW.senc_vessel_id OR reaction_row.senc_vessel_id<>NEW.senc_vessel_id
  OR reaction_row.crew_assignment_id<>NEW.gunner_assignment_id OR reaction_row.ship_id<>NEW.gunner_ship_id
  OR reaction_row.actor_id<>task.actor_id OR reaction_row.duty_status<>'active' OR reaction_row.position_code<>'gunner'
  OR task.skill_rule_id<>skill OR task.difficulty_rule_id<>average OR task.effect<>NEW.task_effect OR task.succeeded<>NEW.task_succeeded
  OR actual_round<>NEW.round_number OR sand<>NEW.sand_before OR NOT EXISTS(
   SELECT 1 FROM ship_class_weapon cw JOIN ship_weapon_definition wd USING(weapon_rule_id)
   WHERE cw.ship_class_rule_id=class_id AND wd.weapon_code='sandcaster') THEN
  RAISE EXCEPTION 'Fire Sand requires a matching beam reaction, active Gunner, sandcaster, task, and ammunition' USING ERRCODE='23514'; END IF;
 INSERT INTO ship_resource_movement(ship_id,campaign_id,resource_type_code,quantity_delta,balance_after,movement_kind)
 VALUES(NEW.gunner_ship_id,NEW.campaign_id,'sand',-1,NEW.sand_after,'consume') RETURNING resource_movement_id INTO movement;
 INSERT INTO senc_fire_sand_ammo_receipt VALUES(NEW.fire_sand_attempt_receipt_id,movement);
 RETURN NEW;
END $$;
CREATE TRIGGER senc_fire_sand_attempt_valid AFTER INSERT ON senc_fire_sand_attempt_receipt FOR EACH ROW EXECUTE FUNCTION senc_validate_fire_sand_attempt();
CREATE FUNCTION senc_guard_fire_sand_die() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE a senc_fire_sand_attempt_receipt%ROWTYPE; BEGIN
 SELECT * INTO STRICT a FROM senc_fire_sand_attempt_receipt WHERE fire_sand_attempt_receipt_id=NEW.fire_sand_attempt_receipt_id FOR UPDATE;
 IF NOT a.task_succeeded OR NEW.beam_order>a.incoming_beam_count OR EXISTS(SELECT 1 FROM senc_fire_sand_final_receipt WHERE fire_sand_attempt_receipt_id=NEW.fire_sand_attempt_receipt_id)
 THEN RAISE EXCEPTION 'Fire Sand reduction dice require an unfinalized successful beam reaction' USING ERRCODE='23514'; END IF; RETURN NEW; END $$;
CREATE TRIGGER senc_fire_sand_die_valid BEFORE INSERT ON senc_fire_sand_reduction_die FOR EACH ROW EXECUTE FUNCTION senc_guard_fire_sand_die();
CREATE FUNCTION senc_validate_fire_sand_final() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE a senc_fire_sand_attempt_receipt%ROWTYPE; n integer; total integer; BEGIN
 SELECT * INTO STRICT a FROM senc_fire_sand_attempt_receipt WHERE fire_sand_attempt_receipt_id=NEW.fire_sand_attempt_receipt_id FOR UPDATE;
 SELECT count(*),coalesce(sum(result),0) INTO n,total FROM senc_fire_sand_reduction_die WHERE fire_sand_attempt_receipt_id=NEW.fire_sand_attempt_receipt_id;
 IF n<>(CASE WHEN a.task_succeeded THEN a.incoming_beam_count ELSE 0 END) OR total<>NEW.total_beam_damage_reduction
 THEN RAISE EXCEPTION 'Fire Sand final receipt does not contain one reduction die per incoming beam' USING ERRCODE='23514'; END IF; RETURN NEW; END $$;
CREATE TRIGGER senc_fire_sand_final_valid BEFORE INSERT ON senc_fire_sand_final_receipt FOR EACH ROW EXECUTE FUNCTION senc_validate_fire_sand_final();
CREATE FUNCTION senc_reject_fire_sand_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Fire Sand receipts and dice are immutable'; END $$;
CREATE TRIGGER senc_fire_sand_attempt_immutable BEFORE UPDATE OR DELETE ON senc_fire_sand_attempt_receipt FOR EACH ROW EXECUTE FUNCTION senc_reject_fire_sand_mutation();
CREATE TRIGGER senc_fire_sand_die_immutable BEFORE UPDATE OR DELETE ON senc_fire_sand_reduction_die FOR EACH ROW EXECUTE FUNCTION senc_reject_fire_sand_mutation();
CREATE TRIGGER senc_fire_sand_final_immutable BEFORE UPDATE OR DELETE ON senc_fire_sand_final_receipt FOR EACH ROW EXECUTE FUNCTION senc_reject_fire_sand_mutation();
CREATE TRIGGER senc_fire_sand_ammo_immutable BEFORE UPDATE OR DELETE ON senc_fire_sand_ammo_receipt FOR EACH ROW EXECUTE FUNCTION senc_reject_fire_sand_mutation();
