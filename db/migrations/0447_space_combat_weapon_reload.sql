INSERT INTO src_locator(source_work_id,source_artifact_id,locator_type,heading_path,display_citation)
SELECT a.source_work_id,a.source_artifact_id,'heading','Space Combat > Significant Actions > Reload Weapons System',
 CASE w.work_code WHEN 'cepheus-engine.ogn' THEN 'Cepheus Engine SRD, Space Combat: Reload Weapons System'
 ELSE 'Cepheus Engine v9.1, Space Combat: Reload Weapons System' END FROM src_artifact a JOIN src_work w USING(source_work_id)
WHERE (w.work_code='cepheus-engine.ogn' AND a.source_uri LIKE '%cepheus-engine-space-combat/')
 OR (w.work_code='cepheus-engine.github-v9.1' AND a.source_uri='src/book2/space-combat.md') ON CONFLICT DO NOTHING;
WITH p AS (SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine')
INSERT INTO rule_rule(content_package_id,rule_code,name,rule_category,rule_status,description)
SELECT content_package_id,'combat.space.reload-weapon-system','Reload Weapons System','combat','approved',
 'A significant action reloads one spent missile rack, sandcaster, or other individual weapon system.' FROM p;
CREATE TABLE rule_space_combat_weapon_reload(rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
 action_code text NOT NULL REFERENCES rule_space_combat_action(action_code),systems_per_action smallint NOT NULL CHECK(systems_per_action=1),
 requires_spent_system boolean NOT NULL,eligible_ammunition_per_attack_min smallint NOT NULL CHECK(eligible_ammunition_per_attack_min=1));
INSERT INTO rule_space_combat_weapon_reload SELECT rule_id,'reload-weapons',1,true,1 FROM rule_rule WHERE rule_code='combat.space.reload-weapon-system';
INSERT INTO src_record_provenance(rule_id,content_package_id,source_locator_id,provenance_class,is_primary_citation)
SELECT r.rule_id,r.content_package_id,l.source_locator_id,CASE w.work_code WHEN 'cepheus-engine.ogn' THEN 'direct' ELSE 'corroborating' END,w.work_code='cepheus-engine.ogn'
FROM rule_rule r CROSS JOIN src_locator l JOIN src_work w USING(source_work_id) WHERE r.rule_code='combat.space.reload-weapon-system'
 AND l.heading_path='Space Combat > Significant Actions > Reload Weapons System' AND w.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1');

CREATE TABLE senc_weapon_readiness_state(
 engagement_id bigint NOT NULL,campaign_id bigint NOT NULL,senc_vessel_id bigint NOT NULL,ship_id bigint NOT NULL,
 class_weapon_mount_id bigint NOT NULL,ship_class_rule_id bigint NOT NULL,mount_instance smallint NOT NULL CHECK(mount_instance>0),
 weapon_slot smallint NOT NULL CHECK(weapon_slot>0),weapon_rule_id bigint NOT NULL REFERENCES ship_weapon_definition(weapon_rule_id),
 resource_type_code text NOT NULL REFERENCES ship_resource_type(resource_type_code),ammunition_per_attack smallint NOT NULL CHECK(ammunition_per_attack>0),
 readiness_status text NOT NULL DEFAULT 'ready' CHECK(readiness_status IN('ready','spent')),concurrency_version bigint NOT NULL DEFAULT 1 CHECK(concurrency_version>0),
 updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),PRIMARY KEY(engagement_id,senc_vessel_id,class_weapon_mount_id,mount_instance,weapon_slot),
 FOREIGN KEY(senc_vessel_id,engagement_id,campaign_id) REFERENCES senc_vessel(senc_vessel_id,engagement_id,campaign_id),
 FOREIGN KEY(class_weapon_mount_id,ship_class_rule_id) REFERENCES ship_class_weapon_mount(class_weapon_mount_id,ship_class_rule_id),
 FOREIGN KEY(class_weapon_mount_id,weapon_slot) REFERENCES ship_class_mount_weapon(class_weapon_mount_id,weapon_slot)
);
CREATE FUNCTION senc_initialize_weapon_readiness(p_senc_vessel_id bigint) RETURNS void LANGUAGE plpgsql AS $$
BEGIN
 INSERT INTO senc_weapon_readiness_state(engagement_id,campaign_id,senc_vessel_id,ship_id,class_weapon_mount_id,ship_class_rule_id,mount_instance,weapon_slot,weapon_rule_id,resource_type_code,ammunition_per_attack)
 SELECT v.engagement_id,v.campaign_id,v.senc_vessel_id,v.ship_id,m.class_weapon_mount_id,m.ship_class_rule_id,instance.number,w.weapon_slot,w.weapon_rule_id,
  CASE d.weapon_kind WHEN 'sandcaster' THEN 'sand' ELSE 'missiles' END,d.ammunition_per_attack
 FROM senc_vessel v JOIN ship_ship s USING(ship_id) JOIN ship_class_weapon_mount m ON m.ship_class_rule_id=s.ship_class_rule_id
 JOIN LATERAL generate_series(1,m.mount_count) instance(number) ON true JOIN ship_class_mount_weapon w USING(class_weapon_mount_id,ship_class_rule_id)
 JOIN ship_weapon_definition d USING(weapon_rule_id) WHERE v.senc_vessel_id=p_senc_vessel_id AND d.ammunition_per_attack>0 ON CONFLICT DO NOTHING;
