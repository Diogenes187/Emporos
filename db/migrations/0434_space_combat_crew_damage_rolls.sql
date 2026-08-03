CREATE TABLE senc_crew_damage_attempt (
    damage_location_hit_receipt_id bigint PRIMARY KEY REFERENCES senc_damage_location_hit_receipt(damage_location_hit_receipt_id),
    target_ship_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    damage_kind text NOT NULL CHECK (damage_kind IN ('normal','radiation')),
    active_crew_count smallint NOT NULL CHECK (active_crew_count>0),
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    FOREIGN KEY (target_ship_id,campaign_id) REFERENCES ship_ship(ship_id,campaign_id)
);
CREATE TABLE senc_crew_damage_outcome_die (
    damage_location_hit_receipt_id bigint NOT NULL REFERENCES senc_crew_damage_attempt(damage_location_hit_receipt_id),
    die_order smallint NOT NULL CHECK (die_order BETWEEN 1 AND 2),
    result smallint NOT NULL CHECK (result BETWEEN 1 AND 6),
    PRIMARY KEY (damage_location_hit_receipt_id,die_order)
);
CREATE TABLE senc_crew_damage_outcome_receipt (
    damage_location_hit_receipt_id bigint PRIMARY KEY REFERENCES senc_crew_damage_attempt(damage_location_hit_receipt_id),
    roll_total smallint NOT NULL CHECK (roll_total BETWEEN 2 AND 12),
    target_scope text NOT NULL CHECK (target_scope IN ('none','one-random','all')),
    damage_dice_count smallint NOT NULL CHECK (damage_dice_count IN (0,2,4)),
    damage_die_sides smallint,
    radiation_multiplier_rads smallint,
    outcome_code text NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CHECK ((damage_dice_count=0)=(damage_die_sides IS NULL))
);

CREATE FUNCTION senc_validate_crew_damage_attempt() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE hit senc_damage_location_hit_receipt%ROWTYPE; crew_count integer; expected_kind text;
BEGIN
 SELECT * INTO STRICT hit FROM senc_damage_location_hit_receipt
 WHERE damage_location_hit_receipt_id=NEW.damage_location_hit_receipt_id FOR SHARE;
 expected_kind:=CASE hit.effect_code WHEN 'crew-radiation-hit' THEN 'radiation' ELSE 'normal' END;
 SELECT count(*) INTO crew_count FROM ship_crew_assignment
 WHERE ship_id=hit.target_ship_id AND campaign_id=hit.campaign_id AND duty_status='active';
 IF NOT hit.secondary_resolution_required
    OR hit.effect_code NOT IN ('roll-crew-damage','crew-normal-hit','crew-radiation-hit')
    OR NEW.target_ship_id<>hit.target_ship_id OR NEW.campaign_id<>hit.campaign_id
    OR NEW.damage_kind<>expected_kind OR NEW.active_crew_count<>crew_count OR crew_count=0 THEN
  RAISE EXCEPTION 'Crew damage attempt must snapshot eligible active crew for a pending crew hit' USING ERRCODE='23514';
 END IF; RETURN NEW;
END $$;
CREATE TRIGGER senc_crew_damage_attempt_valid BEFORE INSERT ON senc_crew_damage_attempt
FOR EACH ROW EXECUTE FUNCTION senc_validate_crew_damage_attempt();

CREATE FUNCTION senc_validate_crew_damage_die() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF EXISTS(SELECT 1 FROM senc_crew_damage_outcome_receipt WHERE damage_location_hit_receipt_id=NEW.damage_location_hit_receipt_id) THEN
  RAISE EXCEPTION 'Crew damage outcome dice cannot follow the outcome receipt' USING ERRCODE='23514';
 END IF; RETURN NEW;
END $$;
CREATE TRIGGER senc_crew_damage_die_valid BEFORE INSERT ON senc_crew_damage_outcome_die
FOR EACH ROW EXECUTE FUNCTION senc_validate_crew_damage_die();

CREATE FUNCTION senc_validate_crew_damage_outcome() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE attempt senc_crew_damage_attempt%ROWTYPE; die_count integer; die_total integer; expected record;
BEGIN
 SELECT * INTO STRICT attempt FROM senc_crew_damage_attempt
 WHERE damage_location_hit_receipt_id=NEW.damage_location_hit_receipt_id FOR UPDATE;
 SELECT count(*),coalesce(sum(result),0) INTO die_count,die_total FROM senc_crew_damage_outcome_die
 WHERE damage_location_hit_receipt_id=NEW.damage_location_hit_receipt_id;
 SELECT band.* INTO STRICT expected FROM rule_space_combat_crew_damage_band band
 JOIN rule_rule rule ON rule.rule_id=band.hit_location_rule_id
 WHERE rule.rule_code='combat.space.hit-locations' AND band.damage_kind=attempt.damage_kind
   AND band.roll_range @> die_total;
 IF die_count<>2 OR NEW.roll_total<>die_total OR NEW.target_scope<>expected.target_scope
    OR NEW.damage_dice_count<>expected.damage_dice_count
    OR NEW.damage_die_sides IS DISTINCT FROM expected.damage_die_sides
    OR NEW.radiation_multiplier_rads IS DISTINCT FROM expected.radiation_multiplier_rads
    OR NEW.outcome_code<>expected.outcome_code THEN
  RAISE EXCEPTION 'Crew damage outcome fails dice and normalized-band recomputation' USING ERRCODE='23514';
 END IF; RETURN NEW;
END $$;
CREATE TRIGGER senc_crew_damage_outcome_valid BEFORE INSERT ON senc_crew_damage_outcome_receipt
FOR EACH ROW EXECUTE FUNCTION senc_validate_crew_damage_outcome();

CREATE FUNCTION senc_reject_crew_damage_roll_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Crew damage attempts, dice, and outcomes are immutable'; END $$;
CREATE TRIGGER senc_crew_damage_attempt_immutable BEFORE UPDATE OR DELETE ON senc_crew_damage_attempt FOR EACH ROW EXECUTE FUNCTION senc_reject_crew_damage_roll_mutation();
CREATE TRIGGER senc_crew_damage_die_immutable BEFORE UPDATE OR DELETE ON senc_crew_damage_outcome_die FOR EACH ROW EXECUTE FUNCTION senc_reject_crew_damage_roll_mutation();
CREATE TRIGGER senc_crew_damage_outcome_immutable BEFORE UPDATE OR DELETE ON senc_crew_damage_outcome_receipt FOR EACH ROW EXECUTE FUNCTION senc_reject_crew_damage_roll_mutation();
