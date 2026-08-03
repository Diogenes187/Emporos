CREATE TABLE env_antiradiation_dose_receipt(
 antiradiation_dose_receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
 actor_id bigint NOT NULL,campaign_id bigint NOT NULL,drug_rule_id bigint NOT NULL REFERENCES rule_personal_antiradiation_drug(drug_rule_id),
 radiation_exposure_attempt_id bigint REFERENCES env_radiation_exposure_attempt(radiation_exposure_attempt_id),prophylactic boolean NOT NULL,
 dose_number_in_rolling_day smallint NOT NULL CHECK(dose_number_in_rolling_day>0),rads_before integer NOT NULL CHECK(rads_before>=0),rads_removed integer NOT NULL CHECK(rads_removed>=0),
 rads_after integer NOT NULL CHECK(rads_after=rads_before-rads_removed),band_code_before text NOT NULL,band_code_after text NOT NULL,
 recovery_entitlement_points smallint NOT NULL CHECK(recovery_entitlement_points>=0),overdose_endurance_damage smallint NOT NULL CHECK(overdose_endurance_damage>=0),
 state_version_before bigint NOT NULL,state_version_after bigint NOT NULL CHECK(state_version_after=state_version_before+1),administered_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id),CHECK(prophylactic=(radiation_exposure_attempt_id IS NULL))
);
CREATE TABLE env_antiradiation_overdose_die(
 antiradiation_dose_receipt_id bigint PRIMARY KEY REFERENCES env_antiradiation_dose_receipt(antiradiation_dose_receipt_id),result smallint NOT NULL CHECK(result BETWEEN 1 AND 6)
);
CREATE TABLE actor_antiradiation_prophylaxis(
 actor_id bigint PRIMARY KEY,campaign_id bigint NOT NULL,antiradiation_dose_receipt_id bigint NOT NULL UNIQUE REFERENCES env_antiradiation_dose_receipt(antiradiation_dose_receipt_id),
 remaining_absorption_rads integer NOT NULL CHECK(remaining_absorption_rads>0),concurrency_version bigint NOT NULL CHECK(concurrency_version>0),
 FOREIGN KEY(actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id)
);
CREATE TABLE health_radiation_recovery_entitlement(
 recovery_entitlement_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,antiradiation_dose_receipt_id bigint NOT NULL UNIQUE REFERENCES env_antiradiation_dose_receipt(antiradiation_dose_receipt_id),
 actor_id bigint NOT NULL,campaign_id bigint NOT NULL,recoverable_points smallint NOT NULL CHECK(recoverable_points>0),recovery_kind text NOT NULL CHECK(recovery_kind='physical-healing-over-time'),
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),FOREIGN KEY(actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id)
);
CREATE FUNCTION env_finalize_antiradiation_dose() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE profile rule_personal_antiradiation_drug%ROWTYPE;state actor_radiation_state%ROWTYPE;before_band rule_radiation_effect_band%ROWTYPE;after_band rule_radiation_effect_band%ROWTYPE;
 exposure env_radiation_exposure_attempt%ROWTYPE;expected_dose integer;expected_removed integer;overdose_result smallint;expected_overdose smallint;endurance_rule bigint;endurance actor_characteristic%ROWTYPE;
