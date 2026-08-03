INSERT INTO src_locator(source_work_id,source_artifact_id,locator_type,heading_path,display_citation)
SELECT artifact.source_work_id,artifact.source_artifact_id,'heading','Environments and Hazards > Falling and Gravity',
 CASE work.work_code WHEN 'cepheus-engine.ogn' THEN 'Cepheus Engine SRD, Environments and Hazards: Falling and Gravity' ELSE 'Cepheus Engine v9.1, Environments and Hazards: Falling and Gravity' END
FROM src_artifact artifact JOIN src_work work USING(source_work_id)
WHERE artifact.source_uri IN('src/book3/environments-and-hazards.md','https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-environments-and-hazards/') ON CONFLICT DO NOTHING;

WITH package AS(SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine')
INSERT INTO rule_rule(content_package_id,rule_code,name,rule_category,rule_status,description)
SELECT content_package_id,'environment.falling-gravity','Falling and Gravity','other','approved',
 'Roll 1D6 per complete two metres fallen, multiply the rolled total by local gravity, and apply the agreed nearest-point rounding rule.' FROM package;
CREATE TABLE rule_falling_gravity(
 rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),millimeters_per_damage_die integer NOT NULL CHECK(millimeters_per_damage_die=2000),
 damage_die_sides smallint NOT NULL CHECK(damage_die_sides=6),standard_gravity_milligee integer NOT NULL CHECK(standard_gravity_milligee=1000),
 incomplete_distance_policy text NOT NULL CHECK(incomplete_distance_policy='complete-increments-only'),
 gravity_scaling_stage text NOT NULL CHECK(gravity_scaling_stage='after-roll-total'),rounding_policy text NOT NULL CHECK(rounding_policy='nearest-half-up')
);
INSERT INTO rule_falling_gravity SELECT rule_id,2000,6,1000,'complete-increments-only','after-roll-total','nearest-half-up'
FROM rule_rule WHERE rule_code='environment.falling-gravity';
INSERT INTO src_record_provenance(rule_id,content_package_id,source_locator_id,provenance_class,is_primary_citation)
SELECT rule.rule_id,rule.content_package_id,locator.source_locator_id,CASE work.work_code WHEN 'cepheus-engine.ogn' THEN 'direct' ELSE 'corroborating' END,work.work_code='cepheus-engine.ogn'
FROM rule_rule rule CROSS JOIN src_locator locator JOIN src_work work USING(source_work_id)
WHERE rule.rule_code='environment.falling-gravity' AND locator.heading_path='Environments and Hazards > Falling and Gravity' AND work.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1');
INSERT INTO rule_interpretation(rule_id,interpretation_type,decision_register_entry,rationale)
SELECT rule_id,'agreed_interpretation','CE-ENV-002',
 'Agreed 2026-08-02: count complete two-metre increments, multiply the rolled total by gravity, and round to the nearest whole damage point with exact halves upward; retain exact millipoints in receipts.'
FROM rule_rule WHERE rule_code='environment.falling-gravity';

