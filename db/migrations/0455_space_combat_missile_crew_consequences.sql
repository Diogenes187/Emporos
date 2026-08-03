CREATE TABLE senc_missile_crew_hit_receipt(
 missile_crew_hit_receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 missile_damage_location_hit_receipt_id bigint UNIQUE REFERENCES senc_missile_damage_location_hit_receipt(missile_damage_location_hit_receipt_id),
 nuclear_missile_impact_attempt_id bigint,nuclear_missile_order smallint,
 target_ship_id bigint NOT NULL,campaign_id bigint NOT NULL,damage_kind text NOT NULL CHECK(damage_kind IN('normal','radiation')),
 active_crew_count smallint NOT NULL CHECK(active_crew_count>0),die_one smallint NOT NULL CHECK(die_one BETWEEN 1 AND 6),die_two smallint NOT NULL CHECK(die_two BETWEEN 1 AND 6),
 armor_dm smallint NOT NULL CHECK(armor_dm<=0),unmodified_roll smallint NOT NULL CHECK(unmodified_roll=die_one+die_two),modified_roll smallint NOT NULL CHECK(modified_roll=unmodified_roll+armor_dm),
 target_scope text NOT NULL CHECK(target_scope IN('none','one-random','all')),damage_dice_count smallint NOT NULL CHECK(damage_dice_count IN(0,2,4)),
 damage_die_sides smallint,radiation_multiplier_rads smallint,outcome_code text NOT NULL,recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(target_ship_id,campaign_id) REFERENCES ship_ship(ship_id,campaign_id),
 FOREIGN KEY(nuclear_missile_impact_attempt_id,nuclear_missile_order) REFERENCES senc_nuclear_missile_radiation_hit_receipt(missile_impact_attempt_id,missile_order),
 CHECK(num_nonnulls(missile_damage_location_hit_receipt_id,nuclear_missile_impact_attempt_id)=1),
 CHECK((nuclear_missile_impact_attempt_id IS NULL)=(nuclear_missile_order IS NULL)),CHECK((damage_dice_count=0)=(damage_die_sides IS NULL)),
 CHECK((damage_kind='radiation')=(radiation_multiplier_rads=10)),UNIQUE(nuclear_missile_impact_attempt_id,nuclear_missile_order));

CREATE FUNCTION senc_validate_missile_crew_hit() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE origin record;crew_count integer;expected record;bounded integer;
BEGIN
 IF NEW.missile_damage_location_hit_receipt_id IS NOT NULL THEN
  SELECT target_ship_id,campaign_id,'normal'::text AS kind,0::smallint AS armor_dm INTO STRICT origin FROM senc_missile_damage_location_hit_receipt
  WHERE missile_damage_location_hit_receipt_id=NEW.missile_damage_location_hit_receipt_id AND effect_code='roll-crew-damage';
 ELSE
  SELECT target_ship_id,campaign_id,'radiation'::text AS kind,armor_dm,die_one,die_two,unmodified_roll,modified_roll,target_scope,damage_dice_count,outcome_code INTO STRICT origin
  FROM senc_nuclear_missile_radiation_hit_receipt WHERE missile_impact_attempt_id=NEW.nuclear_missile_impact_attempt_id AND missile_order=NEW.nuclear_missile_order;
 END IF;
 SELECT count(*) INTO crew_count FROM ship_crew_assignment WHERE ship_id=origin.target_ship_id AND campaign_id=origin.campaign_id AND duty_status='active';
 bounded:=greatest(2,least(12,NEW.modified_roll));
 SELECT band.* INTO STRICT expected FROM rule_space_combat_crew_damage_band band JOIN rule_rule r ON r.rule_id=band.hit_location_rule_id
 WHERE r.rule_code='combat.space.hit-locations' AND band.damage_kind=origin.kind AND band.roll_range @> bounded;
 IF NEW.target_ship_id<>origin.target_ship_id OR NEW.campaign_id<>origin.campaign_id OR NEW.damage_kind<>origin.kind OR NEW.active_crew_count<>crew_count OR crew_count=0
  OR NEW.armor_dm<>origin.armor_dm OR (NEW.nuclear_missile_impact_attempt_id IS NOT NULL AND (NEW.die_one<>origin.die_one OR NEW.die_two<>origin.die_two OR NEW.unmodified_roll<>origin.unmodified_roll OR NEW.modified_roll<>origin.modified_roll))
  OR NEW.target_scope<>expected.target_scope OR NEW.damage_dice_count<>expected.damage_dice_count OR NEW.damage_die_sides IS DISTINCT FROM expected.damage_die_sides
  OR NEW.radiation_multiplier_rads IS DISTINCT FROM expected.radiation_multiplier_rads OR NEW.outcome_code<>expected.outcome_code
 THEN RAISE EXCEPTION 'Missile crew hit must match its source, active crew snapshot, dice, armor DM, and published outcome band' USING ERRCODE='23514';END IF;RETURN NEW;END $$;
