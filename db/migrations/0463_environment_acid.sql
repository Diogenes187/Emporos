INSERT INTO src_artifact(source_work_id,artifact_kind,source_uri,source_revision,byte_length,checksum_sha256,media_type,local_role)
SELECT source_work_id,'repository_file','src/book3/environments-and-hazards.md','0839018902355215fb8148f0b4ce1b1f8e011080',12314,
 '71429402337c466f6c523d9958fdf95c1836c4b8b2048bf99e0c69454b826f2b','text/markdown','governing'
FROM src_work WHERE work_code='cepheus-engine.github-v9.1' ON CONFLICT DO NOTHING;
INSERT INTO src_artifact(source_work_id,artifact_kind,source_uri,source_revision,media_type,local_role)
SELECT source_work_id,'web_page','https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-environments-and-hazards/',
 'reviewed-2026-08-02','text/html','governing' FROM src_work WHERE work_code='cepheus-engine.ogn' ON CONFLICT DO NOTHING;
INSERT INTO src_locator(source_work_id,source_artifact_id,locator_type,heading_path,display_citation)
SELECT artifact.source_work_id,artifact.source_artifact_id,'heading','Environments and Hazards > Acid',
 CASE work.work_code WHEN 'cepheus-engine.ogn' THEN 'Cepheus Engine SRD, Environments and Hazards: Acid'
 ELSE 'Cepheus Engine v9.1, Environments and Hazards: Acid' END
FROM src_artifact artifact JOIN src_work work USING(source_work_id)
WHERE artifact.source_uri IN('src/book3/environments-and-hazards.md',
 'https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-environments-and-hazards/') ON CONFLICT DO NOTHING;

WITH package AS(SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine')
INSERT INTO rule_rule(content_package_id,rule_code,name,rule_category,rule_status,description)
SELECT content_package_id,'environment.acid','Acid Exposure','other','approved',
 'Caustic contact, immersion, attacks, poisonous fumes, immunity, and continuing suffocation boundary.' FROM package;
CREATE TABLE rule_environment_acid (
 rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),contact_damage_dice smallint NOT NULL CHECK(contact_damage_dice=1),
 immersion_damage_dice smallint NOT NULL CHECK(immersion_damage_dice=10),damage_die_sides smallint NOT NULL CHECK(damage_die_sides=6),
 attack_counts_as_exposure_round boolean NOT NULL CHECK(attack_counts_as_exposure_round),fumes_are_poisonous boolean NOT NULL CHECK(fumes_are_poisonous),
 fume_difficulty_rule_id bigint NOT NULL REFERENCES rule_difficulty(rule_id),fume_characteristic_rule_id bigint NOT NULL REFERENCES rule_characteristic(rule_id),
 fume_damage_dice smallint NOT NULL CHECK(fume_damage_dice=1),follow_up_delay_seconds smallint NOT NULL CHECK(follow_up_delay_seconds=60),
 caustic_immunity_prevents_acid_damage boolean NOT NULL CHECK(caustic_immunity_prevents_acid_damage),
 immersion_suffocation_still_applies_when_breathing_required boolean NOT NULL CHECK(immersion_suffocation_still_applies_when_breathing_required)
);
INSERT INTO rule_environment_acid SELECT acid.rule_id,1,10,6,true,true,difficulty.rule_id,characteristic.rule_id,1,60,true,true
FROM rule_rule acid CROSS JOIN rule_rule difficulty CROSS JOIN rule_rule characteristic
WHERE acid.rule_code='environment.acid' AND difficulty.rule_code='difficulty.average' AND characteristic.rule_code='characteristic.endurance';
INSERT INTO src_record_provenance(rule_id,content_package_id,source_locator_id,provenance_class,is_primary_citation)
SELECT rule.rule_id,rule.content_package_id,locator.source_locator_id,
 CASE work.work_code WHEN 'cepheus-engine.ogn' THEN 'direct' ELSE 'corroborating' END,work.work_code='cepheus-engine.ogn'
FROM rule_rule rule CROSS JOIN src_locator locator JOIN src_work work USING(source_work_id)
WHERE rule.rule_code='environment.acid' AND locator.heading_path='Environments and Hazards > Acid'
 AND work.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1');

