ALTER TABLE actor_radiation_state
 ADD COLUMN radiation_effect_band_id bigint REFERENCES rule_radiation_effect_band(radiation_effect_band_id),
 ADD COLUMN effective_endurance_penalty smallint CHECK(effective_endurance_penalty BETWEEN 0 AND 10),
 ADD COLUMN radiation_unconscious boolean;
CREATE FUNCTION env_derive_radiation_state() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE band rule_radiation_effect_band%ROWTYPE; endurance smallint;
BEGIN
 SELECT * INTO STRICT band FROM rule_radiation_effect_band WHERE minimum_rads<=NEW.total_rads AND (maximum_rads IS NULL OR maximum_rads>=NEW.total_rads);
 SELECT characteristic.current_value INTO endurance FROM actor_characteristic characteristic JOIN rule_rule rule ON rule.rule_id=characteristic.characteristic_rule_id
 WHERE characteristic.actor_id=NEW.actor_id AND rule.rule_code='characteristic.endurance';
 NEW.radiation_effect_band_id:=band.radiation_effect_band_id;NEW.effective_endurance_penalty:=band.effective_endurance_penalty;
 NEW.radiation_unconscious:=coalesce(endurance-band.effective_endurance_penalty<0,false);RETURN NEW;
END $$;
CREATE TRIGGER actor_radiation_state_derive BEFORE INSERT OR UPDATE OF total_rads ON actor_radiation_state FOR EACH ROW EXECUTE FUNCTION env_derive_radiation_state();
UPDATE actor_radiation_state state SET radiation_effect_band_id=band.radiation_effect_band_id,
 effective_endurance_penalty=band.effective_endurance_penalty,radiation_unconscious=false
FROM rule_radiation_effect_band band
WHERE band.minimum_rads<=state.total_rads AND (band.maximum_rads IS NULL OR band.maximum_rads>=state.total_rads);
ALTER TABLE actor_radiation_state ALTER COLUMN radiation_effect_band_id SET NOT NULL,
 ALTER COLUMN effective_endurance_penalty SET NOT NULL,ALTER COLUMN radiation_unconscious SET NOT NULL;
