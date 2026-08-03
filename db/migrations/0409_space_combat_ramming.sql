INSERT INTO src_locator(source_work_id,source_artifact_id,locator_type,heading_path,display_citation)
SELECT a.source_work_id,a.source_artifact_id,'heading','Space Combat > Significant Actions > Ram',
 CASE w.work_code WHEN 'cepheus-engine.ogn' THEN 'Cepheus Engine SRD, Space Combat: Ram'
 ELSE 'Cepheus Engine v9.1, Space Combat: Ram' END
FROM src_artifact a JOIN src_work w USING(source_work_id)
WHERE (w.work_code='cepheus-engine.ogn' AND a.source_uri LIKE '%cepheus-engine-space-combat/')
 OR (w.work_code='cepheus-engine.github-v9.1' AND a.source_uri='src/book2/space-combat.md')
ON CONFLICT DO NOTHING;
WITH p AS (SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine')
INSERT INTO rule_rule(content_package_id,rule_code,name,rule_category,rule_status,description)
SELECT content_package_id,'combat.space.ram','Space Combat Ram','combat','approved',
 'Close-range opposed Piloting collision using shared speed-difference damage.' FROM p;
CREATE TABLE rule_space_combat_ram(
 rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),skill_rule_id bigint NOT NULL REFERENCES rule_skill(rule_id),
 required_range_code text NOT NULL CHECK(required_range_code='close') REFERENCES rule_space_range_band(range_band_code),
 rammer_must_be_faster boolean NOT NULL,damage_dice_per_speed_difference smallint NOT NULL CHECK(damage_dice_per_speed_difference=1),
 damage_die_sides smallint NOT NULL CHECK(damage_die_sides=6),opposed_tie_uses_characteristic boolean NOT NULL,
 full_tie_requires_reroll boolean NOT NULL,shared_damage_roll boolean NOT NULL,damage_applies_to_both_vessels boolean NOT NULL,
 armor_applies_independently boolean NOT NULL
);
INSERT INTO rule_space_combat_ram SELECT ram.rule_id,pilot.rule_id,'close',true,1,6,true,true,true,true,true
FROM rule_rule ram CROSS JOIN rule_rule pilot WHERE ram.rule_code='combat.space.ram' AND pilot.rule_code='skill.piloting';
INSERT INTO rule_interpretation(rule_id,interpretation_type,decision_register_entry,rationale)
SELECT rule_id,'agreed_interpretation','CE-SC-005',
 'A successful ram uses one immutable 1D6-per-speed-difference pool applied to both vessels; armor and damage apply independently, failure does no damage, and a full opposed tie requires reroll.'
FROM rule_rule WHERE rule_code='combat.space.ram';
INSERT INTO src_record_provenance(rule_id,content_package_id,source_locator_id,provenance_class,is_primary_citation)
SELECT r.rule_id,r.content_package_id,l.source_locator_id,CASE w.work_code WHEN 'cepheus-engine.ogn' THEN 'direct' ELSE 'corroborating' END,w.work_code='cepheus-engine.ogn'
FROM rule_rule r CROSS JOIN src_locator l JOIN src_work w USING(source_work_id)
WHERE r.rule_code='combat.space.ram' AND l.heading_path='Space Combat > Significant Actions > Ram'
 AND w.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1');