BEGIN
 SELECT * INTO STRICT profile FROM rule_personal_antiradiation_drug WHERE drug_rule_id=NEW.drug_rule_id;
 SELECT * INTO STRICT state FROM actor_radiation_state WHERE actor_id=NEW.actor_id FOR UPDATE;
 SELECT * INTO STRICT before_band FROM rule_radiation_effect_band WHERE radiation_effect_band_id=state.radiation_effect_band_id;
 expected_dose:=(SELECT count(*) FROM env_antiradiation_dose_receipt WHERE actor_id=NEW.actor_id AND administered_at>NEW.administered_at-interval '24 hours' AND administered_at<=NEW.administered_at);
 SELECT result INTO overdose_result FROM env_antiradiation_overdose_die WHERE antiradiation_dose_receipt_id=NEW.antiradiation_dose_receipt_id;
 expected_overdose:=CASE WHEN expected_dose>profile.safe_doses_per_day THEN overdose_result ELSE 0 END;
 expected_removed:=CASE WHEN NEW.prophylactic THEN 0 ELSE least(state.total_rads,profile.absorbed_rads_per_dose) END;
 SELECT * INTO STRICT after_band FROM rule_radiation_effect_band WHERE minimum_rads<=state.total_rads-expected_removed AND (maximum_rads IS NULL OR maximum_rads>=state.total_rads-expected_removed);
 IF NOT NEW.prophylactic THEN SELECT attempt.* INTO STRICT exposure FROM env_radiation_exposure_attempt attempt JOIN env_radiation_exposure_receipt receipt USING(radiation_exposure_attempt_id) WHERE attempt.radiation_exposure_attempt_id=NEW.radiation_exposure_attempt_id;
  IF exposure.actor_id<>NEW.actor_id OR NEW.administered_at<exposure.recorded_at OR NEW.administered_at>exposure.recorded_at+make_interval(secs=>profile.post_exposure_window_seconds) THEN
   RAISE EXCEPTION 'Post-exposure anti-radiation dose must follow this actor exposure within the published window' USING ERRCODE='23514';END IF;END IF;
 IF NEW.dose_number_in_rolling_day<>expected_dose OR NEW.rads_before<>state.total_rads OR NEW.rads_removed<>expected_removed OR NEW.rads_after<>state.total_rads-expected_removed
  OR NEW.band_code_before<>before_band.band_code OR NEW.band_code_after<>after_band.band_code OR NEW.recovery_entitlement_points<>before_band.effective_endurance_penalty-after_band.effective_endurance_penalty
  OR NEW.overdose_endurance_damage<>expected_overdose
  OR NEW.state_version_before<>state.concurrency_version THEN RAISE EXCEPTION 'Anti-radiation receipt must match dosing, cumulative rads, bands, recovery entitlement, overdose, and state version' USING ERRCODE='23514';END IF;
 IF expected_dose<=profile.safe_doses_per_day AND EXISTS(SELECT 1 FROM env_antiradiation_overdose_die WHERE antiradiation_dose_receipt_id=NEW.antiradiation_dose_receipt_id) THEN RAISE EXCEPTION 'Safe anti-radiation dose cannot have an overdose die' USING ERRCODE='23514';END IF;
 IF NEW.overdose_endurance_damage>0 THEN SELECT rule_id INTO STRICT endurance_rule FROM rule_rule WHERE rule_code='characteristic.endurance';SELECT * INTO STRICT endurance FROM actor_characteristic WHERE actor_id=NEW.actor_id AND characteristic_rule_id=endurance_rule FOR UPDATE;
  UPDATE actor_characteristic SET current_value=greatest(0,current_value-NEW.overdose_endurance_damage),maximum_value=greatest(0,maximum_value-NEW.overdose_endurance_damage) WHERE actor_id=NEW.actor_id AND characteristic_rule_id=endurance_rule;END IF;
 UPDATE actor_radiation_state SET total_rads=NEW.rads_after,concurrency_version=NEW.state_version_after,updated_at=NEW.administered_at WHERE actor_id=NEW.actor_id;
 IF NEW.prophylactic THEN INSERT INTO actor_antiradiation_prophylaxis(actor_id,campaign_id,antiradiation_dose_receipt_id,remaining_absorption_rads,concurrency_version)
  VALUES(NEW.actor_id,NEW.campaign_id,NEW.antiradiation_dose_receipt_id,profile.absorbed_rads_per_dose,1)
  ON CONFLICT(actor_id) DO UPDATE SET antiradiation_dose_receipt_id=EXCLUDED.antiradiation_dose_receipt_id,remaining_absorption_rads=EXCLUDED.remaining_absorption_rads,concurrency_version=actor_antiradiation_prophylaxis.concurrency_version+1;END IF;
 IF NEW.recovery_entitlement_points>0 THEN INSERT INTO health_radiation_recovery_entitlement(antiradiation_dose_receipt_id,actor_id,campaign_id,recoverable_points) VALUES(NEW.antiradiation_dose_receipt_id,NEW.actor_id,NEW.campaign_id,NEW.recovery_entitlement_points);END IF;RETURN NEW;
END $$;
CREATE CONSTRAINT TRIGGER env_antiradiation_dose_final AFTER INSERT ON env_antiradiation_dose_receipt DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION env_finalize_antiradiation_dose();
CREATE FUNCTION env_reject_antiradiation_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Anti-radiation dose, overdose die, and recovery entitlement history is immutable';END $$;
CREATE TRIGGER env_antiradiation_dose_immutable BEFORE UPDATE OR DELETE ON env_antiradiation_dose_receipt FOR EACH ROW EXECUTE FUNCTION env_reject_antiradiation_mutation();
CREATE TRIGGER env_antiradiation_die_immutable BEFORE UPDATE OR DELETE ON env_antiradiation_overdose_die FOR EACH ROW EXECUTE FUNCTION env_reject_antiradiation_mutation();
CREATE TRIGGER health_radiation_recovery_immutable BEFORE UPDATE OR DELETE ON health_radiation_recovery_entitlement FOR EACH ROW EXECUTE FUNCTION env_reject_antiradiation_mutation();
CREATE FUNCTION env_guard_antiradiation_prophylaxis() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF pg_trigger_depth()<2 THEN RAISE EXCEPTION 'Anti-radiation prophylaxis changes require an immutable dose or exposure receipt' USING ERRCODE='23514';END IF;RETURN NEW;END $$;
CREATE TRIGGER actor_antiradiation_prophylaxis_guard BEFORE INSERT OR UPDATE OR DELETE ON actor_antiradiation_prophylaxis FOR EACH ROW EXECUTE FUNCTION env_guard_antiradiation_prophylaxis();
