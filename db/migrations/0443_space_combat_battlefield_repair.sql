INSERT INTO src_locator(source_work_id,source_artifact_id,locator_type,heading_path,display_citation)
SELECT artifact.source_work_id,artifact.source_artifact_id,'heading',
 'Space Combat > Significant Actions > Repair Damaged System',
 CASE work.work_code WHEN 'cepheus-engine.ogn' THEN 'Cepheus Engine SRD, Space Combat: Repair Damaged System'
 ELSE 'Cepheus Engine v9.1, Space Combat: Repair Damaged System' END
FROM src_artifact artifact JOIN src_work work USING(source_work_id)
WHERE (work.work_code='cepheus-engine.ogn' AND artifact.source_uri LIKE '%cepheus-engine-space-combat/')
 OR (work.work_code='cepheus-engine.github-v9.1' AND artifact.source_uri='src/book2/space-combat.md')
ON CONFLICT DO NOTHING;

WITH package AS (SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine')
INSERT INTO rule_rule(content_package_id,rule_code,name,rule_category,rule_status,description)
SELECT content_package_id,'combat.space.battlefield-repair','Space Combat Battlefield Repair','combat','approved',
 'Education-based Mechanics Damage Control check temporarily restores system hits according to successful Effect.' FROM package;
CREATE TABLE rule_space_combat_repair_effect_band(
 rule_id bigint NOT NULL REFERENCES rule_rule(rule_id),effect_min smallint NOT NULL,effect_max smallint,
 hits_repaired smallint NOT NULL CHECK(hits_repaired BETWEEN 1 AND 3),PRIMARY KEY(rule_id,effect_min),
 CHECK(effect_min>=0 AND (effect_max IS NULL OR effect_max>=effect_min))
);
INSERT INTO rule_space_combat_repair_effect_band
SELECT rule_id,band.effect_min,band.effect_max,band.hits FROM rule_rule
CROSS JOIN (VALUES(0::smallint,0::smallint,1::smallint),(1,5,2),(6,NULL,3)) band(effect_min,effect_max,hits)
WHERE rule_code='combat.space.battlefield-repair';
INSERT INTO src_record_provenance(rule_id,content_package_id,source_locator_id,provenance_class,is_primary_citation)
SELECT rule.rule_id,rule.content_package_id,locator.source_locator_id,
 CASE work.work_code WHEN 'cepheus-engine.ogn' THEN 'direct' ELSE 'corroborating' END,work.work_code='cepheus-engine.ogn'
FROM rule_rule rule CROSS JOIN src_locator locator JOIN src_work work USING(source_work_id)
WHERE rule.rule_code='combat.space.battlefield-repair'
 AND locator.heading_path='Space Combat > Significant Actions > Repair Damaged System'
 AND work.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1');

CREATE TABLE senc_system_battlefield_repair_receipt(
 battlefield_repair_receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 action_id bigint NOT NULL UNIQUE,space_combat_round_id bigint NOT NULL,engagement_id bigint NOT NULL,campaign_id bigint NOT NULL,
 senc_vessel_id bigint NOT NULL,ship_id bigint NOT NULL,repairer_assignment_id bigint NOT NULL,repairer_actor_id bigint NOT NULL,
 system_code text NOT NULL,system_instance smallint NOT NULL CHECK(system_instance>0),task_command_id bigint NOT NULL UNIQUE REFERENCES cmd_actor_task_receipt(command_id),
 task_succeeded boolean NOT NULL,task_effect smallint NOT NULL,hits_available smallint NOT NULL CHECK(hits_available BETWEEN 1 AND 3),
 hits_repaired smallint NOT NULL CHECK(hits_repaired BETWEEN 1 AND 3),system_hits_before smallint NOT NULL CHECK(system_hits_before BETWEEN 1 AND 3),
 system_hits_after smallint NOT NULL CHECK(system_hits_after>=0 AND system_hits_after<system_hits_before),
 system_version_before bigint NOT NULL,system_version_after bigint NOT NULL CHECK(system_version_after=system_version_before+1),
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(action_id,engagement_id,campaign_id) REFERENCES senc_action(space_combat_action_id,engagement_id,campaign_id),
 FOREIGN KEY(space_combat_round_id,engagement_id,campaign_id) REFERENCES senc_round(space_combat_round_id,engagement_id,campaign_id),
 FOREIGN KEY(senc_vessel_id,engagement_id,campaign_id) REFERENCES senc_vessel(senc_vessel_id,engagement_id,campaign_id),
 FOREIGN KEY(repairer_assignment_id,ship_id,campaign_id) REFERENCES ship_crew_assignment(crew_assignment_id,ship_id,campaign_id),
 FOREIGN KEY(repairer_actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id),
 FOREIGN KEY(ship_id,system_code,system_instance) REFERENCES senc_ship_system_damage_state(ship_id,system_code,system_instance),
 CHECK(task_succeeded AND task_effect>=0),CHECK(system_hits_after=system_hits_before-hits_repaired),CHECK(hits_repaired<=hits_available)
);
CREATE TABLE senc_system_temporary_repair_state(
 battlefield_repair_receipt_id bigint PRIMARY KEY REFERENCES senc_system_battlefield_repair_receipt(battlefield_repair_receipt_id),
 engagement_id bigint NOT NULL,ship_id bigint NOT NULL,campaign_id bigint NOT NULL,system_code text NOT NULL,system_instance smallint NOT NULL,
 restored_hits smallint NOT NULL CHECK(restored_hits BETWEEN 1 AND 3),restoration_status text NOT NULL DEFAULT 'active' CHECK(restoration_status IN('active','expired','superseded')),
 applied_at timestamptz NOT NULL DEFAULT clock_timestamp(),ended_at timestamptz,
 FOREIGN KEY(ship_id,system_code,system_instance) REFERENCES senc_ship_system_damage_state(ship_id,system_code,system_instance),
 CHECK((restoration_status='active')=(ended_at IS NULL))
);

CREATE FUNCTION senc_recompute_damaged_system_runtime(p_ship_id bigint,p_system_code text) RETURNS void LANGUAGE plpgsql AS $$
DECLARE hits smallint; class_thrust smallint; effective_thrust smallint;
BEGIN
 SELECT hit_count INTO hits FROM senc_ship_system_damage_state WHERE ship_id=p_ship_id AND system_code=p_system_code AND system_instance=1;
 IF p_system_code='m-drive' THEN
  SELECT class.maneuver_rating INTO class_thrust FROM ship_ship ship JOIN ship_class class USING(ship_class_rule_id) WHERE ship.ship_id=p_ship_id;
  effective_thrust:=CASE hits WHEN 0 THEN class_thrust WHEN 1 THEN greatest(0,class_thrust-1)
   WHEN 2 THEN floor(greatest(0,class_thrust-1)::numeric/2)::smallint ELSE 0 END;
  UPDATE senc_vessel vessel SET thrust_current=effective_thrust FROM senc_engagement engagement
   WHERE vessel.engagement_id=engagement.engagement_id AND vessel.ship_id=p_ship_id AND engagement.engagement_status='active';
 ELSIF p_system_code='power-plant' AND hits<3 THEN
  UPDATE senc_vessel vessel SET vessel_status='engaged' FROM senc_engagement engagement
   WHERE vessel.engagement_id=engagement.engagement_id AND vessel.ship_id=p_ship_id
    AND engagement.engagement_status='active' AND vessel.vessel_status='disabled';
 END IF;
END $$;

CREATE FUNCTION senc_apply_battlefield_system_repair() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE action_row record; task cmd_actor_task_receipt%ROWTYPE; state senc_ship_system_damage_state%ROWTYPE;
 mechanics bigint; education bigint; expected_hits smallint; actual_round bigint; new_status text; new_attack_dm smallint; new_sensor_dm smallint;
BEGIN
 SELECT action.action_code,action.space_combat_round_id,turn.senc_vessel_id,turn.crew_assignment_id,
  assignment.ship_id,assignment.actor_id,assignment.duty_status INTO STRICT action_row
 FROM senc_action action JOIN senc_crew_turn turn USING(crew_turn_id) JOIN ship_crew_assignment assignment USING(crew_assignment_id)
 WHERE action.space_combat_action_id=NEW.action_id;
 SELECT * INTO STRICT task FROM cmd_actor_task_receipt WHERE command_id=NEW.task_command_id;
 SELECT rule_id INTO STRICT mechanics FROM rule_rule WHERE rule_code='skill.mechanics';
 SELECT rule_id INTO STRICT education FROM rule_rule WHERE rule_code='characteristic.education';
 SELECT round_number INTO actual_round FROM senc_round WHERE space_combat_round_id=NEW.space_combat_round_id;
 SELECT * INTO STRICT state FROM senc_ship_system_damage_state WHERE ship_id=NEW.ship_id AND system_code=NEW.system_code
  AND system_instance=NEW.system_instance FOR UPDATE;
 SELECT hits_repaired INTO expected_hits FROM rule_space_combat_repair_effect_band band JOIN rule_rule rule ON rule.rule_id=band.rule_id
 WHERE rule.rule_code='combat.space.battlefield-repair' AND NEW.task_effect>=band.effect_min
  AND (band.effect_max IS NULL OR NEW.task_effect<=band.effect_max);
 expected_hits:=least(expected_hits,state.hit_count);
 IF action_row.action_code<>'repair-system' OR action_row.space_combat_round_id<>NEW.space_combat_round_id
  OR action_row.senc_vessel_id<>NEW.senc_vessel_id OR action_row.crew_assignment_id<>NEW.repairer_assignment_id
  OR action_row.ship_id<>NEW.ship_id OR action_row.actor_id<>NEW.repairer_actor_id OR action_row.duty_status<>'active'
  OR NOT EXISTS(SELECT 1 FROM senc_crew_role_assignment role WHERE role.engagement_id=NEW.engagement_id
   AND role.senc_vessel_id=NEW.senc_vessel_id AND role.crew_assignment_id=NEW.repairer_assignment_id
   AND role.crew_role='damage_control' AND role.ended_at IS NULL)
  OR task.actor_id<>NEW.repairer_actor_id OR task.skill_rule_id<>mechanics OR task.characteristic_rule_id<>education
  OR NOT task.succeeded OR task.effect<>NEW.task_effect OR NOT NEW.task_succeeded OR NEW.task_effect<0 OR actual_round IS NULL
  OR NEW.system_hits_before<>state.hit_count OR NEW.system_version_before<>state.concurrency_version
  OR NEW.hits_available<>state.hit_count OR NEW.hits_repaired<>expected_hits OR NEW.system_hits_after<>state.hit_count-expected_hits THEN
  RAISE EXCEPTION 'Battlefield repair must match an active Damage Control Mechanics check and current damaged system' USING ERRCODE='23514'; END IF;
 new_status:=CASE state.hit_count-expected_hits WHEN 0 THEN 'operational' WHEN 1 THEN 'damaged' WHEN 2 THEN 'disabled' ELSE 'destroyed' END;
 new_attack_dm:=CASE WHEN NEW.system_code IN('turret','bay') AND state.hit_count-expected_hits=1 THEN -2
  WHEN NEW.system_code='bridge' AND state.hit_count-expected_hits>=2 THEN -2 ELSE 0 END;
 new_sensor_dm:=CASE WHEN NEW.system_code='sensors' AND state.hit_count-expected_hits>=1 THEN -2 ELSE 0 END;
 UPDATE senc_ship_system_damage_state SET hit_count=state.hit_count-expected_hits,system_status=new_status,
  attack_dm=new_attack_dm,sensor_dm=new_sensor_dm,concurrency_version=state.concurrency_version+1,updated_at=clock_timestamp()
 WHERE ship_id=NEW.ship_id AND system_code=NEW.system_code AND system_instance=NEW.system_instance;
 NEW.system_version_after:=state.concurrency_version+1;
 PERFORM senc_recompute_damaged_system_runtime(NEW.ship_id,NEW.system_code);
 RETURN NEW;
END $$;
CREATE TRIGGER senc_battlefield_system_repair_valid BEFORE INSERT ON senc_system_battlefield_repair_receipt
FOR EACH ROW EXECUTE FUNCTION senc_apply_battlefield_system_repair();
CREATE FUNCTION senc_record_temporary_system_repair() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN INSERT INTO senc_system_temporary_repair_state(battlefield_repair_receipt_id,engagement_id,ship_id,campaign_id,system_code,system_instance,restored_hits)
 VALUES(NEW.battlefield_repair_receipt_id,NEW.engagement_id,NEW.ship_id,NEW.campaign_id,NEW.system_code,NEW.system_instance,NEW.hits_repaired); RETURN NEW; END $$;
CREATE TRIGGER senc_battlefield_system_repair_state AFTER INSERT ON senc_system_battlefield_repair_receipt
FOR EACH ROW EXECUTE FUNCTION senc_record_temporary_system_repair();
CREATE FUNCTION senc_reject_battlefield_repair_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Battlefield repair receipts are immutable'; END $$;
CREATE TRIGGER senc_battlefield_system_repair_immutable BEFORE UPDATE OR DELETE ON senc_system_battlefield_repair_receipt
FOR EACH ROW EXECUTE FUNCTION senc_reject_battlefield_repair_mutation();
