CREATE TABLE rule_psi_life_detection (
    power_rule_id bigint PRIMARY KEY REFERENCES psi_power(power_rule_id),
    detects_mind_presence boolean NOT NULL CHECK (detects_mind_presence),
    detects_mind_count boolean NOT NULL CHECK (detects_mind_count),
    detects_general_type boolean NOT NULL CHECK (detects_general_type),
    detects_approximate_location boolean NOT NULL CHECK (
        detects_approximate_location
    ),
    filters_insignificant_life boolean NOT NULL CHECK (
        filters_insignificant_life
    ),
    shielded_minds_undetectable boolean NOT NULL CHECK (
        shielded_minds_undetectable
    ),
    recognizes_known_individuals boolean NOT NULL CHECK (
        recognizes_known_individuals
    )
);

CREATE TABLE cmd_psi_life_detection_receipt (
    activation_command_id bigint PRIMARY KEY REFERENCES
        cmd_psionic_activation_receipt(command_id),
    actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    effect_snapshot smallint NOT NULL,
    timing_rounds_snapshot smallint NOT NULL CHECK (
        timing_rounds_snapshot>0
    ),
    search_area_reference text NOT NULL CHECK (
        btrim(search_area_reference)<>''
    ),
    referee_summary text NOT NULL CHECK (btrim(referee_summary)<>''),
    detected_mind_count smallint NOT NULL CHECK (detected_mind_count>=0),
    detected_at timestamptz NOT NULL,
    FOREIGN KEY (actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id)
);

CREATE TABLE cmd_psi_life_detection_mind (
    activation_command_id bigint NOT NULL REFERENCES
        cmd_psi_life_detection_receipt(activation_command_id),
    mind_order smallint NOT NULL CHECK (mind_order>0),
    detected_actor_id bigint,
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    general_mind_type text NOT NULL CHECK (btrim(general_mind_type)<>''),
    approximate_location text NOT NULL CHECK (
        btrim(approximate_location)<>''
    ),
    significant_mind boolean NOT NULL CHECK (significant_mind),
    recognized_known_individual boolean NOT NULL,
    recognition_basis text,
    PRIMARY KEY (activation_command_id,mind_order),
    FOREIGN KEY (detected_actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    CHECK (
        (recognized_known_individual AND detected_actor_id IS NOT NULL
         AND recognition_basis IS NOT NULL
         AND btrim(recognition_basis)<>'')
        OR
        (NOT recognized_known_individual AND recognition_basis IS NULL)
    )
);

CREATE FUNCTION cmd_validate_psi_life_detection()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE activation cmd_psionic_activation_receipt%ROWTYPE;
BEGIN
 SELECT * INTO STRICT activation FROM cmd_psionic_activation_receipt
  WHERE command_id=NEW.activation_command_id;
 PERFORM 1 FROM rule_psi_life_detection
  WHERE power_rule_id=activation.power_rule_id;
 IF NOT activation.succeeded OR activation.actor_id<>NEW.actor_id
    OR activation.effect<>NEW.effect_snapshot
    OR activation.timing_total<>NEW.timing_rounds_snapshot
    OR activation.timing_unit<>'rounds' THEN
   RAISE EXCEPTION 'Life Detection receipt does not match activation';
 END IF;
 RETURN NEW;
END; $$;

CREATE FUNCTION cmd_validate_psi_life_detection_mind()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE receipt cmd_psi_life_detection_receipt%ROWTYPE;
DECLARE trained_telepath boolean;
DECLARE shield_raised boolean;
BEGIN
 SELECT * INTO STRICT receipt FROM cmd_psi_life_detection_receipt
  WHERE activation_command_id=NEW.activation_command_id;
 IF receipt.campaign_id<>NEW.campaign_id THEN
   RAISE EXCEPTION 'Detected mind is outside the activation campaign';
 END IF;
 IF NEW.detected_actor_id IS NOT NULL THEN
   SELECT EXISTS (
            SELECT 1 FROM actor_skill skill
            JOIN rule_rule rule ON rule.rule_id=skill.skill_rule_id
             AND rule.rule_code='skill.psionic-telepathy'
            WHERE skill.actor_id=NEW.detected_actor_id
          ),
          COALESCE((
            SELECT state.shield_raised
            FROM actor_telepathic_shield_state state
            WHERE state.actor_id=NEW.detected_actor_id
          ),true)
     INTO trained_telepath,shield_raised;
   IF trained_telepath AND shield_raised THEN
     RAISE EXCEPTION 'Shielded minds are undetectable';
   END IF;
 END IF;
 RETURN NEW;
END; $$;

CREATE FUNCTION cmd_validate_psi_life_detection_count()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE expected_count integer;
DECLARE receipt_count integer;
BEGIN
 SELECT count(*) INTO expected_count FROM cmd_psi_life_detection_mind
  WHERE activation_command_id=NEW.activation_command_id;
 SELECT detected_mind_count INTO STRICT receipt_count
   FROM cmd_psi_life_detection_receipt
  WHERE activation_command_id=NEW.activation_command_id;
 IF expected_count<>receipt_count THEN
   RAISE EXCEPTION 'Life Detection mind count does not match receipt';
 END IF;
 RETURN NULL;
END; $$;

CREATE CONSTRAINT TRIGGER cmd_psi_life_detection_count_valid
AFTER INSERT OR UPDATE OR DELETE ON cmd_psi_life_detection_mind
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
EXECUTE FUNCTION cmd_validate_psi_life_detection_count();

CREATE CONSTRAINT TRIGGER cmd_psi_life_detection_empty_count_valid
AFTER INSERT OR UPDATE ON cmd_psi_life_detection_receipt
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
EXECUTE FUNCTION cmd_validate_psi_life_detection_count();

CREATE TRIGGER cmd_psi_life_detection_valid
BEFORE INSERT ON cmd_psi_life_detection_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_validate_psi_life_detection();

CREATE FUNCTION cmd_reject_psi_life_detection_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Life Detection receipts are immutable'; END; $$;

CREATE TRIGGER cmd_psi_life_detection_immutable
BEFORE UPDATE OR DELETE ON cmd_psi_life_detection_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_psi_life_detection_mutation();
CREATE TRIGGER cmd_psi_life_detection_mind_immutable
BEFORE UPDATE OR DELETE ON cmd_psi_life_detection_mind
FOR EACH ROW EXECUTE FUNCTION cmd_reject_psi_life_detection_mutation();

COMMENT ON TABLE rule_psi_life_detection IS
    'CE-PSI-008 paired-source Life Detection facts without invented precision.';
COMMENT ON TABLE cmd_psi_life_detection_receipt IS
    'Immutable campaign-safe Life Detection observation header.';
COMMENT ON TABLE cmd_psi_life_detection_mind IS
    'Normalized detected minds; Referee location/type text is evidence.';
