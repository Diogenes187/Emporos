ALTER TABLE health_damage_instance
 ADD COLUMN crew_damage_location_hit_receipt_id bigint,
 ADD COLUMN crew_damage_target_order smallint,
 ADD CONSTRAINT health_damage_crew_consequence_fk FOREIGN KEY(crew_damage_location_hit_receipt_id,crew_damage_target_order)
  REFERENCES senc_crew_damage_consequence_receipt(damage_location_hit_receipt_id,target_order),
 ADD CONSTRAINT health_damage_crew_consequence_unique UNIQUE(crew_damage_location_hit_receipt_id,crew_damage_target_order),
 ADD CONSTRAINT health_damage_crew_source_pair CHECK((crew_damage_location_hit_receipt_id IS NULL)=(crew_damage_target_order IS NULL));
ALTER TABLE health_damage_instance DROP CONSTRAINT health_damage_exactly_one_source_check,
 ADD CONSTRAINT health_damage_exactly_one_source_check CHECK(
  num_nonnulls(attack_command_id,environmental_command_id,explosion_command_id,grapple_option_command_id)
  + CASE WHEN crew_damage_location_hit_receipt_id IS NULL THEN 0 ELSE 1 END=1
 );

CREATE TABLE actor_radiation_state(
 actor_id bigint PRIMARY KEY REFERENCES actor_actor(actor_id),campaign_id bigint NOT NULL,total_rads integer NOT NULL DEFAULT 0 CHECK(total_rads>=0),
 concurrency_version bigint NOT NULL DEFAULT 1 CHECK(concurrency_version>0),updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id)
);
CREATE TABLE health_radiation_exposure(
 radiation_exposure_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,damage_location_hit_receipt_id bigint NOT NULL,target_order smallint NOT NULL,
 actor_id bigint NOT NULL,campaign_id bigint NOT NULL,rads_added integer NOT NULL CHECK(rads_added>0),rads_before integer NOT NULL CHECK(rads_before>=0),
 rads_after integer NOT NULL CHECK(rads_after=rads_before+rads_added),actor_radiation_version_before bigint NOT NULL,
 actor_radiation_version_after bigint NOT NULL CHECK(actor_radiation_version_after=actor_radiation_version_before+1),recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(damage_location_hit_receipt_id,target_order),FOREIGN KEY(damage_location_hit_receipt_id,target_order)
 REFERENCES senc_crew_damage_consequence_receipt(damage_location_hit_receipt_id,target_order),FOREIGN KEY(actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id)
);
CREATE TABLE senc_crew_damage_application_receipt(
 damage_location_hit_receipt_id bigint NOT NULL,target_order smallint NOT NULL,actor_id bigint NOT NULL,
 damage_instance_id bigint UNIQUE REFERENCES health_damage_instance(damage_instance_id),radiation_exposure_id bigint UNIQUE REFERENCES health_radiation_exposure(radiation_exposure_id),
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),PRIMARY KEY(damage_location_hit_receipt_id,target_order),
 FOREIGN KEY(damage_location_hit_receipt_id,target_order) REFERENCES senc_crew_damage_consequence_receipt(damage_location_hit_receipt_id,target_order),
 CHECK(num_nonnulls(damage_instance_id,radiation_exposure_id)=1)
);

CREATE FUNCTION senc_apply_crew_damage_consequence() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE attempt senc_crew_damage_attempt%ROWTYPE; state actor_radiation_state%ROWTYPE; damage_id bigint; exposure_id bigint;
BEGIN SELECT * INTO STRICT attempt FROM senc_crew_damage_attempt WHERE damage_location_hit_receipt_id=NEW.damage_location_hit_receipt_id;
 IF NEW.normal_damage>0 THEN
  INSERT INTO health_damage_instance(target_actor_id,penetrating_damage,crew_damage_location_hit_receipt_id,crew_damage_target_order)
  VALUES(NEW.actor_id,NEW.normal_damage,NEW.damage_location_hit_receipt_id,NEW.target_order) RETURNING damage_instance_id INTO damage_id;
  INSERT INTO senc_crew_damage_application_receipt(damage_location_hit_receipt_id,target_order,actor_id,damage_instance_id)
  VALUES(NEW.damage_location_hit_receipt_id,NEW.target_order,NEW.actor_id,damage_id);
 ELSE
  INSERT INTO actor_radiation_state(actor_id,campaign_id) VALUES(NEW.actor_id,attempt.campaign_id) ON CONFLICT(actor_id) DO NOTHING;
  SELECT * INTO STRICT state FROM actor_radiation_state WHERE actor_id=NEW.actor_id FOR UPDATE;
  UPDATE actor_radiation_state SET total_rads=state.total_rads+NEW.radiation_rads,concurrency_version=state.concurrency_version+1,updated_at=clock_timestamp()
  WHERE actor_id=NEW.actor_id;
  INSERT INTO health_radiation_exposure(damage_location_hit_receipt_id,target_order,actor_id,campaign_id,rads_added,rads_before,rads_after,
   actor_radiation_version_before,actor_radiation_version_after)
  VALUES(NEW.damage_location_hit_receipt_id,NEW.target_order,NEW.actor_id,attempt.campaign_id,NEW.radiation_rads,state.total_rads,
   state.total_rads+NEW.radiation_rads,state.concurrency_version,state.concurrency_version+1) RETURNING radiation_exposure_id INTO exposure_id;
  INSERT INTO senc_crew_damage_application_receipt(damage_location_hit_receipt_id,target_order,actor_id,radiation_exposure_id)
  VALUES(NEW.damage_location_hit_receipt_id,NEW.target_order,NEW.actor_id,exposure_id);
 END IF; RETURN NEW;
END $$;
CREATE TRIGGER senc_crew_damage_consequence_apply AFTER INSERT ON senc_crew_damage_consequence_receipt
FOR EACH ROW EXECUTE FUNCTION senc_apply_crew_damage_consequence();
CREATE FUNCTION senc_reject_crew_damage_application_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Crew damage application and radiation history are immutable'; END $$;
CREATE TRIGGER health_radiation_exposure_immutable BEFORE UPDATE OR DELETE ON health_radiation_exposure FOR EACH ROW EXECUTE FUNCTION senc_reject_crew_damage_application_mutation();
CREATE TRIGGER senc_crew_damage_application_immutable BEFORE UPDATE OR DELETE ON senc_crew_damage_application_receipt FOR EACH ROW EXECUTE FUNCTION senc_reject_crew_damage_application_mutation();
