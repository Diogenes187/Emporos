CREATE TABLE rule_psi_clairvoyance_power (
    power_rule_id bigint PRIMARY KEY REFERENCES psi_power(power_rule_id),
    sensory_vision boolean NOT NULL,
    sensory_hearing boolean NOT NULL,
    snapshot_only boolean NOT NULL,
    effect_controls_accuracy boolean NOT NULL CHECK (
        effect_controls_accuracy
    ),
    effect_controls_clarity boolean NOT NULL CHECK (
        effect_controls_clarity
    ),
    effect_controls_detail boolean NOT NULL,
    effect_controls_duration_rounds boolean NOT NULL,
    undetectable_by_others boolean NOT NULL CHECK (
        undetectable_by_others
    ),
    targets_location boolean NOT NULL CHECK (targets_location),
    CHECK (sensory_vision OR sensory_hearing OR snapshot_only)
);

ALTER TABLE cmd_psionic_activation_receipt
    ADD COLUMN target_location_id bigint REFERENCES loc_location(location_id);

CREATE TABLE cmd_psi_clairvoyant_observation_receipt (
    activation_command_id bigint PRIMARY KEY REFERENCES
        cmd_psionic_activation_receipt(command_id),
    actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    target_location_id bigint NOT NULL,
    effect_snapshot smallint NOT NULL,
    timing_rounds_snapshot smallint NOT NULL CHECK (
        timing_rounds_snapshot>0
    ),
    sensory_vision boolean NOT NULL,
    sensory_hearing boolean NOT NULL,
    snapshot_only boolean NOT NULL,
    maintained_rounds smallint,
    referee_observation text NOT NULL CHECK (
        btrim(referee_observation)<>''
    ),
    observed_at timestamptz NOT NULL,
    FOREIGN KEY (actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    FOREIGN KEY (target_location_id,campaign_id)
        REFERENCES loc_location(location_id,campaign_id),
    CHECK (
        (snapshot_only AND maintained_rounds IS NULL)
        OR (NOT snapshot_only AND maintained_rounds IS NOT NULL
            AND maintained_rounds>0)
    )
);

CREATE FUNCTION cmd_validate_psi_clairvoyant_observation()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE activation cmd_psionic_activation_receipt%ROWTYPE;
DECLARE mechanic rule_psi_clairvoyance_power%ROWTYPE;
BEGIN
 SELECT * INTO STRICT activation FROM cmd_psionic_activation_receipt
  WHERE command_id=NEW.activation_command_id;
 SELECT * INTO STRICT mechanic FROM rule_psi_clairvoyance_power
  WHERE power_rule_id=activation.power_rule_id;
 IF NOT activation.succeeded OR activation.actor_id<>NEW.actor_id
    OR activation.target_location_id<>NEW.target_location_id
    OR activation.effect<>NEW.effect_snapshot
    OR activation.timing_total<>NEW.timing_rounds_snapshot
    OR activation.timing_unit<>'rounds'
    OR mechanic.sensory_vision<>NEW.sensory_vision
    OR mechanic.sensory_hearing<>NEW.sensory_hearing
    OR mechanic.snapshot_only<>NEW.snapshot_only THEN
   RAISE EXCEPTION 'Clairvoyant observation does not match activation';
 END IF;
 RETURN NEW;
END; $$;

CREATE TRIGGER cmd_psi_clairvoyant_observation_valid
BEFORE INSERT ON cmd_psi_clairvoyant_observation_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_validate_psi_clairvoyant_observation();

CREATE FUNCTION cmd_reject_psi_clairvoyant_observation_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Clairvoyant observation receipts are immutable'; END; $$;

CREATE TRIGGER cmd_psi_clairvoyant_observation_immutable
BEFORE UPDATE OR DELETE ON cmd_psi_clairvoyant_observation_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_psi_clairvoyant_observation_mutation();

COMMENT ON TABLE rule_psi_clairvoyance_power IS
    'CE-PSI-004 paired-source sensory and Effect dependencies without invented thresholds.';
COMMENT ON TABLE cmd_psi_clairvoyant_observation_receipt IS
    'Immutable campaign observation; Referee text is outcome evidence, not mechanical authority.';
