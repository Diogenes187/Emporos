INSERT INTO src_locator(source_work_id,source_artifact_id,locator_type,heading_path,display_citation)
SELECT a.source_work_id,a.source_artifact_id,'heading','Space Combat > Significant Actions > Avoid Collision',
 CASE w.work_code WHEN 'cepheus-engine.ogn' THEN 'Cepheus Engine SRD, Space Combat: Avoid Collision'
 ELSE 'Cepheus Engine v9.1, Space Combat: Avoid Collision' END
FROM src_artifact a JOIN src_work w USING(source_work_id)
WHERE (w.work_code='cepheus-engine.ogn' AND a.source_uri LIKE '%cepheus-engine-space-combat/')
 OR (w.work_code='cepheus-engine.github-v9.1' AND a.source_uri='src/book2/space-combat.md') ON CONFLICT DO NOTHING;
WITH p AS (SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine')
INSERT INTO rule_rule(content_package_id,rule_code,name,rule_category,rule_status,description)
SELECT content_package_id,'combat.space.avoid-collision','Space Combat Avoid Collision','combat','approved',
 'Mandatory Pilot checks and speed-scaled collision damage in close navigational hazards.' FROM p;
CREATE TABLE rule_space_combat_avoid_collision(
 rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),skill_rule_id bigint NOT NULL REFERENCES rule_skill(rule_id),
 applicable_range_codes text[] NOT NULL,check_required_each_turn boolean NOT NULL,
 damage_dice_per_speed_point smallint NOT NULL CHECK(damage_dice_per_speed_point=1),damage_die_sides smallint NOT NULL CHECK(damage_die_sides=6),
 significant_speed_difference_modifier smallint NOT NULL CHECK(significant_speed_difference_modifier=-2),armor_applies boolean NOT NULL
);
INSERT INTO rule_space_combat_avoid_collision SELECT r.rule_id,s.rule_id,ARRAY['close','short'],true,1,6,-2,true
FROM rule_rule r CROSS JOIN rule_rule s WHERE r.rule_code='combat.space.avoid-collision' AND s.rule_code='skill.piloting';
CREATE TABLE rule_space_collision_hazard(
 hazard_code text PRIMARY KEY,hazard_name text NOT NULL,difficulty_rule_id bigint NOT NULL REFERENCES rule_difficulty(rule_id)
);
INSERT INTO rule_space_collision_hazard
SELECT v.code,v.name,d.rule_id FROM (VALUES
 ('traffic-debris','Traffic or Debris','difficulty.average'),('asteroid-light','Asteroid Field, Light Density','difficulty.difficult'),
 ('asteroid-average','Asteroid Field, Average Density','difficulty.very-difficult'),('asteroid-heavy','Asteroid Field, Heavy Density','difficulty.formidable')
) v(code,name,difficulty) JOIN rule_rule d ON d.rule_code=v.difficulty;
INSERT INTO src_record_provenance(rule_id,content_package_id,source_locator_id,provenance_class,is_primary_citation)
SELECT r.rule_id,r.content_package_id,l.source_locator_id,CASE w.work_code WHEN 'cepheus-engine.ogn' THEN 'direct' ELSE 'corroborating' END,w.work_code='cepheus-engine.ogn'
FROM rule_rule r CROSS JOIN src_locator l JOIN src_work w USING(source_work_id)
WHERE r.rule_code='combat.space.avoid-collision' AND l.heading_path='Space Combat > Significant Actions > Avoid Collision'
 AND w.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1');

