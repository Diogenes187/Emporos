INSERT INTO src_locator(source_work_id,source_artifact_id,locator_type,heading_path,display_citation)
SELECT a.source_work_id,a.source_artifact_id,'heading','Space Combat > Special Considerations > Missiles',
 CASE w.work_code WHEN 'cepheus-engine.ogn' THEN 'Cepheus Engine SRD, Space Combat: Missiles'
 ELSE 'Cepheus Engine v9.1, Space Combat: Missiles' END FROM src_artifact a JOIN src_work w USING(source_work_id)
WHERE (w.work_code='cepheus-engine.ogn' AND a.source_uri LIKE '%cepheus-engine-space-combat/')
 OR (w.work_code='cepheus-engine.github-v9.1' AND a.source_uri='src/book2/space-combat.md') ON CONFLICT DO NOTHING;
WITH p AS (SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine')
INSERT INTO rule_rule(content_package_id,rule_code,name,rule_category,rule_status,description)
SELECT content_package_id,'combat.space.missile-flight','Space Combat Missile Flight','combat','approved',
 'Missile launch Effect determines later hit target; range determines arrival, and smart missiles repeat missed attacks.' FROM p;
CREATE TABLE rule_space_combat_missile_range(
 rule_id bigint NOT NULL REFERENCES rule_rule(rule_id),range_band_code text NOT NULL REFERENCES rule_space_range_band(range_band_code),
 launch_available boolean NOT NULL,turns_to_impact smallint,PRIMARY KEY(rule_id,range_band_code),
 CHECK(launch_available=(turns_to_impact IS NOT NULL)),CHECK(turns_to_impact IS NULL OR turns_to_impact IN(1,2)));
INSERT INTO rule_space_combat_missile_range SELECT r.rule_id,v.range_code,v.turns IS NOT NULL,v.turns
FROM rule_rule r CROSS JOIN (VALUES('adjacent',NULL::smallint),('close',NULL),('short',1),('medium',1),('long',1),('very_long',2),('distant',2)) v(range_code,turns)
WHERE r.rule_code='combat.space.missile-flight';
CREATE TABLE rule_space_combat_missile_launch_effect(
 rule_id bigint NOT NULL REFERENCES rule_rule(rule_id),effect_range int4range NOT NULL,impact_target_number smallint NOT NULL CHECK(impact_target_number IN(6,7,8,10,11)),
 display_order smallint NOT NULL,PRIMARY KEY(rule_id,effect_range),UNIQUE(rule_id,display_order),CHECK(NOT isempty(effect_range)));
ALTER TABLE rule_space_combat_missile_launch_effect ADD CONSTRAINT rule_space_combat_missile_effect_no_overlap EXCLUDE USING gist(rule_id WITH =,effect_range WITH &&);
INSERT INTO rule_space_combat_missile_launch_effect SELECT r.rule_id,v.band,v.target,v.ord FROM rule_rule r CROSS JOIN (VALUES
 (int4range(NULL,-5,'[)'),11::smallint,1::smallint),(int4range(-5,0,'[)'),10,2),(int4range(0,1,'[)'),8,3),(int4range(1,6,'[)'),7,4),(int4range(6,NULL,'[)'),6,5)
) v(band,target,ord) WHERE r.rule_code='combat.space.missile-flight';
CREATE TABLE rule_space_combat_missile_behavior(
 rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),thrust smallint NOT NULL CHECK(thrust=10),endurance_turns smallint NOT NULL CHECK(endurance_turns=4),
 launch_difficulty_rule_id bigint NOT NULL REFERENCES rule_difficulty(rule_id),smart_fixed_target smallint NOT NULL CHECK(smart_fixed_target=8),
 smart_repeats_after_miss boolean NOT NULL,reactions_wait_until_arrival boolean NOT NULL);