END $$;
CREATE FUNCTION senc_initialize_weapon_readiness_trigger() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN PERFORM senc_initialize_weapon_readiness(NEW.senc_vessel_id); RETURN NEW; END $$;
CREATE TRIGGER senc_vessel_weapon_readiness AFTER INSERT ON senc_vessel FOR EACH ROW EXECUTE FUNCTION senc_initialize_weapon_readiness_trigger();
DO $$ DECLARE vessel bigint; BEGIN FOR vessel IN SELECT senc_vessel_id FROM senc_vessel LOOP PERFORM senc_initialize_weapon_readiness(vessel); END LOOP; END $$;

CREATE TABLE senc_weapon_ammunition_consumption_receipt(
 weapon_ammunition_consumption_receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 mount_weapon_attack_check_id bigint UNIQUE REFERENCES senc_mount_weapon_attack_check(mount_weapon_attack_check_id),
 fire_sand_attempt_receipt_id bigint UNIQUE REFERENCES senc_fire_sand_attempt_receipt(fire_sand_attempt_receipt_id),
 engagement_id bigint NOT NULL,campaign_id bigint NOT NULL,senc_vessel_id bigint NOT NULL,ship_id bigint NOT NULL,
 class_weapon_mount_id bigint NOT NULL,mount_instance smallint NOT NULL,weapon_slot smallint NOT NULL,weapon_rule_id bigint NOT NULL,
 resource_type_code text NOT NULL,quantity_consumed smallint NOT NULL CHECK(quantity_consumed>0),resource_movement_id bigint UNIQUE REFERENCES ship_resource_movement(resource_movement_id),
 readiness_version_before bigint NOT NULL,readiness_version_after bigint NOT NULL CHECK(readiness_version_after=readiness_version_before+1),recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 CHECK(num_nonnulls(mount_weapon_attack_check_id,fire_sand_attempt_receipt_id)=1));

CREATE FUNCTION senc_consume_mount_attack_ammunition() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE declaration senc_mount_attack_declaration%ROWTYPE; state senc_weapon_readiness_state%ROWTYPE; balance numeric; movement bigint;
BEGIN
 SELECT * INTO STRICT declaration FROM senc_mount_attack_declaration WHERE mount_attack_declaration_id=NEW.mount_attack_declaration_id;
 SELECT * INTO STRICT state FROM senc_weapon_readiness_state WHERE engagement_id=declaration.engagement_id AND senc_vessel_id=declaration.attacker_vessel_id
  AND class_weapon_mount_id=declaration.class_weapon_mount_id AND mount_instance=declaration.mount_instance AND weapon_slot=NEW.weapon_slot FOR UPDATE;
 SELECT current_quantity INTO STRICT balance FROM ship_resource WHERE ship_id=state.ship_id AND resource_type_code=state.resource_type_code FOR UPDATE;
 IF state.readiness_status<>'ready' OR balance<state.ammunition_per_attack THEN RAISE EXCEPTION 'Ammunition weapon system is spent or lacks reserve ammunition' USING ERRCODE='23514'; END IF;
 UPDATE ship_resource SET current_quantity=balance-state.ammunition_per_attack,updated_at=clock_timestamp() WHERE ship_id=state.ship_id AND resource_type_code=state.resource_type_code;
 INSERT INTO ship_resource_movement(ship_id,campaign_id,resource_type_code,quantity_delta,balance_after,movement_kind)
 VALUES(state.ship_id,state.campaign_id,state.resource_type_code,-state.ammunition_per_attack,balance-state.ammunition_per_attack,'consume') RETURNING resource_movement_id INTO movement;
 UPDATE senc_weapon_readiness_state SET readiness_status='spent',concurrency_version=state.concurrency_version+1,updated_at=clock_timestamp()
  WHERE engagement_id=state.engagement_id AND senc_vessel_id=state.senc_vessel_id AND class_weapon_mount_id=state.class_weapon_mount_id AND mount_instance=state.mount_instance AND weapon_slot=state.weapon_slot;
 INSERT INTO senc_weapon_ammunition_consumption_receipt(mount_weapon_attack_check_id,engagement_id,campaign_id,senc_vessel_id,ship_id,class_weapon_mount_id,mount_instance,weapon_slot,weapon_rule_id,resource_type_code,quantity_consumed,resource_movement_id,readiness_version_before,readiness_version_after)
 VALUES(NEW.mount_weapon_attack_check_id,state.engagement_id,state.campaign_id,state.senc_vessel_id,state.ship_id,state.class_weapon_mount_id,state.mount_instance,state.weapon_slot,state.weapon_rule_id,state.resource_type_code,state.ammunition_per_attack,movement,state.concurrency_version,state.concurrency_version+1);
 RETURN NEW;