CREATE TABLE senc_collision_hazard(
 collision_hazard_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,engagement_id bigint NOT NULL,campaign_id bigint NOT NULL,
 space_combat_round_id bigint NOT NULL,round_number integer NOT NULL CHECK(round_number>0),senc_vessel_id bigint NOT NULL,
 hazard_code text NOT NULL REFERENCES rule_space_collision_hazard(hazard_code),significant_speed_difference boolean NOT NULL,
 range_band_snapshot text NOT NULL CHECK(range_band_snapshot IN('close','short')) REFERENCES rule_space_range_band(range_band_code),
 speed_snapshot smallint NOT NULL CHECK(speed_snapshot>=0),declared_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(space_combat_round_id,engagement_id,campaign_id) REFERENCES senc_round(space_combat_round_id,engagement_id,campaign_id),
 FOREIGN KEY(senc_vessel_id,engagement_id,campaign_id) REFERENCES senc_vessel(senc_vessel_id,engagement_id,campaign_id),
 UNIQUE(space_combat_round_id,senc_vessel_id)
);
CREATE TABLE senc_collision_damage_die(
 collision_hazard_id bigint NOT NULL REFERENCES senc_collision_hazard(collision_hazard_id),die_order smallint NOT NULL CHECK(die_order>0),
 result smallint NOT NULL CHECK(result BETWEEN 1 AND 6),PRIMARY KEY(collision_hazard_id,die_order)
);
CREATE TABLE senc_avoid_collision_receipt(
 avoid_collision_receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,collision_hazard_id bigint NOT NULL UNIQUE REFERENCES senc_collision_hazard(collision_hazard_id),
 action_id bigint NOT NULL UNIQUE,task_command_id bigint NOT NULL UNIQUE REFERENCES cmd_actor_task_receipt(command_id),task_effect smallint NOT NULL,
 task_succeeded boolean NOT NULL,rolled_damage smallint NOT NULL CHECK(rolled_damage>=0),ship_id bigint NOT NULL,
 armor_snapshot smallint NOT NULL CHECK(armor_snapshot>=0),net_damage smallint NOT NULL CHECK(net_damage=greatest(rolled_damage-armor_snapshot,0)),
 hull_before smallint NOT NULL,hull_after smallint NOT NULL,structure_before smallint NOT NULL,structure_after smallint NOT NULL,
 version_before bigint NOT NULL,version_after bigint NOT NULL CHECK(version_after=version_before+1),recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 CHECK(hull_after=greatest(hull_before-net_damage,0)),
 CHECK(structure_after=greatest(structure_before-greatest(net_damage-hull_before,0),0)),
 CHECK((task_succeeded AND rolled_damage=0) OR NOT task_succeeded)
);
CREATE TABLE senc_collision_damage_allocation(
 avoid_collision_receipt_id bigint NOT NULL REFERENCES senc_avoid_collision_receipt(avoid_collision_receipt_id),
 damage_kind text NOT NULL CHECK(damage_kind IN('hull','structure')),ship_damage_id bigint NOT NULL UNIQUE REFERENCES ship_damage(ship_damage_id),
 damage_points smallint NOT NULL CHECK(damage_points>0),PRIMARY KEY(avoid_collision_receipt_id,damage_kind)
);

CREATE FUNCTION senc_validate_collision_hazard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE round_no integer; speed numeric; band_ok boolean;
BEGIN
 SELECT round_number INTO round_no FROM senc_round WHERE space_combat_round_id=NEW.space_combat_round_id;
 SELECT speed_current INTO speed FROM senc_vessel WHERE senc_vessel_id=NEW.senc_vessel_id;
 SELECT EXISTS(SELECT 1 FROM senc_vessel_range WHERE engagement_id=NEW.engagement_id AND range_band_code=NEW.range_band_snapshot
  AND (first_vessel_id=NEW.senc_vessel_id OR second_vessel_id=NEW.senc_vessel_id)) INTO band_ok;
 IF round_no<>NEW.round_number OR speed<>NEW.speed_snapshot OR speed<>trunc(speed) OR NOT band_ok THEN
  RAISE EXCEPTION 'Collision hazard requires matching round, integral speed, and Close or Short range' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER senc_collision_hazard_valid BEFORE INSERT ON senc_collision_hazard FOR EACH ROW EXECUTE FUNCTION senc_validate_collision_hazard();
CREATE FUNCTION senc_guard_collision_die() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE h senc_collision_hazard%ROWTYPE;
BEGIN SELECT * INTO STRICT h FROM senc_collision_hazard WHERE collision_hazard_id=NEW.collision_hazard_id FOR UPDATE;
 IF EXISTS(SELECT 1 FROM senc_avoid_collision_receipt WHERE collision_hazard_id=NEW.collision_hazard_id) OR NEW.die_order>h.speed_snapshot THEN
  RAISE EXCEPTION 'Collision dice require an unresolved hazard and current-speed die order' USING ERRCODE='23514'; END IF; RETURN NEW; END $$;
CREATE TRIGGER senc_collision_die_valid BEFORE INSERT ON senc_collision_damage_die FOR EACH ROW EXECUTE FUNCTION senc_guard_collision_die();

CREATE FUNCTION senc_finalize_avoid_collision() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE h senc_collision_hazard%ROWTYPE; action_row record; task record; ship record; base_difficulty bigint; pilot bigint;
 armor integer; die_count integer; die_total integer; hull_damage integer; structure_damage integer; damage_id bigint;
