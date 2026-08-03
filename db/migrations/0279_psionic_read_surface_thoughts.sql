CREATE TABLE rule_psi_read_surface_thoughts (
    power_rule_id bigint PRIMARY KEY REFERENCES psi_power(power_rule_id),
    reads_active_thoughts_only boolean NOT NULL CHECK (
        reads_active_thoughts_only
    ),
    reads_current_thoughts_only boolean NOT NULL CHECK (
        reads_current_thoughts_only
    ),
    nontelepath_subject_unaware boolean NOT NULL CHECK (
        nontelepath_subject_unaware
    ),
    telepath_requires_lowered_shield boolean NOT NULL CHECK (
        telepath_requires_lowered_shield
    ),
    telepath_lowering_is_willing boolean NOT NULL CHECK (
        telepath_lowering_is_willing
    ),
    effect_controls_clarity boolean NOT NULL CHECK (effect_controls_clarity)
);

CREATE TABLE cmd_psi_surface_thought_receipt (
    activation_command_id bigint PRIMARY KEY REFERENCES
        cmd_psionic_activation_receipt(command_id),
    actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    target_actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    effect_snapshot smallint NOT NULL,
    timing_rounds_snapshot smallint NOT NULL CHECK (
        timing_rounds_snapshot>0
    ),
    target_is_telepath boolean NOT NULL,
    target_unaware boolean NOT NULL,
    telepath_consent_reference text,
    active_current_thoughts text NOT NULL CHECK (
        btrim(active_current_thoughts)<>''
    ),
    clarity_evidence text NOT NULL CHECK (btrim(clarity_evidence)<>''),
    observed_at timestamptz NOT NULL,
    FOREIGN KEY (actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    FOREIGN KEY (target_actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    CHECK (
        (target_is_telepath AND NOT target_unaware
         AND telepath_consent_reference IS NOT NULL
         AND btrim(telepath_consent_reference)<>'')
        OR
        (NOT target_is_telepath AND target_unaware
         AND telepath_consent_reference IS NULL)
    )
);

CREATE FUNCTION cmd_validate_psi_surface_thought()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE activation cmd_psionic_activation_receipt%ROWTYPE;
DECLARE expected_telepath boolean;
DECLARE shield_raised boolean;
BEGIN
 SELECT * INTO STRICT activation FROM cmd_psionic_activation_receipt
  WHERE command_id=NEW.activation_command_id;
 PERFORM 1 FROM rule_psi_read_surface_thoughts
  WHERE power_rule_id=activation.power_rule_id;
 SELECT EXISTS (
          SELECT 1 FROM actor_skill skill
          JOIN rule_rule rule ON rule.rule_id=skill.skill_rule_id
           AND rule.rule_code='skill.psionic-telepathy'
          WHERE skill.actor_id=NEW.target_actor_id
        ),
        COALESCE((
          SELECT state.shield_raised FROM actor_telepathic_shield_state state
          WHERE state.actor_id=NEW.target_actor_id
        ),true)
   INTO expected_telepath,shield_raised;
 IF NOT activation.succeeded OR activation.actor_id<>NEW.actor_id
    OR activation.target_actor_id<>NEW.target_actor_id
    OR activation.effect<>NEW.effect_snapshot
    OR activation.timing_total<>NEW.timing_rounds_snapshot
    OR activation.timing_unit<>'rounds'
    OR NEW.target_is_telepath<>expected_telepath
    OR NEW.target_unaware=expected_telepath
    OR (expected_telepath AND shield_raised) THEN
   RAISE EXCEPTION 'Surface-thought receipt does not match activation';
 END IF;
 RETURN NEW;
END; $$;

CREATE TRIGGER cmd_psi_surface_thought_valid
BEFORE INSERT ON cmd_psi_surface_thought_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_validate_psi_surface_thought();

CREATE FUNCTION cmd_reject_psi_surface_thought_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Surface-thought receipts are immutable'; END; $$;

CREATE TRIGGER cmd_psi_surface_thought_immutable
BEFORE UPDATE OR DELETE ON cmd_psi_surface_thought_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_psi_surface_thought_mutation();

COMMENT ON TABLE rule_psi_read_surface_thoughts IS
    'CE-PSI-010 paired-source active/current thoughts, awareness, and clarity.';
COMMENT ON TABLE cmd_psi_surface_thought_receipt IS
    'Immutable current-thought evidence with explicit telepath consent.';