CREATE TABLE actor_environmental_immunity (
 actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),hazard_code text NOT NULL CHECK(hazard_code='acid'),
 source_reference text NOT NULL CHECK(btrim(source_reference)<>''),recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY(actor_id,hazard_code)
);
CREATE TABLE env_acid_exposure (
 acid_exposure_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
 actor_id bigint NOT NULL,campaign_id bigint NOT NULL,exposure_kind text NOT NULL CHECK(exposure_kind IN('contact','total-immersion','acid-attack')),
 breathing_required boolean NOT NULL,exposure_status text NOT NULL DEFAULT 'active' CHECK(exposure_status IN('active','ended')),
 concurrency_version bigint NOT NULL DEFAULT 1 CHECK(concurrency_version>0),started_at timestamptz NOT NULL DEFAULT clock_timestamp(),ended_at timestamptz,
 FOREIGN KEY(actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id),
 CHECK((exposure_status='active')=(ended_at IS NULL)),CHECK(exposure_kind='total-immersion' OR NOT breathing_required)
);
CREATE UNIQUE INDEX env_one_active_acid_exposure ON env_acid_exposure(actor_id,exposure_kind) WHERE exposure_status='active';
CREATE TABLE env_acid_damage_attempt (
 acid_damage_attempt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,acid_exposure_id bigint NOT NULL REFERENCES env_acid_exposure(acid_exposure_id),
 exposure_round integer NOT NULL CHECK(exposure_round>0),actor_id bigint NOT NULL,campaign_id bigint NOT NULL,exposure_kind text NOT NULL,
 caustic_immunity boolean NOT NULL,damage_dice_count smallint NOT NULL CHECK(damage_dice_count IN(0,1,10)),damage_die_sides smallint NOT NULL CHECK(damage_die_sides=6),
 suffocation_resolution_required boolean NOT NULL,recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),UNIQUE(acid_exposure_id,exposure_round),
 FOREIGN KEY(actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id)
);
CREATE TABLE env_acid_damage_die (
 acid_damage_attempt_id bigint NOT NULL REFERENCES env_acid_damage_attempt(acid_damage_attempt_id),die_order smallint NOT NULL CHECK(die_order>0),
 result smallint NOT NULL CHECK(result BETWEEN 1 AND 6),PRIMARY KEY(acid_damage_attempt_id,die_order)
);
CREATE TABLE env_acid_damage_receipt (
 acid_damage_attempt_id bigint PRIMARY KEY REFERENCES env_acid_damage_attempt(acid_damage_attempt_id),rolled_damage smallint NOT NULL CHECK(rolled_damage>=0),
 damage_instance_id bigint UNIQUE,recorded_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE env_acid_fume_exposure (
 acid_fume_exposure_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
 actor_id bigint NOT NULL,campaign_id bigint NOT NULL,large_acid_body boolean NOT NULL CHECK(large_acid_body),
 exposure_status text NOT NULL DEFAULT 'awaiting-initial' CHECK(exposure_status IN('awaiting-initial','awaiting-follow-up','completed')),
 concurrency_version bigint NOT NULL DEFAULT 1 CHECK(concurrency_version>0),started_at timestamptz NOT NULL DEFAULT clock_timestamp(),completed_at timestamptz,
 FOREIGN KEY(actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id),CHECK((exposure_status='completed')=(completed_at IS NOT NULL))
);
CREATE TABLE env_acid_fume_check_receipt (
 acid_fume_check_receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,acid_fume_exposure_id bigint NOT NULL REFERENCES env_acid_fume_exposure(acid_fume_exposure_id),
 check_stage text NOT NULL CHECK(check_stage IN('initial','one-minute-follow-up')),elapsed_seconds smallint NOT NULL CHECK(elapsed_seconds IN(0,60)),
 task_command_id bigint NOT NULL UNIQUE REFERENCES cmd_actor_task_receipt(command_id),task_succeeded boolean NOT NULL,
 damage_die_result smallint CHECK(damage_die_result BETWEEN 1 AND 6),damage_instance_id bigint UNIQUE,recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(acid_fume_exposure_id,check_stage),CHECK(task_succeeded=(damage_die_result IS NULL))
);

ALTER TABLE health_damage_instance ADD COLUMN acid_damage_attempt_id bigint UNIQUE REFERENCES env_acid_damage_attempt(acid_damage_attempt_id),
 ADD COLUMN acid_fume_task_command_id bigint UNIQUE REFERENCES cmd_actor_task_receipt(command_id);
ALTER TABLE health_damage_instance DROP CONSTRAINT health_damage_exactly_one_source_check,
 ADD CONSTRAINT health_damage_exactly_one_source_check CHECK(
  num_nonnulls(attack_command_id,environmental_command_id,explosion_command_id,grapple_option_command_id,personal_scale_attack_receipt_id,acid_damage_attempt_id,acid_fume_task_command_id)
  +CASE WHEN crew_damage_location_hit_receipt_id IS NULL THEN 0 ELSE 1 END+CASE WHEN missile_crew_hit_receipt_id IS NULL THEN 0 ELSE 1 END=1);
ALTER TABLE env_acid_damage_receipt ADD CONSTRAINT env_acid_damage_instance_fk FOREIGN KEY(damage_instance_id) REFERENCES health_damage_instance(damage_instance_id);
ALTER TABLE env_acid_fume_check_receipt ADD CONSTRAINT env_acid_fume_damage_instance_fk FOREIGN KEY(damage_instance_id) REFERENCES health_damage_instance(damage_instance_id);

CREATE FUNCTION env_validate_acid_damage_attempt() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE exposure env_acid_exposure%ROWTYPE; expected_dice smallint; immune boolean;
BEGIN SELECT * INTO STRICT exposure FROM env_acid_exposure WHERE acid_exposure_id=NEW.acid_exposure_id FOR UPDATE;
 SELECT EXISTS(SELECT 1 FROM actor_environmental_immunity WHERE actor_id=exposure.actor_id AND hazard_code='acid') INTO immune;
 expected_dice:=CASE WHEN immune THEN 0 WHEN exposure.exposure_kind='total-immersion' THEN 10 ELSE 1 END;
 IF exposure.exposure_status<>'active' OR NEW.actor_id<>exposure.actor_id OR NEW.campaign_id<>exposure.campaign_id
  OR NEW.exposure_kind<>exposure.exposure_kind OR NEW.caustic_immunity<>immune OR NEW.damage_dice_count<>expected_dice
  OR NEW.exposure_round<>(SELECT count(*)+1 FROM env_acid_damage_attempt WHERE acid_exposure_id=exposure.acid_exposure_id)
  OR NEW.suffocation_resolution_required<>(exposure.exposure_kind='total-immersion' AND exposure.breathing_required) THEN
  RAISE EXCEPTION 'Acid damage attempt must match active exposure, sequential round, immunity, damage dice, and suffocation boundary' USING ERRCODE='23514'; END IF;
 RETURN NEW; END $$;
CREATE TRIGGER env_acid_damage_attempt_valid BEFORE INSERT ON env_acid_damage_attempt FOR EACH ROW EXECUTE FUNCTION env_validate_acid_damage_attempt();
CREATE FUNCTION env_validate_acid_damage_die() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE attempt env_acid_damage_attempt%ROWTYPE;
BEGIN SELECT * INTO STRICT attempt FROM env_acid_damage_attempt WHERE acid_damage_attempt_id=NEW.acid_damage_attempt_id FOR UPDATE;
 IF EXISTS(SELECT 1 FROM env_acid_damage_receipt WHERE acid_damage_attempt_id=NEW.acid_damage_attempt_id) OR NEW.die_order>attempt.damage_dice_count THEN
  RAISE EXCEPTION 'Acid damage die exceeds its unresolved exposure profile' USING ERRCODE='23514'; END IF; RETURN NEW; END $$;
CREATE TRIGGER env_acid_damage_die_valid BEFORE INSERT ON env_acid_damage_die FOR EACH ROW EXECUTE FUNCTION env_validate_acid_damage_die();
CREATE FUNCTION env_finalize_acid_damage() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE attempt env_acid_damage_attempt%ROWTYPE;n integer;total integer;damage_id bigint;
BEGIN SELECT * INTO STRICT attempt FROM env_acid_damage_attempt WHERE acid_damage_attempt_id=NEW.acid_damage_attempt_id FOR UPDATE;
 SELECT count(*),coalesce(sum(result),0) INTO n,total FROM env_acid_damage_die WHERE acid_damage_attempt_id=NEW.acid_damage_attempt_id;
 IF n<>attempt.damage_dice_count OR NEW.rolled_damage<>total THEN RAISE EXCEPTION 'Acid damage receipt requires complete dice and exact total' USING ERRCODE='23514'; END IF;
 IF total>0 THEN INSERT INTO health_damage_instance(target_actor_id,penetrating_damage,acid_damage_attempt_id)
  VALUES(attempt.actor_id,total,attempt.acid_damage_attempt_id) RETURNING damage_instance_id INTO damage_id; NEW.damage_instance_id:=damage_id; END IF;
 RETURN NEW; END $$;
CREATE TRIGGER env_acid_damage_final BEFORE INSERT ON env_acid_damage_receipt FOR EACH ROW EXECUTE FUNCTION env_finalize_acid_damage();

CREATE FUNCTION env_finalize_acid_fume_check() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE exposure env_acid_fume_exposure%ROWTYPE;task cmd_actor_task_receipt%ROWTYPE;acid rule_environment_acid%ROWTYPE;expected_stage text;damage_id bigint;
BEGIN SELECT * INTO STRICT exposure FROM env_acid_fume_exposure WHERE acid_fume_exposure_id=NEW.acid_fume_exposure_id FOR UPDATE;
 SELECT * INTO STRICT task FROM cmd_actor_task_receipt WHERE command_id=NEW.task_command_id;
 SELECT profile.* INTO STRICT acid FROM rule_environment_acid profile JOIN rule_rule rule ON rule.rule_id=profile.rule_id WHERE rule.rule_code='environment.acid';
 expected_stage:=CASE exposure.exposure_status WHEN 'awaiting-initial' THEN 'initial' WHEN 'awaiting-follow-up' THEN 'one-minute-follow-up' END;
 IF expected_stage IS NULL OR NEW.check_stage<>expected_stage OR NEW.elapsed_seconds<>(CASE expected_stage WHEN 'initial' THEN 0 ELSE acid.follow_up_delay_seconds END)
  OR task.actor_id<>exposure.actor_id OR task.characteristic_rule_id<>acid.fume_characteristic_rule_id OR task.skill_rule_id IS NOT NULL
  OR task.difficulty_rule_id<>acid.fume_difficulty_rule_id OR task.circumstance_modifier<>0 OR NEW.task_succeeded<>task.succeeded THEN
  RAISE EXCEPTION 'Acid fume check must match its actor, Average Endurance task, stage, and one-minute schedule' USING ERRCODE='23514'; END IF;
 IF NOT NEW.task_succeeded THEN INSERT INTO health_damage_instance(target_actor_id,penetrating_damage,acid_fume_task_command_id)
  VALUES(exposure.actor_id,NEW.damage_die_result,NEW.task_command_id) RETURNING damage_instance_id INTO damage_id; NEW.damage_instance_id:=damage_id; END IF;
 UPDATE env_acid_fume_exposure SET exposure_status=CASE NEW.check_stage WHEN 'initial' THEN 'awaiting-follow-up' ELSE 'completed' END,
  completed_at=CASE WHEN NEW.check_stage='one-minute-follow-up' THEN clock_timestamp() END,concurrency_version=concurrency_version+1
 WHERE acid_fume_exposure_id=exposure.acid_fume_exposure_id; RETURN NEW; END $$;
CREATE TRIGGER env_acid_fume_check_final BEFORE INSERT ON env_acid_fume_check_receipt FOR EACH ROW EXECUTE FUNCTION env_finalize_acid_fume_check();

CREATE FUNCTION env_reject_acid_receipt_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Acid exposure receipts and dice are immutable'; END $$;
CREATE TRIGGER actor_environmental_immunity_immutable BEFORE UPDATE OR DELETE ON actor_environmental_immunity FOR EACH ROW EXECUTE FUNCTION env_reject_acid_receipt_mutation();
CREATE TRIGGER env_acid_damage_attempt_immutable BEFORE UPDATE OR DELETE ON env_acid_damage_attempt FOR EACH ROW EXECUTE FUNCTION env_reject_acid_receipt_mutation();
CREATE TRIGGER env_acid_damage_die_immutable BEFORE UPDATE OR DELETE ON env_acid_damage_die FOR EACH ROW EXECUTE FUNCTION env_reject_acid_receipt_mutation();
CREATE TRIGGER env_acid_damage_receipt_immutable BEFORE UPDATE OR DELETE ON env_acid_damage_receipt FOR EACH ROW EXECUTE FUNCTION env_reject_acid_receipt_mutation();
CREATE TRIGGER env_acid_fume_check_immutable BEFORE UPDATE OR DELETE ON env_acid_fume_check_receipt FOR EACH ROW EXECUTE FUNCTION env_reject_acid_receipt_mutation();