CREATE TRIGGER senc_missile_crew_hit_valid BEFORE INSERT ON senc_missile_crew_hit_receipt FOR EACH ROW EXECUTE FUNCTION senc_validate_missile_crew_hit();

CREATE TABLE senc_missile_crew_population(
 missile_crew_hit_receipt_id bigint NOT NULL REFERENCES senc_missile_crew_hit_receipt(missile_crew_hit_receipt_id),population_ordinal smallint NOT NULL CHECK(population_ordinal>0),
 crew_assignment_id bigint NOT NULL,actor_id bigint NOT NULL,campaign_id bigint NOT NULL,PRIMARY KEY(missile_crew_hit_receipt_id,population_ordinal),
 UNIQUE(missile_crew_hit_receipt_id,crew_assignment_id),UNIQUE(missile_crew_hit_receipt_id,actor_id),FOREIGN KEY(actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id));
CREATE TABLE senc_missile_crew_population_receipt(missile_crew_hit_receipt_id bigint PRIMARY KEY REFERENCES senc_missile_crew_hit_receipt(missile_crew_hit_receipt_id),population_count smallint NOT NULL CHECK(population_count>0),recorded_at timestamptz NOT NULL DEFAULT clock_timestamp());
CREATE FUNCTION senc_validate_missile_crew_population() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE h senc_missile_crew_hit_receipt%ROWTYPE;a record;BEGIN
 SELECT * INTO STRICT h FROM senc_missile_crew_hit_receipt WHERE missile_crew_hit_receipt_id=NEW.missile_crew_hit_receipt_id FOR UPDATE;
 SELECT actor_id,campaign_id,ship_id,duty_status INTO STRICT a FROM ship_crew_assignment WHERE crew_assignment_id=NEW.crew_assignment_id;
 IF EXISTS(SELECT 1 FROM senc_missile_crew_population_receipt WHERE missile_crew_hit_receipt_id=NEW.missile_crew_hit_receipt_id) OR a.actor_id<>NEW.actor_id OR a.campaign_id<>NEW.campaign_id OR a.ship_id<>h.target_ship_id OR a.duty_status<>'active' OR NEW.campaign_id<>h.campaign_id
  OR NEW.population_ordinal<>(SELECT count(*)+1 FROM senc_missile_crew_population WHERE missile_crew_hit_receipt_id=NEW.missile_crew_hit_receipt_id)
 THEN RAISE EXCEPTION 'Missile crew population must snapshot active assignments in deterministic order' USING ERRCODE='23514';END IF;RETURN NEW;END $$;
CREATE TRIGGER senc_missile_crew_population_valid BEFORE INSERT ON senc_missile_crew_population FOR EACH ROW EXECUTE FUNCTION senc_validate_missile_crew_population();
CREATE FUNCTION senc_validate_missile_crew_population_receipt() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE expected integer;actual integer;BEGIN
 SELECT active_crew_count INTO STRICT expected FROM senc_missile_crew_hit_receipt WHERE missile_crew_hit_receipt_id=NEW.missile_crew_hit_receipt_id FOR UPDATE;
 SELECT count(*) INTO actual FROM senc_missile_crew_population WHERE missile_crew_hit_receipt_id=NEW.missile_crew_hit_receipt_id;
 IF NEW.population_count<>expected OR actual<>expected THEN RAISE EXCEPTION 'Missile crew population receipt requires the complete active population' USING ERRCODE='23514';END IF;RETURN NEW;END $$;
