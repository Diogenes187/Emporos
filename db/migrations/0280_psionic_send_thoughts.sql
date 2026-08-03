CREATE TABLE rule_psi_send_thoughts (
    power_rule_id bigint PRIMARY KEY REFERENCES psi_power(power_rule_id),
    transmits_thoughts boolean NOT NULL CHECK (transmits_thoughts),
    recipient_need_not_be_telepath boolean NOT NULL CHECK (
        recipient_need_not_be_telepath
    ),
    telepaths_normally_open boolean NOT NULL CHECK (telepaths_normally_open),
    telepath_may_close_shield boolean NOT NULL CHECK (
        telepath_may_close_shield
    ),
    shield_blocks_transmission boolean NOT NULL CHECK (
        shield_blocks_transmission
    ),
    effect_controls_content boolean NOT NULL CHECK (
        NOT effect_controls_content
    )
);

CREATE TABLE cmd_psi_sent_thought_receipt (
    activation_command_id bigint PRIMARY KEY REFERENCES
        cmd_psionic_activation_receipt(command_id),
    actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    target_actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    timing_rounds_snapshot smallint NOT NULL CHECK (
        timing_rounds_snapshot>0
    ),
    target_is_telepath boolean NOT NULL,
    transmitted_thought text NOT NULL CHECK (
        btrim(transmitted_thought)<>''
    ),
    delivered boolean NOT NULL CHECK (delivered),
    sent_at timestamptz NOT NULL,
    FOREIGN KEY (actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    FOREIGN KEY (target_actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id)
);

CREATE FUNCTION cmd_validate_psi_sent_thought()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE activation cmd_psionic_activation_receipt%ROWTYPE;
DECLARE expected_telepath boolean;
DECLARE shield_raised boolean;
BEGIN
 SELECT * INTO STRICT activation FROM cmd_psionic_activation_receipt
  WHERE command_id=NEW.activation_command_id;
 PERFORM 1 FROM rule_psi_send_thoughts
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
    OR activation.timing_total<>NEW.timing_rounds_snapshot
    OR activation.timing_unit<>'rounds'
    OR NEW.target_is_telepath<>expected_telepath
    OR (expected_telepath AND shield_raised) THEN
   RAISE EXCEPTION 'Sent-thought receipt does not match activation';
 END IF;
 RETURN NEW;
END; $$;

CREATE TRIGGER cmd_psi_sent_thought_valid
BEFORE INSERT ON cmd_psi_sent_thought_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_validate_psi_sent_thought();

CREATE FUNCTION cmd_reject_psi_sent_thought_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Sent-thought receipts are immutable'; END; $$;

CREATE TRIGGER cmd_psi_sent_thought_immutable
BEFORE UPDATE OR DELETE ON cmd_psi_sent_thought_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_psi_sent_thought_mutation();

COMMENT ON TABLE rule_psi_send_thoughts IS
    'CE-PSI-011 paired-source thought transmission and shield behavior.';
COMMENT ON TABLE cmd_psi_sent_thought_receipt IS
    'Immutable delivered thought content without invented Effect semantics.';