CREATE TABLE env_fall_attempt(
 fall_attempt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
 actor_id bigint NOT NULL,campaign_id bigint NOT NULL,distance_millimeters bigint NOT NULL CHECK(distance_millimeters>=0),
 gravity_milligee integer NOT NULL CHECK(gravity_milligee>=0),damage_dice_count integer NOT NULL CHECK(damage_dice_count>=0),
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),FOREIGN KEY(actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id)
);
CREATE TABLE env_fall_damage_die(
 fall_attempt_id bigint NOT NULL REFERENCES env_fall_attempt(fall_attempt_id),die_order integer NOT NULL CHECK(die_order>0),result smallint NOT NULL CHECK(result BETWEEN 1 AND 6),PRIMARY KEY(fall_attempt_id,die_order)
);
CREATE TABLE env_fall_damage_receipt(
 fall_attempt_id bigint PRIMARY KEY REFERENCES env_fall_attempt(fall_attempt_id),rolled_damage integer NOT NULL CHECK(rolled_damage>=0),
 scaled_damage_millipoints bigint NOT NULL CHECK(scaled_damage_millipoints>=0),applied_damage integer NOT NULL CHECK(applied_damage>=0),
 damage_instance_id bigint UNIQUE,recorded_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
ALTER TABLE health_damage_instance ADD COLUMN fall_attempt_id bigint UNIQUE REFERENCES env_fall_attempt(fall_attempt_id);
ALTER TABLE health_damage_instance DROP CONSTRAINT health_damage_exactly_one_source_check,
 ADD CONSTRAINT health_damage_exactly_one_source_check CHECK(
 num_nonnulls(attack_command_id,environmental_command_id,explosion_command_id,grapple_option_command_id,personal_scale_attack_receipt_id,acid_damage_attempt_id,acid_fume_task_command_id,temperature_damage_receipt_id,fire_resolution_receipt_id,fall_attempt_id)
 +CASE WHEN crew_damage_location_hit_receipt_id IS NULL THEN 0 ELSE 1 END+CASE WHEN missile_crew_hit_receipt_id IS NULL THEN 0 ELSE 1 END=1);
ALTER TABLE env_fall_damage_receipt ADD CONSTRAINT env_fall_damage_instance_fk FOREIGN KEY(damage_instance_id) REFERENCES health_damage_instance(damage_instance_id);

CREATE FUNCTION env_validate_fall_attempt() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
 IF NEW.damage_dice_count<>NEW.distance_millimeters/2000 THEN RAISE EXCEPTION 'Fall damage dice must equal complete two-metre increments' USING ERRCODE='23514';END IF;RETURN NEW;END $$;
CREATE TRIGGER env_fall_attempt_valid BEFORE INSERT ON env_fall_attempt FOR EACH ROW EXECUTE FUNCTION env_validate_fall_attempt();
CREATE FUNCTION env_validate_fall_die() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE attempt env_fall_attempt%ROWTYPE;BEGIN
 SELECT * INTO STRICT attempt FROM env_fall_attempt WHERE fall_attempt_id=NEW.fall_attempt_id FOR UPDATE;
 IF EXISTS(SELECT 1 FROM env_fall_damage_receipt WHERE fall_attempt_id=NEW.fall_attempt_id) OR NEW.die_order>attempt.damage_dice_count THEN RAISE EXCEPTION 'Fall die exceeds unresolved attempt profile' USING ERRCODE='23514';END IF;RETURN NEW;END $$;
CREATE TRIGGER env_fall_die_valid BEFORE INSERT ON env_fall_damage_die FOR EACH ROW EXECUTE FUNCTION env_validate_fall_die();
CREATE FUNCTION env_finalize_fall_damage() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE attempt env_fall_attempt%ROWTYPE;n integer;total integer;scaled bigint;applied integer;damage_id bigint;BEGIN
 SELECT * INTO STRICT attempt FROM env_fall_attempt WHERE fall_attempt_id=NEW.fall_attempt_id FOR UPDATE;
 SELECT count(*),coalesce(sum(result),0) INTO n,total FROM env_fall_damage_die WHERE fall_attempt_id=NEW.fall_attempt_id;
 scaled:=total::bigint*attempt.gravity_milligee;applied:=(scaled+500)/1000;
 IF n<>attempt.damage_dice_count OR NEW.rolled_damage<>total OR NEW.scaled_damage_millipoints<>scaled OR NEW.applied_damage<>applied THEN
  RAISE EXCEPTION 'Fall receipt requires complete dice, gravity-scaled millipoints, and agreed nearest-half-up damage' USING ERRCODE='23514';END IF;
 IF applied>0 THEN INSERT INTO health_damage_instance(target_actor_id,penetrating_damage,fall_attempt_id) VALUES(attempt.actor_id,applied,attempt.fall_attempt_id) RETURNING damage_instance_id INTO damage_id;NEW.damage_instance_id:=damage_id;END IF;
 RETURN NEW;END $$;
CREATE TRIGGER env_fall_damage_final BEFORE INSERT ON env_fall_damage_receipt FOR EACH ROW EXECUTE FUNCTION env_finalize_fall_damage();
CREATE FUNCTION env_reject_fall_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Fall attempts, dice, and receipts are immutable';END $$;
CREATE TRIGGER env_fall_attempt_immutable BEFORE UPDATE OR DELETE ON env_fall_attempt FOR EACH ROW EXECUTE FUNCTION env_reject_fall_mutation();
CREATE TRIGGER env_fall_die_immutable BEFORE UPDATE OR DELETE ON env_fall_damage_die FOR EACH ROW EXECUTE FUNCTION env_reject_fall_mutation();
CREATE TRIGGER env_fall_receipt_immutable BEFORE UPDATE OR DELETE ON env_fall_damage_receipt FOR EACH ROW EXECUTE FUNCTION env_reject_fall_mutation();
