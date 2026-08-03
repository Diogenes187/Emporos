ALTER TABLE health_radiation_recovery_entitlement ALTER COLUMN recovery_kind SET DEFAULT 'physical-healing-over-time';
ALTER TABLE env_radiation_exposure_receipt
 DROP CONSTRAINT env_radiation_exposure_receipt_rads_added_check,
 ALTER COLUMN rads_added SET DEFAULT 0,
 ADD COLUMN rads_absorbed integer NOT NULL DEFAULT 0 CHECK(rads_absorbed>=0),
 ADD COLUMN gross_rads_added integer GENERATED ALWAYS AS (rads_added+rads_absorbed) STORED,
 ADD COLUMN prophylaxis_dose_receipt_id bigint REFERENCES env_antiradiation_dose_receipt(antiradiation_dose_receipt_id),
 ADD CONSTRAINT env_radiation_net_rads CHECK(rads_added>=0 AND gross_rads_added>0),
 ADD CONSTRAINT env_radiation_absorption_source CHECK((rads_absorbed>0)=(prophylaxis_dose_receipt_id IS NOT NULL));
CREATE OR REPLACE FUNCTION env_finalize_radiation_exposure() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE attempt env_radiation_exposure_attempt%ROWTYPE;state actor_radiation_state%ROWTYPE;prophylaxis actor_antiradiation_prophylaxis%ROWTYPE;n integer;total integer;gross integer;absorbed integer;before_rads integer;after_rads integer;
 before_band rule_radiation_effect_band%ROWTYPE;after_band rule_radiation_effect_band%ROWTYPE;endurance smallint;before_effective smallint;after_effective smallint;after_unconscious boolean;
BEGIN SELECT * INTO STRICT attempt FROM env_radiation_exposure_attempt WHERE radiation_exposure_attempt_id=NEW.radiation_exposure_attempt_id FOR UPDATE;
 SELECT * INTO state FROM actor_radiation_state WHERE actor_id=attempt.actor_id FOR UPDATE;
 SELECT * INTO prophylaxis FROM actor_antiradiation_prophylaxis WHERE actor_id=attempt.actor_id FOR UPDATE;
 SELECT count(*),sum(result) INTO n,total FROM env_radiation_exposure_die WHERE radiation_exposure_attempt_id=attempt.radiation_exposure_attempt_id;
 gross:=total*attempt.rad_multiplier;absorbed:=least(gross,coalesce(prophylaxis.remaining_absorption_rads,0));before_rads:=coalesce(state.total_rads,0);after_rads:=before_rads+gross-absorbed;
 SELECT * INTO STRICT before_band FROM rule_radiation_effect_band WHERE minimum_rads<=before_rads AND (maximum_rads IS NULL OR maximum_rads>=before_rads);
 SELECT * INTO STRICT after_band FROM rule_radiation_effect_band WHERE minimum_rads<=after_rads AND (maximum_rads IS NULL OR maximum_rads>=after_rads);
 SELECT current_value INTO STRICT endurance FROM actor_characteristic characteristic JOIN rule_rule rule ON rule.rule_id=characteristic.characteristic_rule_id WHERE characteristic.actor_id=attempt.actor_id AND rule.rule_code='characteristic.endurance';
 before_effective:=endurance-before_band.effective_endurance_penalty;after_effective:=endurance-after_band.effective_endurance_penalty;after_unconscious:=after_effective<0;
 IF n<>attempt.damage_dice_count OR NEW.rolled_total<>total OR NEW.gross_rads_added<>gross OR NEW.rads_absorbed<>absorbed OR NEW.rads_added<>gross-absorbed OR NEW.rads_before<>before_rads OR NEW.rads_after<>after_rads
  OR NEW.prophylaxis_dose_receipt_id IS DISTINCT FROM prophylaxis.antiradiation_dose_receipt_id OR NEW.band_code_before<>before_band.band_code OR NEW.band_code_after<>after_band.band_code
  OR NEW.effective_endurance_before<>before_effective OR NEW.effective_endurance_after<>after_effective OR NEW.radiation_unconscious_before<>coalesce(state.radiation_unconscious,false)
  OR NEW.radiation_unconscious_after<>after_unconscious THEN RAISE EXCEPTION 'Radiation receipt must match dice, prophylactic absorption, net cumulative rads, bands, effective Endurance, and unconsciousness' USING ERRCODE='23514';END IF;
 INSERT INTO actor_radiation_state(actor_id,campaign_id,total_rads,radiation_effect_band_id,effective_endurance_penalty,radiation_unconscious,concurrency_version)
 VALUES(attempt.actor_id,attempt.campaign_id,after_rads,after_band.radiation_effect_band_id,after_band.effective_endurance_penalty,after_unconscious,attempt.state_version_after)
 ON CONFLICT(actor_id) DO UPDATE SET total_rads=EXCLUDED.total_rads,radiation_effect_band_id=EXCLUDED.radiation_effect_band_id,effective_endurance_penalty=EXCLUDED.effective_endurance_penalty,radiation_unconscious=EXCLUDED.radiation_unconscious,concurrency_version=EXCLUDED.concurrency_version,updated_at=clock_timestamp();
 IF absorbed>0 THEN IF absorbed=prophylaxis.remaining_absorption_rads THEN DELETE FROM actor_antiradiation_prophylaxis WHERE actor_id=attempt.actor_id;ELSE UPDATE actor_antiradiation_prophylaxis SET remaining_absorption_rads=remaining_absorption_rads-absorbed,concurrency_version=concurrency_version+1 WHERE actor_id=attempt.actor_id;END IF;END IF;RETURN NEW;END $$;