CREATE TABLE senc_ram_attempt_receipt(
 ram_attempt_receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 engagement_id bigint NOT NULL,campaign_id bigint NOT NULL,space_combat_round_id bigint NOT NULL,
 round_number integer NOT NULL CHECK(round_number>0),ramming_vessel_id bigint NOT NULL,target_vessel_id bigint NOT NULL,
 action_id bigint NOT NULL UNIQUE,ramming_task_command_id bigint NOT NULL UNIQUE REFERENCES cmd_actor_task_receipt(command_id),
 target_task_command_id bigint NOT NULL UNIQUE REFERENCES cmd_actor_task_receipt(command_id),
 ramming_effect smallint NOT NULL,target_effect smallint NOT NULL,ramming_characteristic_value smallint NOT NULL,
 target_characteristic_value smallint NOT NULL,resolution_status text NOT NULL CHECK(resolution_status IN('succeeded','failed','reroll-required')),
 range_band_snapshot text NOT NULL CHECK(range_band_snapshot='close') REFERENCES rule_space_range_band(range_band_code),
 ramming_speed_snapshot numeric NOT NULL,target_speed_snapshot numeric NOT NULL,
 speed_difference smallint NOT NULL CHECK(speed_difference>0),recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(space_combat_round_id,engagement_id,campaign_id) REFERENCES senc_round(space_combat_round_id,engagement_id,campaign_id),
 FOREIGN KEY(ramming_vessel_id,engagement_id,campaign_id) REFERENCES senc_vessel(senc_vessel_id,engagement_id,campaign_id),
 FOREIGN KEY(target_vessel_id,engagement_id,campaign_id) REFERENCES senc_vessel(senc_vessel_id,engagement_id,campaign_id),
 FOREIGN KEY(action_id,engagement_id,campaign_id) REFERENCES senc_action(space_combat_action_id,engagement_id,campaign_id),
 CHECK(ramming_vessel_id<>target_vessel_id),CHECK(ramming_speed_snapshot-target_speed_snapshot=speed_difference)
);
CREATE TABLE senc_ram_damage_die(
 ram_attempt_receipt_id bigint NOT NULL REFERENCES senc_ram_attempt_receipt(ram_attempt_receipt_id),
 die_order smallint NOT NULL CHECK(die_order>0),result smallint NOT NULL CHECK(result BETWEEN 1 AND 6),
 PRIMARY KEY(ram_attempt_receipt_id,die_order)
);
CREATE TABLE senc_ram_final_receipt(
 ram_attempt_receipt_id bigint PRIMARY KEY REFERENCES senc_ram_attempt_receipt(ram_attempt_receipt_id),
 rolled_damage smallint NOT NULL CHECK(rolled_damage>=0),
 rammer_ship_id bigint NOT NULL,target_ship_id bigint NOT NULL,
 rammer_armor_snapshot smallint NOT NULL CHECK(rammer_armor_snapshot>=0),target_armor_snapshot smallint NOT NULL CHECK(target_armor_snapshot>=0),
 rammer_net_damage smallint NOT NULL CHECK(rammer_net_damage>=0),target_net_damage smallint NOT NULL CHECK(target_net_damage>=0),
 rammer_hull_before smallint NOT NULL,rammer_hull_after smallint NOT NULL,rammer_structure_before smallint NOT NULL,rammer_structure_after smallint NOT NULL,
 target_hull_before smallint NOT NULL,target_hull_after smallint NOT NULL,target_structure_before smallint NOT NULL,target_structure_after smallint NOT NULL,
 rammer_version_before bigint NOT NULL,rammer_version_after bigint NOT NULL,target_version_before bigint NOT NULL,target_version_after bigint NOT NULL,
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 CHECK(rammer_net_damage=greatest(rolled_damage-rammer_armor_snapshot,0)),
 CHECK(target_net_damage=greatest(rolled_damage-target_armor_snapshot,0)),
 CHECK(rammer_hull_after=greatest(rammer_hull_before-rammer_net_damage,0)),
 CHECK(rammer_structure_after=greatest(rammer_structure_before-greatest(rammer_net_damage-rammer_hull_before,0),0)),
 CHECK(target_hull_after=greatest(target_hull_before-target_net_damage,0)),
 CHECK(target_structure_after=greatest(target_structure_before-greatest(target_net_damage-target_hull_before,0),0))
);
CREATE TABLE senc_ram_damage_allocation(
 ram_attempt_receipt_id bigint NOT NULL REFERENCES senc_ram_final_receipt(ram_attempt_receipt_id),
 affected_vessel text NOT NULL CHECK(affected_vessel IN('rammer','target')),damage_kind text NOT NULL CHECK(damage_kind IN('hull','structure')),
 ship_damage_id bigint NOT NULL UNIQUE REFERENCES ship_damage(ship_damage_id),damage_points smallint NOT NULL CHECK(damage_points>0),
 PRIMARY KEY(ram_attempt_receipt_id,affected_vessel,damage_kind)
);

