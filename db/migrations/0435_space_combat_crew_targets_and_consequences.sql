CREATE TABLE senc_crew_damage_population (
 damage_location_hit_receipt_id bigint NOT NULL REFERENCES senc_crew_damage_attempt(damage_location_hit_receipt_id),
 population_ordinal smallint NOT NULL CHECK(population_ordinal>0),crew_assignment_id bigint NOT NULL,
 actor_id bigint NOT NULL,campaign_id bigint NOT NULL,PRIMARY KEY(damage_location_hit_receipt_id,population_ordinal),
 UNIQUE(damage_location_hit_receipt_id,crew_assignment_id),UNIQUE(damage_location_hit_receipt_id,actor_id),
 FOREIGN KEY(actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id)
);
CREATE TABLE senc_crew_damage_population_receipt(
 damage_location_hit_receipt_id bigint PRIMARY KEY REFERENCES senc_crew_damage_attempt(damage_location_hit_receipt_id),
 population_count smallint NOT NULL CHECK(population_count>0),recorded_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE senc_crew_damage_target(
 damage_location_hit_receipt_id bigint NOT NULL REFERENCES senc_crew_damage_outcome_receipt(damage_location_hit_receipt_id),
 target_order smallint NOT NULL CHECK(target_order>0),population_ordinal smallint NOT NULL,actor_id bigint NOT NULL,
 random_ordinal smallint,PRIMARY KEY(damage_location_hit_receipt_id,target_order),UNIQUE(damage_location_hit_receipt_id,actor_id),
 FOREIGN KEY(damage_location_hit_receipt_id,population_ordinal) REFERENCES senc_crew_damage_population(damage_location_hit_receipt_id,population_ordinal)
);
CREATE TABLE senc_crew_damage_target_receipt(
 damage_location_hit_receipt_id bigint PRIMARY KEY REFERENCES senc_crew_damage_outcome_receipt(damage_location_hit_receipt_id),
 target_count smallint NOT NULL CHECK(target_count>=0),recorded_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE senc_crew_damage_consequence_die(
 damage_location_hit_receipt_id bigint NOT NULL,target_order smallint NOT NULL,die_order smallint NOT NULL CHECK(die_order>0),
 result smallint NOT NULL CHECK(result BETWEEN 1 AND 6),PRIMARY KEY(damage_location_hit_receipt_id,target_order,die_order),
 FOREIGN KEY(damage_location_hit_receipt_id,target_order) REFERENCES senc_crew_damage_target(damage_location_hit_receipt_id,target_order)
);
CREATE TABLE senc_crew_damage_consequence_receipt(
 damage_location_hit_receipt_id bigint NOT NULL,target_order smallint NOT NULL,actor_id bigint NOT NULL,
 rolled_total smallint NOT NULL CHECK(rolled_total>0),normal_damage smallint NOT NULL CHECK(normal_damage>=0),
 radiation_rads integer NOT NULL CHECK(radiation_rads>=0),recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY(damage_location_hit_receipt_id,target_order),
 FOREIGN KEY(damage_location_hit_receipt_id,target_order) REFERENCES senc_crew_damage_target(damage_location_hit_receipt_id,target_order),
 CHECK((normal_damage=0)<>(radiation_rads=0))
);

CREATE FUNCTION senc_validate_crew_damage_population() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE a senc_crew_damage_attempt%ROWTYPE; assignment record;
BEGIN SELECT * INTO STRICT a FROM senc_crew_damage_attempt WHERE damage_location_hit_receipt_id=NEW.damage_location_hit_receipt_id FOR UPDATE;
 IF EXISTS(SELECT 1 FROM senc_crew_damage_population_receipt WHERE damage_location_hit_receipt_id=NEW.damage_location_hit_receipt_id) THEN
  RAISE EXCEPTION 'Crew population is already finalized' USING ERRCODE='23514'; END IF;
 SELECT actor_id,campaign_id,ship_id,duty_status INTO STRICT assignment FROM ship_crew_assignment WHERE crew_assignment_id=NEW.crew_assignment_id;
 IF assignment.actor_id<>NEW.actor_id OR assignment.campaign_id<>NEW.campaign_id OR assignment.ship_id<>a.target_ship_id
  OR assignment.duty_status<>'active' OR NEW.campaign_id<>a.campaign_id OR NEW.population_ordinal<>(SELECT count(*)+1 FROM senc_crew_damage_population WHERE damage_location_hit_receipt_id=NEW.damage_location_hit_receipt_id) THEN
  RAISE EXCEPTION 'Crew population must snapshot each active assignment in deterministic order' USING ERRCODE='23514'; END IF; RETURN NEW;
END $$;
CREATE TRIGGER senc_crew_damage_population_valid BEFORE INSERT ON senc_crew_damage_population FOR EACH ROW EXECUTE FUNCTION senc_validate_crew_damage_population();
CREATE FUNCTION senc_validate_crew_damage_population_receipt() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE expected integer; actual integer;
BEGIN SELECT active_crew_count INTO STRICT expected FROM senc_crew_damage_attempt WHERE damage_location_hit_receipt_id=NEW.damage_location_hit_receipt_id FOR UPDATE;
 SELECT count(*) INTO actual FROM senc_crew_damage_population WHERE damage_location_hit_receipt_id=NEW.damage_location_hit_receipt_id;
 IF NEW.population_count<>expected OR actual<>expected THEN RAISE EXCEPTION 'Crew population receipt must finalize the complete snapshotted population' USING ERRCODE='23514'; END IF; RETURN NEW; END $$;
CREATE TRIGGER senc_crew_damage_population_receipt_valid BEFORE INSERT ON senc_crew_damage_population_receipt FOR EACH ROW EXECUTE FUNCTION senc_validate_crew_damage_population_receipt();

CREATE FUNCTION senc_validate_crew_damage_target() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE o senc_crew_damage_outcome_receipt%ROWTYPE; selected_actor bigint; pop_count integer;
BEGIN SELECT * INTO STRICT o FROM senc_crew_damage_outcome_receipt WHERE damage_location_hit_receipt_id=NEW.damage_location_hit_receipt_id FOR UPDATE;
 IF NOT EXISTS(SELECT 1 FROM senc_crew_damage_population_receipt WHERE damage_location_hit_receipt_id=NEW.damage_location_hit_receipt_id)
  OR EXISTS(SELECT 1 FROM senc_crew_damage_target_receipt WHERE damage_location_hit_receipt_id=NEW.damage_location_hit_receipt_id) THEN RAISE EXCEPTION 'Crew targets require a finalized population and open target set' USING ERRCODE='23514'; END IF;
 SELECT actor_id INTO STRICT selected_actor FROM senc_crew_damage_population WHERE damage_location_hit_receipt_id=NEW.damage_location_hit_receipt_id AND population_ordinal=NEW.population_ordinal;
 SELECT receipt.population_count INTO pop_count FROM senc_crew_damage_population_receipt receipt WHERE damage_location_hit_receipt_id=NEW.damage_location_hit_receipt_id;
 IF selected_actor<>NEW.actor_id OR o.target_scope='none' OR NEW.target_order<>(SELECT count(*)+1 FROM senc_crew_damage_target WHERE damage_location_hit_receipt_id=NEW.damage_location_hit_receipt_id)
  OR (o.target_scope='one-random' AND (NEW.target_order<>1 OR NEW.random_ordinal IS NULL OR NEW.random_ordinal<>NEW.population_ordinal OR NEW.random_ordinal NOT BETWEEN 1 AND pop_count))
  OR (o.target_scope='all' AND (NEW.random_ordinal IS NOT NULL OR NEW.population_ordinal<>NEW.target_order)) THEN
  RAISE EXCEPTION 'Crew target does not match normalized target scope and population ordinal' USING ERRCODE='23514'; END IF; RETURN NEW;
END $$;
CREATE TRIGGER senc_crew_damage_target_valid BEFORE INSERT ON senc_crew_damage_target FOR EACH ROW EXECUTE FUNCTION senc_validate_crew_damage_target();
CREATE FUNCTION senc_validate_crew_damage_target_receipt() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE scope text; population integer; actual integer; expected integer;
BEGIN SELECT target_scope INTO STRICT scope FROM senc_crew_damage_outcome_receipt WHERE damage_location_hit_receipt_id=NEW.damage_location_hit_receipt_id FOR UPDATE;
 SELECT population_count INTO STRICT population FROM senc_crew_damage_population_receipt WHERE damage_location_hit_receipt_id=NEW.damage_location_hit_receipt_id;
 SELECT count(*) INTO actual FROM senc_crew_damage_target WHERE damage_location_hit_receipt_id=NEW.damage_location_hit_receipt_id;
 expected:=CASE scope WHEN 'none' THEN 0 WHEN 'one-random' THEN 1 ELSE population END;
 IF NEW.target_count<>expected OR actual<>expected THEN RAISE EXCEPTION 'Crew target receipt must finalize the exact normalized target set' USING ERRCODE='23514'; END IF; RETURN NEW; END $$;
CREATE TRIGGER senc_crew_damage_target_receipt_valid BEFORE INSERT ON senc_crew_damage_target_receipt FOR EACH ROW EXECUTE FUNCTION senc_validate_crew_damage_target_receipt();

CREATE FUNCTION senc_validate_crew_consequence_die() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE dice_count integer;
BEGIN SELECT damage_dice_count INTO STRICT dice_count FROM senc_crew_damage_outcome_receipt WHERE damage_location_hit_receipt_id=NEW.damage_location_hit_receipt_id;
 IF NEW.die_order>dice_count OR EXISTS(SELECT 1 FROM senc_crew_damage_consequence_receipt WHERE damage_location_hit_receipt_id=NEW.damage_location_hit_receipt_id AND target_order=NEW.target_order) THEN
  RAISE EXCEPTION 'Crew consequence die exceeds its unresolved published dice count' USING ERRCODE='23514'; END IF; RETURN NEW; END $$;
CREATE TRIGGER senc_crew_consequence_die_valid BEFORE INSERT ON senc_crew_damage_consequence_die FOR EACH ROW EXECUTE FUNCTION senc_validate_crew_consequence_die();
CREATE FUNCTION senc_validate_crew_consequence_receipt() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE o senc_crew_damage_outcome_receipt%ROWTYPE; target_actor bigint; n integer; total integer;
BEGIN SELECT * INTO STRICT o FROM senc_crew_damage_outcome_receipt WHERE damage_location_hit_receipt_id=NEW.damage_location_hit_receipt_id FOR UPDATE;
 SELECT actor_id INTO STRICT target_actor FROM senc_crew_damage_target WHERE damage_location_hit_receipt_id=NEW.damage_location_hit_receipt_id AND target_order=NEW.target_order;
 SELECT count(*),coalesce(sum(result),0) INTO n,total FROM senc_crew_damage_consequence_die WHERE damage_location_hit_receipt_id=NEW.damage_location_hit_receipt_id AND target_order=NEW.target_order;
 IF NEW.actor_id<>target_actor OR n<>o.damage_dice_count OR NEW.rolled_total<>total
  OR NEW.normal_damage<>(CASE WHEN o.radiation_multiplier_rads IS NULL THEN total ELSE 0 END)
  OR NEW.radiation_rads<>(CASE WHEN o.radiation_multiplier_rads IS NULL THEN 0 ELSE total*o.radiation_multiplier_rads END) THEN
  RAISE EXCEPTION 'Crew consequence receipt fails target, dice, or radiation recomputation' USING ERRCODE='23514'; END IF; RETURN NEW; END $$;
CREATE TRIGGER senc_crew_consequence_receipt_valid BEFORE INSERT ON senc_crew_damage_consequence_receipt FOR EACH ROW EXECUTE FUNCTION senc_validate_crew_consequence_receipt();

CREATE FUNCTION senc_reject_crew_target_consequence_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Crew population, targets, dice, and consequences are immutable'; END $$;
CREATE TRIGGER senc_crew_population_immutable BEFORE UPDATE OR DELETE ON senc_crew_damage_population FOR EACH ROW EXECUTE FUNCTION senc_reject_crew_target_consequence_mutation();
CREATE TRIGGER senc_crew_population_receipt_immutable BEFORE UPDATE OR DELETE ON senc_crew_damage_population_receipt FOR EACH ROW EXECUTE FUNCTION senc_reject_crew_target_consequence_mutation();
CREATE TRIGGER senc_crew_target_immutable BEFORE UPDATE OR DELETE ON senc_crew_damage_target FOR EACH ROW EXECUTE FUNCTION senc_reject_crew_target_consequence_mutation();
CREATE TRIGGER senc_crew_target_receipt_immutable BEFORE UPDATE OR DELETE ON senc_crew_damage_target_receipt FOR EACH ROW EXECUTE FUNCTION senc_reject_crew_target_consequence_mutation();
CREATE TRIGGER senc_crew_consequence_die_immutable BEFORE UPDATE OR DELETE ON senc_crew_damage_consequence_die FOR EACH ROW EXECUTE FUNCTION senc_reject_crew_target_consequence_mutation();
CREATE TRIGGER senc_crew_consequence_receipt_immutable BEFORE UPDATE OR DELETE ON senc_crew_damage_consequence_receipt FOR EACH ROW EXECUTE FUNCTION senc_reject_crew_target_consequence_mutation();