CREATE TRIGGER senc_missile_crew_population_receipt_valid BEFORE INSERT ON senc_missile_crew_population_receipt FOR EACH ROW EXECUTE FUNCTION senc_validate_missile_crew_population_receipt();

CREATE TABLE senc_missile_crew_target(
 missile_crew_hit_receipt_id bigint NOT NULL REFERENCES senc_missile_crew_hit_receipt(missile_crew_hit_receipt_id),target_order smallint NOT NULL CHECK(target_order>0),population_ordinal smallint NOT NULL,actor_id bigint NOT NULL,random_ordinal smallint,
 PRIMARY KEY(missile_crew_hit_receipt_id,target_order),UNIQUE(missile_crew_hit_receipt_id,actor_id),FOREIGN KEY(missile_crew_hit_receipt_id,population_ordinal) REFERENCES senc_missile_crew_population(missile_crew_hit_receipt_id,population_ordinal));
CREATE TABLE senc_missile_crew_target_receipt(missile_crew_hit_receipt_id bigint PRIMARY KEY REFERENCES senc_missile_crew_hit_receipt(missile_crew_hit_receipt_id),target_count smallint NOT NULL CHECK(target_count>=0),recorded_at timestamptz NOT NULL DEFAULT clock_timestamp());
CREATE FUNCTION senc_validate_missile_crew_target() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE h senc_missile_crew_hit_receipt%ROWTYPE;selected bigint;population integer;BEGIN
 SELECT * INTO STRICT h FROM senc_missile_crew_hit_receipt WHERE missile_crew_hit_receipt_id=NEW.missile_crew_hit_receipt_id FOR UPDATE;
 SELECT actor_id INTO STRICT selected FROM senc_missile_crew_population WHERE missile_crew_hit_receipt_id=NEW.missile_crew_hit_receipt_id AND population_ordinal=NEW.population_ordinal;
 SELECT population_count INTO STRICT population FROM senc_missile_crew_population_receipt WHERE missile_crew_hit_receipt_id=NEW.missile_crew_hit_receipt_id;
 IF EXISTS(SELECT 1 FROM senc_missile_crew_target_receipt WHERE missile_crew_hit_receipt_id=NEW.missile_crew_hit_receipt_id) OR selected<>NEW.actor_id OR h.target_scope='none'
  OR NEW.target_order<>(SELECT count(*)+1 FROM senc_missile_crew_target WHERE missile_crew_hit_receipt_id=NEW.missile_crew_hit_receipt_id)
  OR (h.target_scope='one-random' AND (NEW.target_order<>1 OR NEW.random_ordinal<>NEW.population_ordinal OR NEW.random_ordinal NOT BETWEEN 1 AND population))
  OR (h.target_scope='all' AND (NEW.random_ordinal IS NOT NULL OR NEW.population_ordinal<>NEW.target_order))
 THEN RAISE EXCEPTION 'Missile crew target must match the published scope and snapshotted population' USING ERRCODE='23514';END IF;RETURN NEW;END $$;
CREATE TRIGGER senc_missile_crew_target_valid BEFORE INSERT ON senc_missile_crew_target FOR EACH ROW EXECUTE FUNCTION senc_validate_missile_crew_target();
CREATE FUNCTION senc_validate_missile_crew_target_receipt() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE scope text;population integer;actual integer;expected integer;BEGIN
 SELECT target_scope INTO STRICT scope FROM senc_missile_crew_hit_receipt WHERE missile_crew_hit_receipt_id=NEW.missile_crew_hit_receipt_id FOR UPDATE;
 SELECT population_count INTO STRICT population FROM senc_missile_crew_population_receipt WHERE missile_crew_hit_receipt_id=NEW.missile_crew_hit_receipt_id;
 SELECT count(*) INTO actual FROM senc_missile_crew_target WHERE missile_crew_hit_receipt_id=NEW.missile_crew_hit_receipt_id;expected:=CASE scope WHEN 'none' THEN 0 WHEN 'one-random' THEN 1 ELSE population END;
 IF NEW.target_count<>expected OR actual<>expected THEN RAISE EXCEPTION 'Missile crew target receipt must finalize the exact target set' USING ERRCODE='23514';END IF;RETURN NEW;END $$;