CREATE FUNCTION senc_validate_ram_attempt() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE range_row text; action_row record; a record; b record; opposing_actor bigint; pilot bigint; expected text;
BEGIN
 SELECT range_band_code INTO range_row FROM senc_vessel_range WHERE engagement_id=NEW.engagement_id
  AND first_vessel_id=least(NEW.ramming_vessel_id,NEW.target_vessel_id) AND second_vessel_id=greatest(NEW.ramming_vessel_id,NEW.target_vessel_id);
 SELECT action.action_code,action.target_vessel_id,action.space_combat_round_id,turn.senc_vessel_id,assignment.actor_id,
  assignment.duty_status,definition.position_code INTO action_row FROM senc_action action JOIN senc_crew_turn turn USING(crew_turn_id)
 JOIN ship_crew_assignment assignment USING(crew_assignment_id) JOIN ship_crew_position ps USING(ship_crew_position_id)
 JOIN ship_crew_position_definition definition USING(crew_position_rule_id) WHERE action.space_combat_action_id=NEW.action_id;
 SELECT actor_id,skill_rule_id,effect INTO a FROM cmd_actor_task_receipt WHERE command_id=NEW.ramming_task_command_id;
 SELECT assignment.actor_id INTO opposing_actor FROM senc_vessel vessel JOIN ship_crew_assignment assignment ON assignment.ship_id=vessel.ship_id AND assignment.duty_status='active'
 JOIN ship_crew_position ps USING(ship_crew_position_id) JOIN ship_crew_position_definition definition USING(crew_position_rule_id)
 WHERE vessel.senc_vessel_id=NEW.target_vessel_id AND definition.position_code='pilot';
 SELECT actor_id,skill_rule_id,effect INTO b FROM cmd_actor_task_receipt WHERE command_id=NEW.target_task_command_id;
 SELECT rule_id INTO STRICT pilot FROM rule_rule WHERE rule_code='skill.piloting';
 expected:=CASE WHEN NEW.ramming_effect>NEW.target_effect THEN 'succeeded' WHEN NEW.ramming_effect<NEW.target_effect THEN 'failed'
  WHEN NEW.ramming_characteristic_value>NEW.target_characteristic_value THEN 'succeeded'
  WHEN NEW.ramming_characteristic_value<NEW.target_characteristic_value THEN 'failed' ELSE 'reroll-required' END;
 IF range_row<>'close' OR action_row.action_code<>'ram' OR action_row.target_vessel_id<>NEW.target_vessel_id
  OR action_row.space_combat_round_id<>NEW.space_combat_round_id OR action_row.senc_vessel_id<>NEW.ramming_vessel_id
  OR action_row.position_code<>'pilot' OR action_row.duty_status<>'active' OR a.actor_id<>action_row.actor_id
  OR b.actor_id<>opposing_actor OR a.skill_rule_id<>pilot OR b.skill_rule_id<>pilot OR a.effect<>NEW.ramming_effect
  OR b.effect<>NEW.target_effect OR NEW.resolution_status<>expected THEN
  RAISE EXCEPTION 'Ram attempt is inconsistent with Close-range opposed Piloting' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER senc_ram_attempt_valid BEFORE INSERT ON senc_ram_attempt_receipt FOR EACH ROW EXECUTE FUNCTION senc_validate_ram_attempt();

CREATE FUNCTION senc_finalize_ram() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE attempt senc_ram_attempt_receipt%ROWTYPE; dice_count integer; dice_total integer; rammer record; target record;
 rammer_armor integer; target_armor integer; hull_damage integer; structure_damage integer; damage_id bigint;