CREATE TABLE env_radiation_exposure_attempt(
 radiation_exposure_attempt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
 actor_id bigint NOT NULL,campaign_id bigint NOT NULL,radiation_source_profile_id bigint NOT NULL REFERENCES rule_radiation_source_profile(radiation_source_profile_id),
 exposure_mode text NOT NULL CHECK(exposure_mode IN('instant','extended-hour')),damage_dice_count smallint NOT NULL CHECK(damage_dice_count BETWEEN 1 AND 12),
 rad_multiplier smallint NOT NULL CHECK(rad_multiplier IN(1,10,100)),state_version_before bigint NOT NULL,state_version_after bigint NOT NULL CHECK(state_version_after=state_version_before+1),
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),FOREIGN KEY(actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id)
);
CREATE TABLE env_radiation_exposure_die(
 radiation_exposure_attempt_id bigint NOT NULL REFERENCES env_radiation_exposure_attempt(radiation_exposure_attempt_id),die_order smallint NOT NULL CHECK(die_order>0),result smallint NOT NULL CHECK(result BETWEEN 1 AND 6),PRIMARY KEY(radiation_exposure_attempt_id,die_order)
);
CREATE TABLE env_radiation_exposure_receipt(
 radiation_exposure_attempt_id bigint PRIMARY KEY REFERENCES env_radiation_exposure_attempt(radiation_exposure_attempt_id),rolled_total smallint NOT NULL CHECK(rolled_total>0),
 rads_added integer NOT NULL CHECK(rads_added>0),rads_before integer NOT NULL CHECK(rads_before>=0),rads_after integer NOT NULL CHECK(rads_after=rads_before+rads_added),
 band_code_before text NOT NULL,band_code_after text NOT NULL,effective_endurance_before smallint NOT NULL,effective_endurance_after smallint NOT NULL,
 radiation_unconscious_before boolean NOT NULL,radiation_unconscious_after boolean NOT NULL,recorded_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE FUNCTION env_validate_radiation_attempt() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE profile rule_radiation_source_profile%ROWTYPE;state actor_radiation_state%ROWTYPE;expected_dice smallint;expected_multiplier smallint;
BEGIN SELECT * INTO STRICT profile FROM rule_radiation_source_profile WHERE radiation_source_profile_id=NEW.radiation_source_profile_id;
 SELECT * INTO state FROM actor_radiation_state WHERE actor_id=NEW.actor_id FOR UPDATE;
 expected_dice:=CASE NEW.exposure_mode WHEN 'instant' THEN profile.instant_dice_count ELSE profile.extended_dice_count END;
 expected_multiplier:=CASE NEW.exposure_mode WHEN 'instant' THEN profile.instant_multiplier ELSE profile.extended_multiplier END;
 IF expected_dice IS NULL OR NEW.damage_dice_count<>expected_dice OR NEW.rad_multiplier<>expected_multiplier OR NEW.state_version_before<>coalesce(state.concurrency_version,0)
  THEN RAISE EXCEPTION 'Radiation attempt must match source mode, dice, multiplier, and state version' USING ERRCODE='23514';END IF;RETURN NEW;END $$;
CREATE TRIGGER env_radiation_attempt_valid BEFORE INSERT ON env_radiation_exposure_attempt FOR EACH ROW EXECUTE FUNCTION env_validate_radiation_attempt();
CREATE FUNCTION env_validate_radiation_die() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE attempt env_radiation_exposure_attempt%ROWTYPE;BEGIN
 SELECT * INTO STRICT attempt FROM env_radiation_exposure_attempt WHERE radiation_exposure_attempt_id=NEW.radiation_exposure_attempt_id FOR UPDATE;
 IF EXISTS(SELECT 1 FROM env_radiation_exposure_receipt WHERE radiation_exposure_attempt_id=NEW.radiation_exposure_attempt_id) OR NEW.die_order>attempt.damage_dice_count THEN RAISE EXCEPTION 'Radiation die exceeds unresolved exposure profile' USING ERRCODE='23514';END IF;RETURN NEW;END $$;
CREATE TRIGGER env_radiation_die_valid BEFORE INSERT ON env_radiation_exposure_die FOR EACH ROW EXECUTE FUNCTION env_validate_radiation_die();
CREATE FUNCTION env_finalize_radiation_exposure() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE attempt env_radiation_exposure_attempt%ROWTYPE;state actor_radiation_state%ROWTYPE;n integer;total integer;before_rads integer;after_rads integer;
 before_band rule_radiation_effect_band%ROWTYPE;after_band rule_radiation_effect_band%ROWTYPE;endurance smallint;before_effective smallint;after_effective smallint;after_unconscious boolean;
BEGIN SELECT * INTO STRICT attempt FROM env_radiation_exposure_attempt WHERE radiation_exposure_attempt_id=NEW.radiation_exposure_attempt_id FOR UPDATE;
 SELECT * INTO state FROM actor_radiation_state WHERE actor_id=attempt.actor_id FOR UPDATE;
 SELECT count(*),sum(result) INTO n,total FROM env_radiation_exposure_die WHERE radiation_exposure_attempt_id=attempt.radiation_exposure_attempt_id;
 before_rads:=coalesce(state.total_rads,0);after_rads:=before_rads+total*attempt.rad_multiplier;
 SELECT * INTO STRICT before_band FROM rule_radiation_effect_band WHERE minimum_rads<=before_rads AND (maximum_rads IS NULL OR maximum_rads>=before_rads);
 SELECT * INTO STRICT after_band FROM rule_radiation_effect_band WHERE minimum_rads<=after_rads AND (maximum_rads IS NULL OR maximum_rads>=after_rads);
 SELECT current_value INTO STRICT endurance FROM actor_characteristic characteristic JOIN rule_rule rule ON rule.rule_id=characteristic.characteristic_rule_id WHERE characteristic.actor_id=attempt.actor_id AND rule.rule_code='characteristic.endurance';
 before_effective:=endurance-before_band.effective_endurance_penalty;after_effective:=endurance-after_band.effective_endurance_penalty;after_unconscious:=after_effective<0;
 IF n<>attempt.damage_dice_count OR NEW.rolled_total<>total OR NEW.rads_added<>total*attempt.rad_multiplier OR NEW.rads_before<>before_rads OR NEW.rads_after<>after_rads
  OR NEW.band_code_before<>before_band.band_code OR NEW.band_code_after<>after_band.band_code OR NEW.effective_endurance_before<>before_effective OR NEW.effective_endurance_after<>after_effective
  OR NEW.radiation_unconscious_before<>coalesce(state.radiation_unconscious,false) OR NEW.radiation_unconscious_after<>after_unconscious THEN
  RAISE EXCEPTION 'Radiation receipt must match complete dice, cumulative rads, effect bands, effective Endurance, and unconsciousness' USING ERRCODE='23514';END IF;
 INSERT INTO actor_radiation_state(actor_id,campaign_id,total_rads,radiation_effect_band_id,effective_endurance_penalty,radiation_unconscious,concurrency_version)
 VALUES(attempt.actor_id,attempt.campaign_id,after_rads,after_band.radiation_effect_band_id,after_band.effective_endurance_penalty,after_unconscious,attempt.state_version_after)
 ON CONFLICT(actor_id) DO UPDATE SET total_rads=EXCLUDED.total_rads,radiation_effect_band_id=EXCLUDED.radiation_effect_band_id,effective_endurance_penalty=EXCLUDED.effective_endurance_penalty,
 radiation_unconscious=EXCLUDED.radiation_unconscious,concurrency_version=EXCLUDED.concurrency_version,updated_at=clock_timestamp();RETURN NEW;END $$;
CREATE TRIGGER env_radiation_exposure_final BEFORE INSERT ON env_radiation_exposure_receipt FOR EACH ROW EXECUTE FUNCTION env_finalize_radiation_exposure();
CREATE FUNCTION env_reject_radiation_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Radiation exposure attempts, dice, and receipts are immutable';END $$;
CREATE TRIGGER env_radiation_attempt_immutable BEFORE UPDATE OR DELETE ON env_radiation_exposure_attempt FOR EACH ROW EXECUTE FUNCTION env_reject_radiation_mutation();
CREATE TRIGGER env_radiation_die_immutable BEFORE UPDATE OR DELETE ON env_radiation_exposure_die FOR EACH ROW EXECUTE FUNCTION env_reject_radiation_mutation();
CREATE TRIGGER env_radiation_receipt_immutable BEFORE UPDATE OR DELETE ON env_radiation_exposure_receipt FOR EACH ROW EXECUTE FUNCTION env_reject_radiation_mutation();
CREATE FUNCTION env_guard_radiation_state() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF pg_trigger_depth()<2 THEN RAISE EXCEPTION 'Radiation state changes require an immutable receipt' USING ERRCODE='23514';END IF;RETURN NEW;END $$;
CREATE TRIGGER actor_radiation_state_guard BEFORE INSERT OR UPDATE OR DELETE ON actor_radiation_state FOR EACH ROW EXECUTE FUNCTION env_guard_radiation_state();