BEGIN
 SELECT * INTO STRICT h FROM senc_collision_hazard WHERE collision_hazard_id=NEW.collision_hazard_id FOR UPDATE;
 SELECT action.action_code,turn.senc_vessel_id,assignment.actor_id,assignment.ship_id,assignment.duty_status,definition.position_code INTO action_row
 FROM senc_action action JOIN senc_crew_turn turn USING(crew_turn_id) JOIN ship_crew_assignment assignment USING(crew_assignment_id)
 JOIN ship_crew_position ps USING(ship_crew_position_id) JOIN ship_crew_position_definition definition USING(crew_position_rule_id)
 WHERE action.space_combat_action_id=NEW.action_id;
 SELECT actor_id,skill_rule_id,difficulty_rule_id,circumstance_modifier,effect,succeeded INTO task FROM cmd_actor_task_receipt WHERE command_id=NEW.task_command_id;
 SELECT difficulty_rule_id INTO base_difficulty FROM rule_space_collision_hazard WHERE hazard_code=h.hazard_code;
 SELECT rule_id INTO pilot FROM rule_rule WHERE rule_code='skill.piloting';
 SELECT vessel.ship_id,ship.ship_class_rule_id,ship.hull_current,ship.structure_current,ship.concurrency_version INTO ship
 FROM senc_vessel vessel JOIN ship_ship ship USING(ship_id) WHERE vessel.senc_vessel_id=h.senc_vessel_id FOR UPDATE OF ship;
 SELECT coalesce((SELECT armor_value FROM ship_class_published_armor WHERE ship_class_rule_id=ship.ship_class_rule_id),
  (SELECT hull.armor_increments*a.protection_per_increment FROM ship_class_design_hull hull JOIN rule_ship_armor_design a USING(armor_code) WHERE hull.ship_class_rule_id=ship.ship_class_rule_id),0) INTO armor;
 SELECT count(*),coalesce(sum(result),0) INTO die_count,die_total FROM senc_collision_damage_die WHERE collision_hazard_id=h.collision_hazard_id;
 IF action_row.action_code<>'avoid-collision' OR action_row.senc_vessel_id<>h.senc_vessel_id OR action_row.actor_id<>task.actor_id
  OR action_row.ship_id<>NEW.ship_id OR action_row.duty_status<>'active' OR action_row.position_code<>'pilot'
  OR task.skill_rule_id<>pilot OR task.difficulty_rule_id<>base_difficulty
  OR task.circumstance_modifier<>(CASE WHEN h.significant_speed_difference THEN -2 ELSE 0 END)
  OR task.effect<>NEW.task_effect OR task.succeeded<>NEW.task_succeeded
  OR die_count<>(CASE WHEN task.succeeded THEN 0 ELSE h.speed_snapshot END) OR die_total<>NEW.rolled_damage
  OR NEW.ship_id<>ship.ship_id OR NEW.armor_snapshot<>armor OR NEW.hull_before<>ship.hull_current
  OR NEW.structure_before<>ship.structure_current OR NEW.version_before<>ship.concurrency_version THEN
  RAISE EXCEPTION 'Avoid Collision receipt fails action, task, dice, or ship-state recomputation' USING ERRCODE='23514'; END IF;
 UPDATE ship_ship SET hull_current=NEW.hull_after,structure_current=NEW.structure_after,concurrency_version=NEW.version_after WHERE ship_id=NEW.ship_id;
 hull_damage:=NEW.hull_before-NEW.hull_after; structure_damage:=NEW.structure_before-NEW.structure_after;
 IF hull_damage>0 THEN INSERT INTO ship_damage(ship_id,campaign_id,target_kind,damage_points,description) VALUES(NEW.ship_id,h.campaign_id,'hull',hull_damage,'Collision hazard') RETURNING ship_damage_id INTO damage_id;
  INSERT INTO senc_collision_damage_allocation VALUES(NEW.avoid_collision_receipt_id,'hull',damage_id,hull_damage); END IF;
 IF structure_damage>0 THEN INSERT INTO ship_damage(ship_id,campaign_id,target_kind,damage_points,description) VALUES(NEW.ship_id,h.campaign_id,'structure',structure_damage,'Collision hazard overflow') RETURNING ship_damage_id INTO damage_id;
  INSERT INTO senc_collision_damage_allocation VALUES(NEW.avoid_collision_receipt_id,'structure',damage_id,structure_damage); END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER senc_avoid_collision_final AFTER INSERT ON senc_avoid_collision_receipt FOR EACH ROW EXECUTE FUNCTION senc_finalize_avoid_collision();
CREATE FUNCTION senc_require_collision_resolution() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
 IF NEW.round_status IN('completed','aborted') AND EXISTS(SELECT 1 FROM senc_collision_hazard h WHERE h.space_combat_round_id=NEW.space_combat_round_id
  AND NOT EXISTS(SELECT 1 FROM senc_avoid_collision_receipt r WHERE r.collision_hazard_id=h.collision_hazard_id)) THEN
  RAISE EXCEPTION 'Every declared collision hazard requires resolution before round completion' USING ERRCODE='23514'; END IF; RETURN NEW; END $$;
CREATE TRIGGER senc_round_collision_resolved BEFORE UPDATE OF round_status ON senc_round FOR EACH ROW EXECUTE FUNCTION senc_require_collision_resolution();
CREATE FUNCTION senc_reject_collision_history_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Collision hazard history is immutable'; END $$;
CREATE TRIGGER senc_collision_hazard_immutable BEFORE UPDATE OR DELETE ON senc_collision_hazard FOR EACH ROW EXECUTE FUNCTION senc_reject_collision_history_mutation();
CREATE TRIGGER senc_collision_die_immutable BEFORE UPDATE OR DELETE ON senc_collision_damage_die FOR EACH ROW EXECUTE FUNCTION senc_reject_collision_history_mutation();
CREATE TRIGGER senc_avoid_collision_immutable BEFORE UPDATE OR DELETE ON senc_avoid_collision_receipt FOR EACH ROW EXECUTE FUNCTION senc_reject_collision_history_mutation();
CREATE TRIGGER senc_collision_allocation_immutable BEFORE UPDATE OR DELETE ON senc_collision_damage_allocation FOR EACH ROW EXECUTE FUNCTION senc_reject_collision_history_mutation();
