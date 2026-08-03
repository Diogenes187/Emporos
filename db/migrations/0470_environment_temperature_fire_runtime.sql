CREATE TABLE env_temperature_exposure(
 temperature_exposure_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
 actor_id bigint NOT NULL,campaign_id bigint NOT NULL,temperature_band_id bigint NOT NULL REFERENCES rule_extreme_temperature_band(temperature_band_id),
 suitably_protected boolean NOT NULL,exposure_status text NOT NULL DEFAULT 'active' CHECK(exposure_status IN('active','ended')),
 concurrency_version bigint NOT NULL DEFAULT 1 CHECK(concurrency_version>0),started_at timestamptz NOT NULL DEFAULT clock_timestamp(),ended_at timestamptz,
 FOREIGN KEY(actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id),CHECK((exposure_status='active')=(ended_at IS NULL))
);
CREATE TABLE env_temperature_damage_receipt(
 temperature_damage_receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,temperature_exposure_id bigint NOT NULL REFERENCES env_temperature_exposure(temperature_exposure_id),
 exposure_tick integer NOT NULL CHECK(exposure_tick>0),damage_interval text CHECK(damage_interval IN('round','hour')),damage_dice_count smallint NOT NULL CHECK(damage_dice_count BETWEEN 0 AND 3),
 die_1 smallint CHECK(die_1 BETWEEN 1 AND 6),die_2 smallint CHECK(die_2 BETWEEN 1 AND 6),die_3 smallint CHECK(die_3 BETWEEN 1 AND 6),
 rolled_damage smallint NOT NULL CHECK(rolled_damage>=0),damage_instance_id bigint UNIQUE,recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(temperature_exposure_id,exposure_tick),CHECK(num_nonnulls(die_1,die_2,die_3)=damage_dice_count)
);
CREATE TABLE env_fire_episode(
 fire_episode_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,actor_id bigint NOT NULL,campaign_id bigint NOT NULL,
 fire_status text NOT NULL DEFAULT 'at-risk' CHECK(fire_status IN('at-risk','burning','extinguished','avoided')),current_round integer NOT NULL DEFAULT 0 CHECK(current_round>=0),
 concurrency_version bigint NOT NULL DEFAULT 1 CHECK(concurrency_version>0),started_at timestamptz NOT NULL DEFAULT clock_timestamp(),ended_at timestamptz,
 FOREIGN KEY(actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id),CHECK((fire_status IN('at-risk','burning'))=(ended_at IS NULL))
);
CREATE UNIQUE INDEX env_one_active_fire_episode ON env_fire_episode(actor_id) WHERE fire_status IN('at-risk','burning');
CREATE TABLE env_fire_resolution_receipt(
 fire_resolution_receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,fire_episode_id bigint NOT NULL REFERENCES env_fire_episode(fire_episode_id),
 resolution_sequence integer NOT NULL CHECK(resolution_sequence>0),resolution_kind text NOT NULL CHECK(resolution_kind IN('ignition-check','burning-round-check','automatic-extinguish')),
 task_command_id bigint UNIQUE REFERENCES cmd_actor_task_receipt(command_id),automatic_method text CHECK(automatic_method IN('water','fire-extinguisher','vent-atmosphere','smother-other')),
 improvised_smothering boolean NOT NULL DEFAULT false,task_succeeded boolean,die_1 smallint CHECK(die_1 BETWEEN 1 AND 6),die_2 smallint CHECK(die_2 BETWEEN 1 AND 6),
 rolled_damage smallint NOT NULL CHECK(rolled_damage IN(0,2,3,4,5,6,7,8,9,10,11,12)),damage_instance_id bigint UNIQUE,
 fire_status_after text NOT NULL CHECK(fire_status_after IN('burning','extinguished','avoided')),state_version_before bigint NOT NULL,state_version_after bigint NOT NULL,
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),UNIQUE(fire_episode_id,resolution_sequence),CHECK(state_version_after=state_version_before+1),
 CHECK((resolution_kind='automatic-extinguish')=(task_command_id IS NULL)),CHECK((resolution_kind='automatic-extinguish')=(automatic_method IS NOT NULL)),
 CHECK((rolled_damage=0)=(die_1 IS NULL AND die_2 IS NULL)),CHECK((rolled_damage>0)=(die_1 IS NOT NULL AND die_2 IS NOT NULL))
);