BEGIN
 SELECT * INTO STRICT attempt FROM senc_ram_attempt_receipt WHERE ram_attempt_receipt_id=NEW.ram_attempt_receipt_id FOR UPDATE;
 SELECT count(*),coalesce(sum(result),0) INTO dice_count,dice_total FROM senc_ram_damage_die WHERE ram_attempt_receipt_id=NEW.ram_attempt_receipt_id;
 SELECT vessel.ship_id,ship.ship_class_rule_id,ship.hull_current,ship.structure_current,ship.concurrency_version INTO rammer
 FROM senc_vessel vessel JOIN ship_ship ship USING(ship_id) WHERE vessel.senc_vessel_id=attempt.ramming_vessel_id FOR UPDATE OF ship;
 SELECT vessel.ship_id,ship.ship_class_rule_id,ship.hull_current,ship.structure_current,ship.concurrency_version INTO target
 FROM senc_vessel vessel JOIN ship_ship ship USING(ship_id) WHERE vessel.senc_vessel_id=attempt.target_vessel_id FOR UPDATE OF ship;
 SELECT coalesce((SELECT armor_value FROM ship_class_published_armor WHERE ship_class_rule_id=rammer.ship_class_rule_id),
  (SELECT h.armor_increments*a.protection_per_increment FROM ship_class_design_hull h JOIN rule_ship_armor_design a USING(armor_code) WHERE h.ship_class_rule_id=rammer.ship_class_rule_id),0) INTO rammer_armor;
 SELECT coalesce((SELECT armor_value FROM ship_class_published_armor WHERE ship_class_rule_id=target.ship_class_rule_id),
  (SELECT h.armor_increments*a.protection_per_increment FROM ship_class_design_hull h JOIN rule_ship_armor_design a USING(armor_code) WHERE h.ship_class_rule_id=target.ship_class_rule_id),0) INTO target_armor;
 IF (attempt.resolution_status='succeeded' AND (dice_count<>attempt.speed_difference OR dice_total<>NEW.rolled_damage))
  OR (attempt.resolution_status<>'succeeded' AND (dice_count<>0 OR NEW.rolled_damage<>0))
  OR NEW.rammer_ship_id<>rammer.ship_id OR NEW.target_ship_id<>target.ship_id
  OR NEW.rammer_armor_snapshot<>rammer_armor OR NEW.target_armor_snapshot<>target_armor
  OR NEW.rammer_hull_before<>rammer.hull_current OR NEW.rammer_structure_before<>rammer.structure_current
  OR NEW.target_hull_before<>target.hull_current OR NEW.target_structure_before<>target.structure_current
  OR NEW.rammer_version_before<>rammer.concurrency_version OR NEW.target_version_before<>target.concurrency_version
  OR NEW.rammer_version_after<>rammer.concurrency_version+1 OR NEW.target_version_after<>target.concurrency_version+1 THEN
  RAISE EXCEPTION 'Ram final receipt fails collision recomputation' USING ERRCODE='23514';
 END IF;
 UPDATE ship_ship SET hull_current=NEW.rammer_hull_after,structure_current=NEW.rammer_structure_after,
  concurrency_version=NEW.rammer_version_after WHERE ship_id=rammer.ship_id;
 UPDATE ship_ship SET hull_current=NEW.target_hull_after,structure_current=NEW.target_structure_after,
  concurrency_version=NEW.target_version_after WHERE ship_id=target.ship_id;
 hull_damage:=rammer.hull_current-NEW.rammer_hull_after; structure_damage:=rammer.structure_current-NEW.rammer_structure_after;
 IF hull_damage>0 THEN INSERT INTO ship_damage(ship_id,campaign_id,target_kind,damage_points,description)
  VALUES(rammer.ship_id,attempt.campaign_id,'hull',hull_damage,'Ramming collision') RETURNING ship_damage_id INTO damage_id;
  INSERT INTO senc_ram_damage_allocation VALUES(attempt.ram_attempt_receipt_id,'rammer','hull',damage_id,hull_damage); END IF;
 IF structure_damage>0 THEN INSERT INTO ship_damage(ship_id,campaign_id,target_kind,damage_points,description)
  VALUES(rammer.ship_id,attempt.campaign_id,'structure',structure_damage,'Ramming collision overflow') RETURNING ship_damage_id INTO damage_id;
  INSERT INTO senc_ram_damage_allocation VALUES(attempt.ram_attempt_receipt_id,'rammer','structure',damage_id,structure_damage); END IF;
 hull_damage:=target.hull_current-NEW.target_hull_after; structure_damage:=target.structure_current-NEW.target_structure_after;
 IF hull_damage>0 THEN INSERT INTO ship_damage(ship_id,campaign_id,target_kind,damage_points,description)
  VALUES(target.ship_id,attempt.campaign_id,'hull',hull_damage,'Ramming collision') RETURNING ship_damage_id INTO damage_id;
  INSERT INTO senc_ram_damage_allocation VALUES(attempt.ram_attempt_receipt_id,'target','hull',damage_id,hull_damage); END IF;
 IF structure_damage>0 THEN INSERT INTO ship_damage(ship_id,campaign_id,target_kind,damage_points,description)
  VALUES(target.ship_id,attempt.campaign_id,'structure',structure_damage,'Ramming collision overflow') RETURNING ship_damage_id INTO damage_id;
  INSERT INTO senc_ram_damage_allocation VALUES(attempt.ram_attempt_receipt_id,'target','structure',damage_id,structure_damage); END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER senc_ram_final_valid AFTER INSERT ON senc_ram_final_receipt FOR EACH ROW EXECUTE FUNCTION senc_finalize_ram();
CREATE FUNCTION senc_reject_ram_history_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Ram receipts and dice are immutable'; END $$;
CREATE TRIGGER senc_ram_attempt_immutable BEFORE UPDATE OR DELETE ON senc_ram_attempt_receipt FOR EACH ROW EXECUTE FUNCTION senc_reject_ram_history_mutation();
CREATE TRIGGER senc_ram_die_immutable BEFORE UPDATE OR DELETE ON senc_ram_damage_die FOR EACH ROW EXECUTE FUNCTION senc_reject_ram_history_mutation();
CREATE TRIGGER senc_ram_final_immutable BEFORE UPDATE OR DELETE ON senc_ram_final_receipt FOR EACH ROW EXECUTE FUNCTION senc_reject_ram_history_mutation();
CREATE TRIGGER senc_ram_allocation_immutable BEFORE UPDATE OR DELETE ON senc_ram_damage_allocation FOR EACH ROW EXECUTE FUNCTION senc_reject_ram_history_mutation();
