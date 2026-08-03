CREATE TABLE env_poison_attempt(
 poison_attempt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
 actor_id bigint NOT NULL,campaign_id bigint NOT NULL,poison_profile_id bigint NOT NULL REFERENCES rule_poison_profile(poison_profile_id),
 exposure_reference text NOT NULL CHECK(btrim(exposure_reference)<>''),recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id)
);
CREATE TABLE actor_poison_unconscious_state(
 actor_id bigint PRIMARY KEY,campaign_id bigint NOT NULL,poison_attempt_id bigint NOT NULL UNIQUE REFERENCES env_poison_attempt(poison_attempt_id),
 unconscious boolean NOT NULL CHECK(unconscious),concurrency_version bigint NOT NULL CHECK(concurrency_version>0),started_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id)
);
CREATE TABLE env_poison_resolution_receipt(
 poison_attempt_id bigint PRIMARY KEY REFERENCES env_poison_attempt(poison_attempt_id),task_command_id bigint NOT NULL UNIQUE REFERENCES cmd_actor_task_receipt(command_id),
 dm_die_result smallint CHECK(dm_die_result BETWEEN 1 AND 6),effective_resistance_dm smallint NOT NULL,task_succeeded boolean NOT NULL,
 damage_die_1 smallint CHECK(damage_die_1 BETWEEN 1 AND 6),damage_die_2 smallint CHECK(damage_die_2 BETWEEN 1 AND 6),rolled_damage smallint NOT NULL CHECK(rolled_damage>=0),
 affected_characteristic_rule_id bigint REFERENCES rule_characteristic(rule_id),characteristic_value_before smallint,characteristic_value_after smallint,
 became_unconscious boolean NOT NULL,damage_instance_id bigint UNIQUE,recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 CHECK((characteristic_value_before IS NULL)=(affected_characteristic_rule_id IS NULL)),CHECK((characteristic_value_after IS NULL)=(affected_characteristic_rule_id IS NULL)),
 CHECK(characteristic_value_before IS NULL OR characteristic_value_after<=characteristic_value_before)
);
ALTER TABLE health_damage_instance ADD COLUMN poison_attempt_id bigint UNIQUE REFERENCES env_poison_attempt(poison_attempt_id);
ALTER TABLE health_damage_instance DROP CONSTRAINT health_damage_exactly_one_source_check,
 ADD CONSTRAINT health_damage_exactly_one_source_check CHECK(
 num_nonnulls(attack_command_id,environmental_command_id,explosion_command_id,grapple_option_command_id,personal_scale_attack_receipt_id,acid_damage_attempt_id,acid_fume_task_command_id,temperature_damage_receipt_id,fire_resolution_receipt_id,fall_attempt_id,poison_attempt_id)
 +CASE WHEN crew_damage_location_hit_receipt_id IS NULL THEN 0 ELSE 1 END+CASE WHEN missile_crew_hit_receipt_id IS NULL THEN 0 ELSE 1 END=1);
ALTER TABLE env_poison_resolution_receipt ADD CONSTRAINT env_poison_damage_instance_fk FOREIGN KEY(damage_instance_id) REFERENCES health_damage_instance(damage_instance_id);

CREATE FUNCTION env_finalize_poison_resolution() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE attempt env_poison_attempt%ROWTYPE;profile rule_poison_profile%ROWTYPE;task cmd_actor_task_receipt%ROWTYPE;average_id bigint;
 characteristic actor_characteristic%ROWTYPE;expected_dm smallint;expected_dice smallint;expected_damage integer;damage_id bigint;