ALTER TABLE health_damage_instance ADD COLUMN temperature_damage_receipt_id bigint UNIQUE,
 ADD COLUMN fire_resolution_receipt_id bigint UNIQUE,
 ADD CONSTRAINT health_temperature_damage_receipt_fk FOREIGN KEY(temperature_damage_receipt_id) REFERENCES env_temperature_damage_receipt(temperature_damage_receipt_id) DEFERRABLE INITIALLY DEFERRED,
 ADD CONSTRAINT health_fire_resolution_receipt_fk FOREIGN KEY(fire_resolution_receipt_id) REFERENCES env_fire_resolution_receipt(fire_resolution_receipt_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE health_damage_instance DROP CONSTRAINT health_damage_exactly_one_source_check,
 ADD CONSTRAINT health_damage_exactly_one_source_check CHECK(
 num_nonnulls(attack_command_id,environmental_command_id,explosion_command_id,grapple_option_command_id,personal_scale_attack_receipt_id,acid_damage_attempt_id,acid_fume_task_command_id,temperature_damage_receipt_id,fire_resolution_receipt_id)
 +CASE WHEN crew_damage_location_hit_receipt_id IS NULL THEN 0 ELSE 1 END+CASE WHEN missile_crew_hit_receipt_id IS NULL THEN 0 ELSE 1 END=1);
ALTER TABLE env_temperature_damage_receipt ADD CONSTRAINT env_temperature_damage_instance_fk FOREIGN KEY(damage_instance_id) REFERENCES health_damage_instance(damage_instance_id);
ALTER TABLE env_fire_resolution_receipt ADD CONSTRAINT env_fire_damage_instance_fk FOREIGN KEY(damage_instance_id) REFERENCES health_damage_instance(damage_instance_id);

CREATE FUNCTION env_finalize_temperature_damage() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE exposure env_temperature_exposure%ROWTYPE;band rule_extreme_temperature_band%ROWTYPE;expected integer;damage_id bigint;
BEGIN SELECT * INTO STRICT exposure FROM env_temperature_exposure WHERE temperature_exposure_id=NEW.temperature_exposure_id FOR UPDATE;
 SELECT * INTO STRICT band FROM rule_extreme_temperature_band WHERE temperature_band_id=exposure.temperature_band_id;
 expected:=CASE WHEN exposure.suitably_protected THEN 0 ELSE band.damage_dice_count END;
 IF exposure.exposure_status<>'active' OR NEW.exposure_tick<>(SELECT count(*)+1 FROM env_temperature_damage_receipt WHERE temperature_exposure_id=exposure.temperature_exposure_id)
  OR NEW.damage_dice_count<>expected OR NEW.damage_interval IS DISTINCT FROM (CASE WHEN expected=0 THEN NULL ELSE band.damage_interval END)
  OR NEW.rolled_damage<>coalesce(NEW.die_1,0)+coalesce(NEW.die_2,0)+coalesce(NEW.die_3,0) THEN
  RAISE EXCEPTION 'Temperature damage receipt must match active exposure, protection, cadence, dice, and exact total' USING ERRCODE='23514'; END IF;
 IF NEW.rolled_damage>0 THEN INSERT INTO health_damage_instance(target_actor_id,penetrating_damage,temperature_damage_receipt_id)
  VALUES(exposure.actor_id,NEW.rolled_damage,NEW.temperature_damage_receipt_id) RETURNING damage_instance_id INTO damage_id; NEW.damage_instance_id:=damage_id; END IF;
 RETURN NEW; END $$;
CREATE TRIGGER env_temperature_damage_final BEFORE INSERT ON env_temperature_damage_receipt FOR EACH ROW EXECUTE FUNCTION env_finalize_temperature_damage();

CREATE FUNCTION env_finalize_fire_resolution() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE episode env_fire_episode%ROWTYPE;task cmd_actor_task_receipt%ROWTYPE;fire rule_catching_fire%ROWTYPE;expected_kind text;expected_status text;expected_damage integer;damage_id bigint;
BEGIN SELECT * INTO STRICT episode FROM env_fire_episode WHERE fire_episode_id=NEW.fire_episode_id FOR UPDATE;
 SELECT profile.* INTO STRICT fire FROM rule_catching_fire profile JOIN rule_rule rule ON rule.rule_id=profile.rule_id WHERE rule.rule_code='environment.catching-fire';
 expected_kind:=CASE episode.fire_status WHEN 'at-risk' THEN 'ignition-check' WHEN 'burning' THEN NEW.resolution_kind END;
 IF NEW.resolution_sequence<>(SELECT count(*)+1 FROM env_fire_resolution_receipt WHERE fire_episode_id=episode.fire_episode_id) OR NEW.state_version_before<>episode.concurrency_version
  OR NEW.resolution_kind<>expected_kind OR episode.fire_status NOT IN('at-risk','burning') THEN RAISE EXCEPTION 'Fire receipt must match active episode, sequence, and version' USING ERRCODE='23514'; END IF;
 IF NEW.resolution_kind='automatic-extinguish' THEN expected_status:='extinguished';expected_damage:=0;
 ELSE SELECT * INTO STRICT task FROM cmd_actor_task_receipt WHERE command_id=NEW.task_command_id;
  IF task.actor_id<>episode.actor_id OR task.characteristic_rule_id<>fire.check_characteristic_rule_id OR task.skill_rule_id IS NOT NULL OR task.difficulty_rule_id<>fire.difficulty_rule_id
   OR task.circumstance_modifier<>(CASE WHEN NEW.improvised_smothering THEN fire.improvised_smothering_dm ELSE 0 END) OR NEW.task_succeeded<>task.succeeded THEN
   RAISE EXCEPTION 'Fire check must be the published Difficult Dexterity check with only the smothering DM' USING ERRCODE='23514'; END IF;
  expected_status:=CASE WHEN NEW.task_succeeded THEN CASE NEW.resolution_kind WHEN 'ignition-check' THEN 'avoided' ELSE 'extinguished' END ELSE 'burning' END;
  expected_damage:=CASE WHEN NEW.task_succeeded THEN 0 ELSE 2 END;
 END IF;
 IF NEW.fire_status_after<>expected_status OR num_nonnulls(NEW.die_1,NEW.die_2)<>expected_damage OR NEW.rolled_damage<>coalesce(NEW.die_1,0)+coalesce(NEW.die_2,0) THEN
  RAISE EXCEPTION 'Fire outcome must match check result and exact 2D6 damage' USING ERRCODE='23514'; END IF;
 IF NEW.rolled_damage>0 THEN INSERT INTO health_damage_instance(target_actor_id,penetrating_damage,fire_resolution_receipt_id)
  VALUES(episode.actor_id,NEW.rolled_damage,NEW.fire_resolution_receipt_id) RETURNING damage_instance_id INTO damage_id; NEW.damage_instance_id:=damage_id; END IF;
 UPDATE env_fire_episode SET fire_status=expected_status,current_round=CASE WHEN expected_status='burning' THEN current_round+1 ELSE current_round END,
  concurrency_version=NEW.state_version_after,ended_at=CASE WHEN expected_status IN('avoided','extinguished') THEN clock_timestamp() END WHERE fire_episode_id=episode.fire_episode_id;
 RETURN NEW; END $$;
CREATE TRIGGER env_fire_resolution_final BEFORE INSERT ON env_fire_resolution_receipt FOR EACH ROW EXECUTE FUNCTION env_finalize_fire_resolution();

CREATE FUNCTION env_reject_temperature_fire_receipt_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Temperature and fire receipts are immutable'; END $$;
CREATE TRIGGER env_temperature_damage_immutable BEFORE UPDATE OR DELETE ON env_temperature_damage_receipt FOR EACH ROW EXECUTE FUNCTION env_reject_temperature_fire_receipt_mutation();
CREATE TRIGGER env_fire_resolution_immutable BEFORE UPDATE OR DELETE ON env_fire_resolution_receipt FOR EACH ROW EXECUTE FUNCTION env_reject_temperature_fire_receipt_mutation();
CREATE FUNCTION env_guard_fire_episode() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF pg_trigger_depth()<2 THEN RAISE EXCEPTION 'Fire episode changes require an immutable receipt' USING ERRCODE='23514'; END IF;RETURN NEW;END $$;
CREATE TRIGGER env_fire_episode_guard BEFORE UPDATE OR DELETE ON env_fire_episode FOR EACH ROW EXECUTE FUNCTION env_guard_fire_episode();