CREATE TRIGGER senc_missile_crew_target_receipt_valid BEFORE INSERT ON senc_missile_crew_target_receipt FOR EACH ROW EXECUTE FUNCTION senc_validate_missile_crew_target_receipt();

CREATE TABLE senc_missile_crew_consequence_die(missile_crew_hit_receipt_id bigint NOT NULL,target_order smallint NOT NULL,die_order smallint NOT NULL CHECK(die_order>0),result smallint NOT NULL CHECK(result BETWEEN 1 AND 6),PRIMARY KEY(missile_crew_hit_receipt_id,target_order,die_order),FOREIGN KEY(missile_crew_hit_receipt_id,target_order) REFERENCES senc_missile_crew_target(missile_crew_hit_receipt_id,target_order));
CREATE TABLE senc_missile_crew_consequence_receipt(missile_crew_hit_receipt_id bigint NOT NULL,target_order smallint NOT NULL,actor_id bigint NOT NULL,rolled_total smallint NOT NULL CHECK(rolled_total>0),normal_damage smallint NOT NULL CHECK(normal_damage>=0),radiation_rads integer NOT NULL CHECK(radiation_rads>=0),recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),PRIMARY KEY(missile_crew_hit_receipt_id,target_order),FOREIGN KEY(missile_crew_hit_receipt_id,target_order) REFERENCES senc_missile_crew_target(missile_crew_hit_receipt_id,target_order),CHECK((normal_damage=0)<>(radiation_rads=0)));
CREATE FUNCTION senc_validate_missile_crew_consequence_die() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE dice_count integer;BEGIN SELECT damage_dice_count INTO STRICT dice_count FROM senc_missile_crew_hit_receipt WHERE missile_crew_hit_receipt_id=NEW.missile_crew_hit_receipt_id;
 IF NEW.die_order>dice_count OR EXISTS(SELECT 1 FROM senc_missile_crew_consequence_receipt WHERE missile_crew_hit_receipt_id=NEW.missile_crew_hit_receipt_id AND target_order=NEW.target_order) THEN RAISE EXCEPTION 'Missile crew consequence die exceeds its unresolved dice count' USING ERRCODE='23514';END IF;RETURN NEW;END $$;
CREATE TRIGGER senc_missile_crew_consequence_die_valid BEFORE INSERT ON senc_missile_crew_consequence_die FOR EACH ROW EXECUTE FUNCTION senc_validate_missile_crew_consequence_die();
CREATE FUNCTION senc_validate_missile_crew_consequence() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE h senc_missile_crew_hit_receipt%ROWTYPE;target_actor bigint;n integer;total integer;BEGIN
 SELECT * INTO STRICT h FROM senc_missile_crew_hit_receipt WHERE missile_crew_hit_receipt_id=NEW.missile_crew_hit_receipt_id FOR UPDATE;
 SELECT actor_id INTO STRICT target_actor FROM senc_missile_crew_target WHERE missile_crew_hit_receipt_id=NEW.missile_crew_hit_receipt_id AND target_order=NEW.target_order;
 SELECT count(*),coalesce(sum(result),0) INTO n,total FROM senc_missile_crew_consequence_die WHERE missile_crew_hit_receipt_id=NEW.missile_crew_hit_receipt_id AND target_order=NEW.target_order;
 IF NEW.actor_id<>target_actor OR n<>h.damage_dice_count OR NEW.rolled_total<>total OR NEW.normal_damage<>(CASE WHEN h.damage_kind='normal' THEN total ELSE 0 END) OR NEW.radiation_rads<>(CASE WHEN h.damage_kind='radiation' THEN total*h.radiation_multiplier_rads ELSE 0 END)
 THEN RAISE EXCEPTION 'Missile crew consequence fails target, dice, damage, or radiation recomputation' USING ERRCODE='23514';END IF;RETURN NEW;END $$;