BEGIN
 SELECT * INTO STRICT attempt FROM env_poison_attempt WHERE poison_attempt_id=NEW.poison_attempt_id FOR UPDATE;
 SELECT * INTO STRICT profile FROM rule_poison_profile WHERE poison_profile_id=attempt.poison_profile_id;
 SELECT * INTO STRICT task FROM cmd_actor_task_receipt WHERE command_id=NEW.task_command_id;
 SELECT rule_id INTO STRICT average_id FROM rule_rule WHERE rule_code='difficulty.average';
 expected_dm:=CASE profile.dm_kind WHEN 'fixed' THEN profile.fixed_dm ELSE -NEW.dm_die_result END;
 IF (profile.dm_kind='fixed' AND NEW.dm_die_result IS NOT NULL) OR (profile.dm_kind='negative-die' AND NEW.dm_die_result IS NULL)
  OR NEW.effective_resistance_dm<>expected_dm OR task.actor_id<>attempt.actor_id OR task.characteristic_rule_id<>profile.resistance_characteristic_rule_id
  OR task.skill_rule_id IS NOT NULL OR task.difficulty_rule_id<>average_id OR task.circumstance_modifier<>expected_dm OR NEW.task_succeeded<>task.succeeded THEN
  RAISE EXCEPTION 'Poison resolution must match its actor, Average Endurance check, and fixed or rolled resistance DM' USING ERRCODE='23514';END IF;
 expected_dice:=CASE WHEN NEW.task_succeeded THEN 0 ELSE profile.damage_dice_count END;
 expected_damage:=coalesce(NEW.damage_die_1,0)+coalesce(NEW.damage_die_2,0);
 IF num_nonnulls(NEW.damage_die_1,NEW.damage_die_2)<>expected_dice OR NEW.rolled_damage<>expected_damage
  OR NEW.became_unconscious<>(NOT NEW.task_succeeded AND profile.outcome_kind='unconsciousness') THEN
  RAISE EXCEPTION 'Poison outcome must match success, published effect, complete dice, and exact total' USING ERRCODE='23514';END IF;
 IF profile.outcome_kind='characteristic-damage' AND NOT NEW.task_succeeded THEN
  SELECT * INTO STRICT characteristic FROM actor_characteristic WHERE actor_id=attempt.actor_id AND characteristic_rule_id=profile.affected_characteristic_rule_id FOR UPDATE;
  IF NEW.affected_characteristic_rule_id<>profile.affected_characteristic_rule_id OR NEW.characteristic_value_before<>characteristic.current_value
   OR NEW.characteristic_value_after<>greatest(0,characteristic.current_value-expected_damage) THEN RAISE EXCEPTION 'Neurotoxin must apply exact rolled damage to its published characteristic' USING ERRCODE='23514';END IF;
  UPDATE actor_characteristic SET current_value=NEW.characteristic_value_after WHERE actor_id=attempt.actor_id AND characteristic_rule_id=profile.affected_characteristic_rule_id;
 ELSIF NEW.affected_characteristic_rule_id IS NOT NULL THEN RAISE EXCEPTION 'Only characteristic-damage poison failures may record characteristic state' USING ERRCODE='23514';END IF;
 IF profile.outcome_kind='physical-damage' AND NOT NEW.task_succeeded AND expected_damage>0 THEN
  INSERT INTO health_damage_instance(target_actor_id,penetrating_damage,poison_attempt_id) VALUES(attempt.actor_id,expected_damage,attempt.poison_attempt_id) RETURNING damage_instance_id INTO damage_id;NEW.damage_instance_id:=damage_id;
 END IF;
 IF NEW.became_unconscious THEN INSERT INTO actor_poison_unconscious_state(actor_id,campaign_id,poison_attempt_id,unconscious,concurrency_version)
  VALUES(attempt.actor_id,attempt.campaign_id,attempt.poison_attempt_id,true,1);END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER env_poison_resolution_final BEFORE INSERT ON env_poison_resolution_receipt FOR EACH ROW EXECUTE FUNCTION env_finalize_poison_resolution();
CREATE FUNCTION env_reject_poison_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Poison attempts and resolution receipts are immutable';END $$;
CREATE TRIGGER env_poison_attempt_immutable BEFORE UPDATE OR DELETE ON env_poison_attempt FOR EACH ROW EXECUTE FUNCTION env_reject_poison_mutation();
CREATE TRIGGER env_poison_resolution_immutable BEFORE UPDATE OR DELETE ON env_poison_resolution_receipt FOR EACH ROW EXECUTE FUNCTION env_reject_poison_mutation();
CREATE FUNCTION env_guard_poison_unconscious_state() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF pg_trigger_depth()<2 THEN RAISE EXCEPTION 'Poison unconscious state changes require an immutable receipt' USING ERRCODE='23514';END IF;RETURN NEW;END $$;
CREATE TRIGGER actor_poison_unconscious_guard BEFORE INSERT OR UPDATE OR DELETE ON actor_poison_unconscious_state FOR EACH ROW EXECUTE FUNCTION env_guard_poison_unconscious_state();