INSERT INTO rule_space_combat_missile_behavior SELECT flight.rule_id,10,4,difficulty.rule_id,8,true,true FROM rule_rule flight CROSS JOIN rule_rule difficulty
WHERE flight.rule_code='combat.space.missile-flight' AND difficulty.rule_code='difficulty.average';
INSERT INTO src_record_provenance(rule_id,content_package_id,source_locator_id,provenance_class,is_primary_citation)
SELECT r.rule_id,r.content_package_id,l.source_locator_id,CASE w.work_code WHEN 'cepheus-engine.ogn' THEN 'direct' ELSE 'corroborating' END,w.work_code='cepheus-engine.ogn'
FROM rule_rule r CROSS JOIN src_locator l JOIN src_work w USING(source_work_id) WHERE r.rule_code='combat.space.missile-flight'
 AND l.heading_path='Space Combat > Special Considerations > Missiles' AND w.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1');
ALTER TABLE rule_space_combat_weapon_profile DROP CONSTRAINT rule_space_combat_weapon_profile_weapon_profile_code_check;
ALTER TABLE rule_space_combat_weapon_profile ADD CONSTRAINT rule_space_combat_weapon_profile_weapon_profile_code_check
 CHECK(weapon_profile_code IN('pulse-laser','beam-laser','particle-beam','fusion-gun','meson-gun','sandcaster','missile'));
INSERT INTO rule_space_combat_weapon_profile SELECT weapon_rule_id,'missile',true FROM ship_weapon_definition WHERE weapon_code IN('missile-rack','missile-bank');

ALTER TABLE senc_missile_salvo ALTER COLUMN launch_attack_id DROP NOT NULL;
ALTER TABLE senc_missile_salvo ADD COLUMN launch_receipt_id bigint UNIQUE;
CREATE TABLE senc_missile_launch_receipt(
 missile_launch_receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,mount_weapon_attack_check_id bigint NOT NULL UNIQUE REFERENCES senc_mount_weapon_attack_check(mount_weapon_attack_check_id),
 engagement_id bigint NOT NULL,campaign_id bigint NOT NULL,space_combat_round_id bigint NOT NULL,attacker_vessel_id bigint NOT NULL,target_vessel_id bigint NOT NULL,
 missile_code text NOT NULL REFERENCES rule_ship_missile(missile_code),missile_count smallint NOT NULL CHECK(missile_count>0),range_band_code text NOT NULL,
 launch_effect smallint NOT NULL,impact_target_number smallint NOT NULL CHECK(impact_target_number BETWEEN 2 AND 12),launched_round integer NOT NULL CHECK(launched_round>0),
 turns_to_impact smallint NOT NULL CHECK(turns_to_impact IN(1,2)),impact_round integer NOT NULL CHECK(impact_round=launched_round+turns_to_impact),
 smart_missiles boolean NOT NULL,recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(space_combat_round_id,engagement_id,campaign_id) REFERENCES senc_round(space_combat_round_id,engagement_id,campaign_id),
 FOREIGN KEY(attacker_vessel_id,engagement_id,campaign_id) REFERENCES senc_vessel(senc_vessel_id,engagement_id,campaign_id),
 FOREIGN KEY(target_vessel_id,engagement_id,campaign_id) REFERENCES senc_vessel(senc_vessel_id,engagement_id,campaign_id));
ALTER TABLE senc_missile_salvo ADD CONSTRAINT senc_missile_salvo_launch_receipt_fk FOREIGN KEY(launch_receipt_id) REFERENCES senc_missile_launch_receipt(missile_launch_receipt_id);
ALTER TABLE senc_missile_salvo ADD CONSTRAINT senc_missile_salvo_one_launch_origin CHECK(num_nonnulls(launch_attack_id,launch_receipt_id)=1);
CREATE FUNCTION senc_validate_missile_launch_receipt() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE attack senc_mount_weapon_attack_check%ROWTYPE; declaration senc_mount_attack_declaration%ROWTYPE; weapon ship_weapon_definition%ROWTYPE;
 expected_turns smallint; expected_target smallint; expected_round integer; missile rule_ship_missile%ROWTYPE;