CREATE TRIGGER senc_missile_crew_consequence_valid BEFORE INSERT ON senc_missile_crew_consequence_receipt FOR EACH ROW EXECUTE FUNCTION senc_validate_missile_crew_consequence();

ALTER TABLE health_damage_instance ADD COLUMN missile_crew_hit_receipt_id bigint,ADD COLUMN missile_crew_target_order smallint,
 ADD CONSTRAINT health_damage_missile_crew_fk FOREIGN KEY(missile_crew_hit_receipt_id,missile_crew_target_order) REFERENCES senc_missile_crew_consequence_receipt(missile_crew_hit_receipt_id,target_order),
 ADD CONSTRAINT health_damage_missile_crew_unique UNIQUE(missile_crew_hit_receipt_id,missile_crew_target_order),ADD CONSTRAINT health_damage_missile_crew_pair CHECK((missile_crew_hit_receipt_id IS NULL)=(missile_crew_target_order IS NULL));
ALTER TABLE health_damage_instance DROP CONSTRAINT health_damage_exactly_one_source_check,
 ADD CONSTRAINT health_damage_exactly_one_source_check CHECK(num_nonnulls(attack_command_id,environmental_command_id,explosion_command_id,grapple_option_command_id)+CASE WHEN crew_damage_location_hit_receipt_id IS NULL THEN 0 ELSE 1 END+CASE WHEN missile_crew_hit_receipt_id IS NULL THEN 0 ELSE 1 END=1);
ALTER TABLE health_radiation_exposure ALTER COLUMN damage_location_hit_receipt_id DROP NOT NULL,ALTER COLUMN target_order DROP NOT NULL,
 ADD COLUMN missile_crew_hit_receipt_id bigint,ADD COLUMN missile_crew_target_order smallint,
 ADD CONSTRAINT health_radiation_missile_crew_fk FOREIGN KEY(missile_crew_hit_receipt_id,missile_crew_target_order) REFERENCES senc_missile_crew_consequence_receipt(missile_crew_hit_receipt_id,target_order),
 ADD CONSTRAINT health_radiation_one_crew_origin CHECK(num_nonnulls(damage_location_hit_receipt_id,missile_crew_hit_receipt_id)=1),ADD CONSTRAINT health_radiation_legacy_pair CHECK((damage_location_hit_receipt_id IS NULL)=(target_order IS NULL)),
 ADD CONSTRAINT health_radiation_missile_pair CHECK((missile_crew_hit_receipt_id IS NULL)=(missile_crew_target_order IS NULL)),ADD CONSTRAINT health_radiation_missile_crew_unique UNIQUE(missile_crew_hit_receipt_id,missile_crew_target_order);
