CREATE TABLE rule_psionic_training (
 rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
 strength_dice_count smallint NOT NULL CHECK (strength_dice_count=2),
 strength_die_sides smallint NOT NULL CHECK (strength_die_sides=6),
 strength_penalty_per_career_term smallint NOT NULL CHECK (
  strength_penalty_per_career_term=-1),
 training_months smallint NOT NULL CHECK (training_months=4),
 training_cost_credits bigint NOT NULL CHECK (training_cost_credits=100000),
 learning_check_target smallint NOT NULL CHECK (learning_check_target=8),
 modifier_per_prior_attempt smallint NOT NULL CHECK (
  modifier_per_prior_attempt=-1),
 learned_talent_level smallint NOT NULL CHECK (learned_talent_level=0),
 referee_permission_required boolean NOT NULL CHECK (referee_permission_required)
);
CREATE TABLE cmd_psionic_strength_determination_receipt (
 receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 idempotency_key text NOT NULL UNIQUE CHECK (btrim(idempotency_key)<>''),
 actor_id bigint NOT NULL UNIQUE REFERENCES actor_actor(actor_id),
 career_terms_served smallint NOT NULL CHECK (career_terms_served>=0),
 die_one smallint NOT NULL CHECK (die_one BETWEEN 1 AND 6),
 die_two smallint NOT NULL CHECK (die_two BETWEEN 1 AND 6),
 raw_psionic_strength smallint NOT NULL,
 eligible_for_training boolean NOT NULL,
 determined_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 CHECK (raw_psionic_strength=die_one+die_two-career_terms_served),
 CHECK (eligible_for_training=(raw_psionic_strength>0))
);
CREATE FUNCTION cmd_validate_psionic_strength_determination()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE actual_terms integer;
BEGIN
 SELECT count(*) INTO actual_terms FROM actor_career_term term
 JOIN actor_career_stint stint USING(career_stint_id)
 WHERE stint.actor_id=NEW.actor_id;
 IF NEW.career_terms_served<>actual_terms
 THEN RAISE EXCEPTION 'Psionic Strength career-term snapshot is invalid'; END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER cmd_psionic_strength_determination_valid BEFORE INSERT
ON cmd_psionic_strength_determination_receipt FOR EACH ROW
EXECUTE FUNCTION cmd_validate_psionic_strength_determination();
CREATE TABLE camp_psionic_training (
 training_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 actor_id bigint NOT NULL UNIQUE REFERENCES actor_actor(actor_id),
 determination_receipt_id bigint NOT NULL UNIQUE REFERENCES
  cmd_psionic_strength_determination_receipt(receipt_id),
 training_months smallint NOT NULL CHECK (training_months=4),
 paid_credits bigint NOT NULL CHECK (paid_credits=100000),
 training_status text NOT NULL CHECK (
  training_status IN ('active','completed','abandoned')),
 started_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 completed_at timestamptz,
 CHECK ((training_status='completed')=(completed_at IS NOT NULL))
);
CREATE TABLE cmd_psionic_talent_learning_receipt (
 receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 idempotency_key text NOT NULL UNIQUE CHECK (btrim(idempotency_key)<>''),
 training_id bigint NOT NULL REFERENCES camp_psionic_training(training_id),
 talent_rule_id bigint NOT NULL REFERENCES psi_talent(talent_rule_id),
 attempt_number smallint NOT NULL CHECK (attempt_number BETWEEN 1 AND 5),
 psionic_strength_value smallint NOT NULL CHECK (psionic_strength_value>0),
 characteristic_modifier smallint NOT NULL,
 talent_learning_modifier smallint NOT NULL,
 prior_attempt_modifier smallint NOT NULL,
 die_one smallint NOT NULL CHECK (die_one BETWEEN 1 AND 6),
 die_two smallint NOT NULL CHECK (die_two BETWEEN 1 AND 6),
 check_total smallint NOT NULL,
 target_number smallint NOT NULL CHECK (target_number=8),
 succeeded boolean NOT NULL,
 learned_level smallint,
 attempted_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE (training_id,talent_rule_id),
 UNIQUE (training_id,attempt_number),
 CHECK (prior_attempt_modifier=1-attempt_number),
 CHECK (check_total=die_one+die_two+characteristic_modifier+
                    talent_learning_modifier+prior_attempt_modifier),
 CHECK (succeeded=(check_total>=target_number)),
 CHECK ((succeeded AND learned_level=0)
     OR (NOT succeeded AND learned_level IS NULL))
);
CREATE FUNCTION cmd_validate_psionic_training_receipts()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE determination cmd_psionic_strength_determination_receipt%ROWTYPE;
DECLARE training camp_psionic_training%ROWTYPE;
DECLARE talent psi_talent%ROWTYPE;
DECLARE prior_count integer;
BEGIN
 IF TG_TABLE_NAME='camp_psionic_training' THEN
  SELECT * INTO determination FROM cmd_psionic_strength_determination_receipt
   WHERE receipt_id=NEW.determination_receipt_id;
  IF determination.actor_id<>NEW.actor_id OR NOT determination.eligible_for_training
  THEN RAISE EXCEPTION 'Psionic training requires an eligible determination'; END IF;
 ELSE
  SELECT * INTO training FROM camp_psionic_training WHERE training_id=NEW.training_id;
  SELECT * INTO determination FROM cmd_psionic_strength_determination_receipt
   WHERE receipt_id=training.determination_receipt_id;
  SELECT * INTO talent FROM psi_talent WHERE talent_rule_id=NEW.talent_rule_id;
  SELECT count(*) INTO prior_count FROM cmd_psionic_talent_learning_receipt
   WHERE training_id=NEW.training_id;
  IF training.training_status<>'active' OR NEW.attempt_number<>prior_count+1
   OR NEW.psionic_strength_value<>determination.raw_psionic_strength
   OR NEW.talent_learning_modifier<>talent.learning_modifier
  THEN RAISE EXCEPTION 'Psionic learning snapshot or sequence is invalid'; END IF;
 END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER camp_psionic_training_valid BEFORE INSERT ON camp_psionic_training
FOR EACH ROW EXECUTE FUNCTION cmd_validate_psionic_training_receipts();
CREATE TRIGGER cmd_psionic_learning_valid BEFORE INSERT ON cmd_psionic_talent_learning_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_validate_psionic_training_receipts();
CREATE FUNCTION cmd_reject_psionic_training_receipt_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Psionic determination and learning receipts are immutable'; END; $$;
CREATE TRIGGER cmd_psionic_determination_immutable BEFORE UPDATE OR DELETE
ON cmd_psionic_strength_determination_receipt FOR EACH ROW
EXECUTE FUNCTION cmd_reject_psionic_training_receipt_mutation();
CREATE TRIGGER cmd_psionic_learning_immutable BEFORE UPDATE OR DELETE
ON cmd_psionic_talent_learning_receipt FOR EACH ROW
EXECUTE FUNCTION cmd_reject_psionic_training_receipt_mutation();
COMMENT ON TABLE rule_psionic_training IS
 'CE-PSI-001 paired-source Psionic Strength determination and training procedure.';
