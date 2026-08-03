CREATE TABLE rule_psi_telempathy (
    power_rule_id bigint PRIMARY KEY REFERENCES psi_power(power_rule_id),
    reads_emotions boolean NOT NULL CHECK (reads_emotions),
    projects_emotions boolean NOT NULL CHECK (projects_emotions),
    effect_controls_projected_strength boolean NOT NULL CHECK (
        effect_controls_projected_strength
    ),
    target_behavior_not_guaranteed boolean NOT NULL CHECK (
        target_behavior_not_guaranteed
    ),
    telepaths_recognize_emotional_influence boolean NOT NULL CHECK (
        telepaths_recognize_emotional_influence
    ),
    nontelepaths_do_not_recognize_source boolean NOT NULL CHECK (
        nontelepaths_do_not_recognize_source
    ),
    shield_grants_immunity boolean NOT NULL CHECK (shield_grants_immunity)
);

CREATE TABLE cmd_psi_telempathy_receipt (
    activation_command_id bigint PRIMARY KEY REFERENCES
        cmd_psionic_activation_receipt(command_id),
    actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    target_actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    operation text NOT NULL CHECK (
        operation IN ('read','project','read_and_project')
    ),
    effect_snapshot smallint NOT NULL,
    timing_rounds_snapshot smallint NOT NULL CHECK (
        timing_rounds_snapshot>0
    ),
    projected_emotion text,
    perceived_emotions text,
    target_recognized_influence boolean NOT NULL,
    referee_outcome text NOT NULL CHECK (btrim(referee_outcome)<>''),
    behavior_not_guaranteed boolean NOT NULL CHECK (
        behavior_not_guaranteed
    ),
    resolved_at timestamptz NOT NULL,
    FOREIGN KEY (actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    FOREIGN KEY (target_actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    CHECK (
        (operation='read' AND projected_emotion IS NULL
         AND perceived_emotions IS NOT NULL
         AND btrim(perceived_emotions)<>'')
        OR
        (operation='project' AND projected_emotion IS NOT NULL
         AND btrim(projected_emotion)<>''
         AND perceived_emotions IS NULL)
        OR
        (operation='read_and_project'
         AND projected_emotion IS NOT NULL
         AND btrim(projected_emotion)<>''
         AND perceived_emotions IS NOT NULL
         AND btrim(perceived_emotions)<>'')
    )
);

CREATE FUNCTION cmd_validate_psi_telempathy()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE activation cmd_psionic_activation_receipt%ROWTYPE;
DECLARE target_is_telepath boolean;
DECLARE expected_recognition boolean;
BEGIN
 SELECT * INTO STRICT activation FROM cmd_psionic_activation_receipt
  WHERE command_id=NEW.activation_command_id;
 PERFORM 1 FROM rule_psi_telempathy
  WHERE power_rule_id=activation.power_rule_id;
 SELECT EXISTS (
          SELECT 1 FROM actor_skill skill
          JOIN rule_rule rule ON rule.rule_id=skill.skill_rule_id
           AND rule.rule_code='skill.psionic-telepathy'
          WHERE skill.actor_id=NEW.target_actor_id
        ) INTO target_is_telepath;
 expected_recognition :=
   target_is_telepath AND NEW.operation IN ('project','read_and_project');
 IF NOT activation.succeeded OR activation.actor_id<>NEW.actor_id
    OR activation.target_actor_id<>NEW.target_actor_id
    OR activation.effect<>NEW.effect_snapshot
    OR activation.timing_total<>NEW.timing_rounds_snapshot
    OR activation.timing_unit<>'rounds'
    OR NEW.target_recognized_influence<>expected_recognition THEN
   RAISE EXCEPTION 'Telempathy receipt does not match activation';
 END IF;
 RETURN NEW;
END; $$;

CREATE TRIGGER cmd_psi_telempathy_valid
BEFORE INSERT ON cmd_psi_telempathy_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_validate_psi_telempathy();

CREATE FUNCTION cmd_reject_psi_telempathy_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Telempathy receipts are immutable'; END; $$;

CREATE TRIGGER cmd_psi_telempathy_immutable
BEFORE UPDATE OR DELETE ON cmd_psi_telempathy_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_psi_telempathy_mutation();

COMMENT ON TABLE rule_psi_telempathy IS
    'CE-PSI-009 paired-source emotional reading, projection, and recognition.';
COMMENT ON TABLE cmd_psi_telempathy_receipt IS
    'Immutable targeted Telempathy evidence without guaranteed behavior.';