CREATE TABLE senc_missile_crew_application_receipt(missile_crew_hit_receipt_id bigint NOT NULL,target_order smallint NOT NULL,actor_id bigint NOT NULL,damage_instance_id bigint UNIQUE REFERENCES health_damage_instance(damage_instance_id),radiation_exposure_id bigint UNIQUE REFERENCES health_radiation_exposure(radiation_exposure_id),recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),PRIMARY KEY(missile_crew_hit_receipt_id,target_order),FOREIGN KEY(missile_crew_hit_receipt_id,target_order) REFERENCES senc_missile_crew_consequence_receipt(missile_crew_hit_receipt_id,target_order),CHECK(num_nonnulls(damage_instance_id,radiation_exposure_id)=1));
CREATE FUNCTION senc_apply_missile_crew_consequence() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE h senc_missile_crew_hit_receipt%ROWTYPE;state actor_radiation_state%ROWTYPE;damage_id bigint;exposure_id bigint;BEGIN
 SELECT * INTO STRICT h FROM senc_missile_crew_hit_receipt WHERE missile_crew_hit_receipt_id=NEW.missile_crew_hit_receipt_id;
 IF NEW.normal_damage>0 THEN INSERT INTO health_damage_instance(target_actor_id,penetrating_damage,missile_crew_hit_receipt_id,missile_crew_target_order) VALUES(NEW.actor_id,NEW.normal_damage,NEW.missile_crew_hit_receipt_id,NEW.target_order) RETURNING damage_instance_id INTO damage_id;
  INSERT INTO senc_missile_crew_application_receipt(missile_crew_hit_receipt_id,target_order,actor_id,damage_instance_id) VALUES(NEW.missile_crew_hit_receipt_id,NEW.target_order,NEW.actor_id,damage_id);
 ELSE INSERT INTO actor_radiation_state(actor_id,campaign_id) VALUES(NEW.actor_id,h.campaign_id) ON CONFLICT(actor_id) DO NOTHING;SELECT * INTO STRICT state FROM actor_radiation_state WHERE actor_id=NEW.actor_id FOR UPDATE;
  UPDATE actor_radiation_state SET total_rads=state.total_rads+NEW.radiation_rads,concurrency_version=state.concurrency_version+1,updated_at=clock_timestamp() WHERE actor_id=NEW.actor_id;
  INSERT INTO health_radiation_exposure(missile_crew_hit_receipt_id,missile_crew_target_order,actor_id,campaign_id,rads_added,rads_before,rads_after,actor_radiation_version_before,actor_radiation_version_after)
  VALUES(NEW.missile_crew_hit_receipt_id,NEW.target_order,NEW.actor_id,h.campaign_id,NEW.radiation_rads,state.total_rads,state.total_rads+NEW.radiation_rads,state.concurrency_version,state.concurrency_version+1) RETURNING radiation_exposure_id INTO exposure_id;
  INSERT INTO senc_missile_crew_application_receipt(missile_crew_hit_receipt_id,target_order,actor_id,radiation_exposure_id) VALUES(NEW.missile_crew_hit_receipt_id,NEW.target_order,NEW.actor_id,exposure_id);END IF;RETURN NEW;END $$;
CREATE TRIGGER senc_missile_crew_consequence_apply AFTER INSERT ON senc_missile_crew_consequence_receipt FOR EACH ROW EXECUTE FUNCTION senc_apply_missile_crew_consequence();

CREATE FUNCTION senc_reject_missile_crew_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Missile crew damage receipts are immutable';END $$;
CREATE TRIGGER senc_missile_crew_hit_immutable BEFORE UPDATE OR DELETE ON senc_missile_crew_hit_receipt FOR EACH ROW EXECUTE FUNCTION senc_reject_missile_crew_mutation();
CREATE TRIGGER senc_missile_crew_population_immutable BEFORE UPDATE OR DELETE ON senc_missile_crew_population FOR EACH ROW EXECUTE FUNCTION senc_reject_missile_crew_mutation();
CREATE TRIGGER senc_missile_crew_population_receipt_immutable BEFORE UPDATE OR DELETE ON senc_missile_crew_population_receipt FOR EACH ROW EXECUTE FUNCTION senc_reject_missile_crew_mutation();
CREATE TRIGGER senc_missile_crew_target_immutable BEFORE UPDATE OR DELETE ON senc_missile_crew_target FOR EACH ROW EXECUTE FUNCTION senc_reject_missile_crew_mutation();
CREATE TRIGGER senc_missile_crew_target_receipt_immutable BEFORE UPDATE OR DELETE ON senc_missile_crew_target_receipt FOR EACH ROW EXECUTE FUNCTION senc_reject_missile_crew_mutation();
CREATE TRIGGER senc_missile_crew_consequence_die_immutable BEFORE UPDATE OR DELETE ON senc_missile_crew_consequence_die FOR EACH ROW EXECUTE FUNCTION senc_reject_missile_crew_mutation();
CREATE TRIGGER senc_missile_crew_consequence_immutable BEFORE UPDATE OR DELETE ON senc_missile_crew_consequence_receipt FOR EACH ROW EXECUTE FUNCTION senc_reject_missile_crew_mutation();
CREATE TRIGGER senc_missile_crew_application_immutable BEFORE UPDATE OR DELETE ON senc_missile_crew_application_receipt FOR EACH ROW EXECUTE FUNCTION senc_reject_missile_crew_mutation();