BEGIN
 SELECT * INTO STRICT attack FROM senc_mount_weapon_attack_check WHERE mount_weapon_attack_check_id=NEW.mount_weapon_attack_check_id;
 SELECT * INTO STRICT declaration FROM senc_mount_attack_declaration WHERE mount_attack_declaration_id=attack.mount_attack_declaration_id;
 SELECT * INTO STRICT weapon FROM ship_weapon_definition WHERE weapon_rule_id=attack.weapon_rule_id;
 SELECT * INTO STRICT missile FROM rule_ship_missile WHERE missile_code=NEW.missile_code;
 SELECT turns_to_impact INTO STRICT expected_turns FROM rule_space_combat_missile_range range_rule JOIN rule_rule r ON r.rule_id=range_rule.rule_id
  WHERE r.rule_code='combat.space.missile-flight' AND range_rule.range_band_code=declaration.range_band_code AND launch_available;
 SELECT round_number INTO STRICT expected_round FROM senc_round WHERE space_combat_round_id=declaration.space_combat_round_id;
 IF missile.fixed_attack_target IS NOT NULL THEN expected_target:=missile.fixed_attack_target;
 ELSE SELECT impact_target_number INTO STRICT expected_target FROM rule_space_combat_missile_launch_effect band JOIN rule_rule r ON r.rule_id=band.rule_id
  WHERE r.rule_code='combat.space.missile-flight' AND band.effect_range @> attack.effect; END IF;
 IF weapon.weapon_kind<>'missile' OR attack.weapon_profile_code<>'missile' OR attack.difficulty_rule_id<>(SELECT launch_difficulty_rule_id FROM rule_space_combat_missile_behavior)
  OR declaration.engagement_id<>NEW.engagement_id OR declaration.campaign_id<>NEW.campaign_id OR declaration.space_combat_round_id<>NEW.space_combat_round_id
  OR declaration.attacker_vessel_id<>NEW.attacker_vessel_id OR declaration.target_vessel_id<>NEW.target_vessel_id OR declaration.range_band_code<>NEW.range_band_code
  OR NEW.missile_count<>weapon.ammunition_per_attack OR NEW.launch_effect<>attack.effect OR NEW.impact_target_number<>expected_target
  OR NEW.launched_round<>expected_round OR NEW.turns_to_impact<>expected_turns OR NEW.impact_round<>expected_round+expected_turns
  OR NEW.smart_missiles<>(missile.fixed_attack_target IS NOT NULL AND missile.may_repeat_missed_attack) THEN
  RAISE EXCEPTION 'Missile launch receipt does not match installed launcher, launch check, missile type, range, or arrival timing' USING ERRCODE='23514'; END IF; RETURN NEW;
END $$;
CREATE TRIGGER senc_missile_launch_valid BEFORE INSERT ON senc_missile_launch_receipt FOR EACH ROW EXECUTE FUNCTION senc_validate_missile_launch_receipt();
CREATE FUNCTION senc_create_missile_salvo() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
 INSERT INTO senc_missile_salvo(launch_receipt_id,engagement_id,campaign_id,target_vessel_id,missile_count,smart_missiles,launched_round,impact_round,missiles_remaining)
 VALUES(NEW.missile_launch_receipt_id,NEW.engagement_id,NEW.campaign_id,NEW.target_vessel_id,NEW.missile_count,NEW.smart_missiles,NEW.launched_round,NEW.impact_round,NEW.missile_count); RETURN NEW; END $$;
CREATE TRIGGER senc_missile_launch_create_salvo AFTER INSERT ON senc_missile_launch_receipt FOR EACH ROW EXECUTE FUNCTION senc_create_missile_salvo();
CREATE FUNCTION senc_reject_missile_launch_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Missile launch receipts are immutable'; END $$;
CREATE TRIGGER senc_missile_launch_immutable BEFORE UPDATE OR DELETE ON senc_missile_launch_receipt FOR EACH ROW EXECUTE FUNCTION senc_reject_missile_launch_mutation();