EXCEPTION WHEN no_data_found THEN
 IF EXISTS(SELECT 1 FROM ship_weapon_definition WHERE weapon_rule_id=NEW.weapon_rule_id AND ammunition_per_attack>0) THEN RAISE EXCEPTION 'Ammunition weapon lacks initialized readiness state' USING ERRCODE='23514'; END IF; RETURN NEW;
END $$;
CREATE TRIGGER senc_mount_attack_consume_ammunition AFTER INSERT ON senc_mount_weapon_attack_check FOR EACH ROW EXECUTE FUNCTION senc_consume_mount_attack_ammunition();

CREATE TABLE senc_weapon_reload_receipt(
 weapon_reload_receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,action_id bigint NOT NULL UNIQUE,space_combat_round_id bigint NOT NULL,
 engagement_id bigint NOT NULL,campaign_id bigint NOT NULL,senc_vessel_id bigint NOT NULL,ship_id bigint NOT NULL,reloader_assignment_id bigint NOT NULL,
 class_weapon_mount_id bigint NOT NULL,mount_instance smallint NOT NULL,weapon_slot smallint NOT NULL,weapon_rule_id bigint NOT NULL,
 readiness_version_before bigint NOT NULL,readiness_version_after bigint NOT NULL CHECK(readiness_version_after=readiness_version_before+1),recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(action_id,engagement_id,campaign_id) REFERENCES senc_action(space_combat_action_id,engagement_id,campaign_id),
 FOREIGN KEY(space_combat_round_id,engagement_id,campaign_id) REFERENCES senc_round(space_combat_round_id,engagement_id,campaign_id),
 FOREIGN KEY(senc_vessel_id,engagement_id,campaign_id) REFERENCES senc_vessel(senc_vessel_id,engagement_id,campaign_id));
CREATE FUNCTION senc_apply_weapon_reload() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE action_row record; state senc_weapon_readiness_state%ROWTYPE;
BEGIN
 SELECT a.action_code,a.space_combat_round_id,t.senc_vessel_id,t.crew_assignment_id,ca.ship_id,ca.duty_status INTO STRICT action_row
 FROM senc_action a JOIN senc_crew_turn t USING(crew_turn_id) JOIN ship_crew_assignment ca USING(crew_assignment_id) WHERE a.space_combat_action_id=NEW.action_id;
 SELECT * INTO STRICT state FROM senc_weapon_readiness_state WHERE engagement_id=NEW.engagement_id AND senc_vessel_id=NEW.senc_vessel_id
  AND class_weapon_mount_id=NEW.class_weapon_mount_id AND mount_instance=NEW.mount_instance AND weapon_slot=NEW.weapon_slot FOR UPDATE;
 IF action_row.action_code<>'reload-weapons' OR action_row.space_combat_round_id<>NEW.space_combat_round_id OR action_row.senc_vessel_id<>NEW.senc_vessel_id
  OR action_row.crew_assignment_id<>NEW.reloader_assignment_id OR action_row.ship_id<>NEW.ship_id OR action_row.duty_status<>'active'
  OR state.ship_id<>NEW.ship_id OR state.weapon_rule_id<>NEW.weapon_rule_id OR state.readiness_status<>'spent'
  OR state.concurrency_version<>NEW.readiness_version_before OR NEW.readiness_version_after<>state.concurrency_version+1 THEN
  RAISE EXCEPTION 'Reload Weapons System must target one matching spent individual weapon system' USING ERRCODE='23514'; END IF;
 UPDATE senc_weapon_readiness_state SET readiness_status='ready',concurrency_version=state.concurrency_version+1,updated_at=clock_timestamp()
 WHERE engagement_id=state.engagement_id AND senc_vessel_id=state.senc_vessel_id AND class_weapon_mount_id=state.class_weapon_mount_id AND mount_instance=state.mount_instance AND weapon_slot=state.weapon_slot;
 RETURN NEW;
END $$;
CREATE TRIGGER senc_weapon_reload_valid BEFORE INSERT ON senc_weapon_reload_receipt FOR EACH ROW EXECUTE FUNCTION senc_apply_weapon_reload();
CREATE FUNCTION senc_reject_weapon_ammunition_receipt_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Weapon ammunition receipts are immutable'; END $$;
CREATE TRIGGER senc_weapon_consumption_immutable BEFORE UPDATE OR DELETE ON senc_weapon_ammunition_consumption_receipt FOR EACH ROW EXECUTE FUNCTION senc_reject_weapon_ammunition_receipt_mutation();
CREATE TRIGGER senc_weapon_reload_immutable BEFORE UPDATE OR DELETE ON senc_weapon_reload_receipt FOR EACH ROW EXECUTE FUNCTION senc_reject_weapon_ammunition_receipt_mutation();
