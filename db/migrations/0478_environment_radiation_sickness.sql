CREATE TABLE env_radiation_sickness_case(
 radiation_sickness_case_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
 radiation_exposure_attempt_id bigint NOT NULL UNIQUE REFERENCES env_radiation_exposure_attempt(radiation_exposure_attempt_id),actor_id bigint NOT NULL,campaign_id bigint NOT NULL,
 initial_radiation_effect_band_id bigint NOT NULL REFERENCES rule_radiation_effect_band(radiation_effect_band_id),case_status text NOT NULL DEFAULT 'active' CHECK(case_status IN('active','resisted')),
 next_check_at timestamptz,concurrency_version bigint NOT NULL DEFAULT 1 CHECK(concurrency_version>0),opened_at timestamptz NOT NULL DEFAULT clock_timestamp(),resolved_at timestamptz,
 FOREIGN KEY(actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id),CHECK((case_status='active')=(resolved_at IS NULL)),CHECK(case_status='active' OR next_check_at IS NULL)
);
CREATE TABLE env_radiation_sickness_check_receipt(
 radiation_sickness_check_receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
 radiation_sickness_case_id bigint NOT NULL REFERENCES env_radiation_sickness_case(radiation_sickness_case_id),check_sequence integer NOT NULL CHECK(check_sequence>0),
 task_command_id bigint NOT NULL UNIQUE REFERENCES cmd_actor_task_receipt(command_id),radiation_effect_band_id bigint NOT NULL REFERENCES rule_radiation_effect_band(radiation_effect_band_id),
 task_succeeded boolean NOT NULL,damage_die_result smallint CHECK(damage_die_result BETWEEN 1 AND 6),rolled_damage smallint NOT NULL CHECK(rolled_damage>=0),
 interval_die_total smallint,interval_seconds bigint,case_version_before bigint NOT NULL,case_version_after bigint NOT NULL CHECK(case_version_after=case_version_before+1),
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),UNIQUE(radiation_sickness_case_id,check_sequence),
 CHECK((task_succeeded AND damage_die_result IS NULL AND rolled_damage=0 AND interval_die_total IS NULL AND interval_seconds IS NULL)
 OR (NOT task_succeeded AND damage_die_result IS NOT NULL AND rolled_damage>0 AND interval_die_total IS NOT NULL AND interval_seconds IS NOT NULL))
);
ALTER TABLE health_damage_instance ADD COLUMN radiation_sickness_check_receipt_id bigint UNIQUE REFERENCES env_radiation_sickness_check_receipt(radiation_sickness_check_receipt_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE health_damage_instance DROP CONSTRAINT health_damage_exactly_one_source_check,
 ADD CONSTRAINT health_damage_exactly_one_source_check CHECK(num_nonnulls(attack_command_id,environmental_command_id,explosion_command_id,grapple_option_command_id,personal_scale_attack_receipt_id,acid_damage_attempt_id,acid_fume_task_command_id,temperature_damage_receipt_id,fire_resolution_receipt_id,fall_attempt_id,poison_attempt_id,radiation_sickness_check_receipt_id)
 +CASE WHEN crew_damage_location_hit_receipt_id IS NULL THEN 0 ELSE 1 END+CASE WHEN missile_crew_hit_receipt_id IS NULL THEN 0 ELSE 1 END=1);

CREATE FUNCTION env_open_radiation_sickness_case() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE attempt env_radiation_exposure_attempt%ROWTYPE;band_id bigint;
BEGIN IF NEW.rads_added=0 OR NEW.band_code_after='mild' THEN RETURN NEW;END IF;
 SELECT * INTO STRICT attempt FROM env_radiation_exposure_attempt WHERE radiation_exposure_attempt_id=NEW.radiation_exposure_attempt_id;
 SELECT radiation_effect_band_id INTO STRICT band_id FROM rule_radiation_effect_band WHERE band_code=NEW.band_code_after;
 INSERT INTO env_radiation_sickness_case(radiation_exposure_attempt_id,actor_id,campaign_id,initial_radiation_effect_band_id)
 VALUES(NEW.radiation_exposure_attempt_id,attempt.actor_id,attempt.campaign_id,band_id);RETURN NEW;END $$;
CREATE TRIGGER env_radiation_sickness_case_open AFTER INSERT ON env_radiation_exposure_receipt FOR EACH ROW EXECUTE FUNCTION env_open_radiation_sickness_case();

CREATE FUNCTION env_finalize_radiation_sickness_check() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE sickness env_radiation_sickness_case%ROWTYPE;state actor_radiation_state%ROWTYPE;band rule_radiation_effect_band%ROWTYPE;task cmd_actor_task_receipt%ROWTYPE;average_id bigint;expected_damage integer;expected_seconds bigint;unit_seconds bigint;
BEGIN SELECT * INTO STRICT sickness FROM env_radiation_sickness_case WHERE radiation_sickness_case_id=NEW.radiation_sickness_case_id FOR UPDATE;
 SELECT * INTO STRICT state FROM actor_radiation_state WHERE actor_id=sickness.actor_id;SELECT * INTO STRICT band FROM rule_radiation_effect_band WHERE radiation_effect_band_id=state.radiation_effect_band_id;
 SELECT * INTO STRICT task FROM cmd_actor_task_receipt WHERE command_id=NEW.task_command_id;SELECT rule_id INTO STRICT average_id FROM rule_rule WHERE rule_code='difficulty.average';
 IF sickness.case_status<>'active' OR (sickness.next_check_at IS NOT NULL AND NEW.recorded_at<sickness.next_check_at) OR NEW.check_sequence<>(SELECT count(*)+1 FROM env_radiation_sickness_check_receipt WHERE radiation_sickness_case_id=sickness.radiation_sickness_case_id)
  OR NEW.case_version_before<>sickness.concurrency_version OR NEW.radiation_effect_band_id<>band.radiation_effect_band_id OR task.actor_id<>sickness.actor_id
  OR task.characteristic_rule_id<>(SELECT rule_id FROM rule_rule WHERE rule_code='characteristic.endurance') OR task.skill_rule_id IS NOT NULL OR task.difficulty_rule_id<>average_id
  OR task.circumstance_modifier<>band.resistance_dm OR NEW.task_succeeded<>task.succeeded THEN RAISE EXCEPTION 'Radiation sickness check must match active case, timing, current band, Average Endurance task, listed DM, sequence, and version' USING ERRCODE='23514';END IF;
 IF NEW.task_succeeded THEN UPDATE env_radiation_sickness_case SET case_status='resisted',next_check_at=NULL,resolved_at=NEW.recorded_at,concurrency_version=NEW.case_version_after WHERE radiation_sickness_case_id=sickness.radiation_sickness_case_id;
 ELSE expected_damage:=NEW.damage_die_result+band.damage_flat_modifier;unit_seconds:=CASE band.interval_unit WHEN 'hours' THEN 3600 WHEN 'days' THEN 86400 ELSE 604800 END;expected_seconds:=NEW.interval_die_total::bigint*unit_seconds;
  IF NEW.rolled_damage<>expected_damage OR NEW.interval_die_total<band.interval_dice_count OR NEW.interval_die_total>band.interval_dice_count*6 OR NEW.interval_seconds<>expected_seconds THEN RAISE EXCEPTION 'Failed radiation sickness check must match published damage and interval dice' USING ERRCODE='23514';END IF;
  INSERT INTO health_damage_instance(target_actor_id,penetrating_damage,radiation_sickness_check_receipt_id) VALUES(sickness.actor_id,expected_damage,NEW.radiation_sickness_check_receipt_id);
  UPDATE env_radiation_sickness_case SET next_check_at=NEW.recorded_at+make_interval(secs=>expected_seconds),concurrency_version=NEW.case_version_after WHERE radiation_sickness_case_id=sickness.radiation_sickness_case_id;END IF;RETURN NEW;END $$;
CREATE TRIGGER env_radiation_sickness_check_final AFTER INSERT ON env_radiation_sickness_check_receipt FOR EACH ROW EXECUTE FUNCTION env_finalize_radiation_sickness_check();
CREATE FUNCTION env_reject_radiation_sickness_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Radiation sickness cases and receipts are immutable outside receipt finalization';END $$;
CREATE TRIGGER env_radiation_sickness_receipt_immutable BEFORE UPDATE OR DELETE ON env_radiation_sickness_check_receipt FOR EACH ROW EXECUTE FUNCTION env_reject_radiation_sickness_mutation();
CREATE FUNCTION env_guard_radiation_sickness_case() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF pg_trigger_depth()<2 THEN RAISE EXCEPTION 'Radiation sickness case changes require an immutable check receipt' USING ERRCODE='23514';END IF;RETURN NEW;END $$;
CREATE TRIGGER env_radiation_sickness_case_guard BEFORE UPDATE OR DELETE ON env_radiation_sickness_case FOR EACH ROW EXECUTE FUNCTION env_guard_radiation_sickness_case();
