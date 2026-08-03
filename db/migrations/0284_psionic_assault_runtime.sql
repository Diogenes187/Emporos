ALTER TABLE actor_personal_condition
    DROP CONSTRAINT actor_personal_condition_unconscious_cause_check,
    DROP CONSTRAINT actor_personal_condition_check,
    DROP CONSTRAINT actor_personal_condition_check1;
ALTER TABLE actor_personal_condition ADD CHECK (
    unconscious_cause IN ('repeated_fatigue','telepathic_assault')
);
ALTER TABLE actor_personal_condition ADD CHECK (
    (fatigued AND fatigue_sequence>0
     AND fatigue_endurance_modifier IS NOT NULL
     AND fatigue_rest_required_hours IS NOT NULL)
    OR
    (NOT fatigued AND fatigue_endurance_modifier IS NULL
     AND fatigue_rest_required_hours IS NULL)
);
ALTER TABLE actor_personal_condition ADD CHECK (
    (unconscious AND unconscious_cause IS NOT NULL)
    OR
    (NOT unconscious AND unconscious_cause IS NULL
     AND unconscious_recovery_failures=0
     AND unconscious_minutes_elapsed=0)
);
ALTER TABLE actor_personal_condition_transition
    DROP CONSTRAINT actor_personal_condition_transition_transition_kind_check;
ALTER TABLE actor_personal_condition_transition ADD CHECK (
    transition_kind IN (
        'fatigue_started','fatigue_repeated_unconscious',
        'fatigue_rest_completed','consciousness_recovered',
        'consciousness_recovery_failed','psi_assault_unconscious'
    )
);
ALTER TABLE cmd_personal_unconscious_recovery_receipt
    DROP CONSTRAINT cmd_personal_unconscious_recovery_receip_remains_fatigued_check;

CREATE TABLE cmd_psi_assault_receipt (
    activation_command_id bigint PRIMARY KEY REFERENCES
        cmd_psionic_activation_receipt(command_id),
    actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    target_actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    effect_snapshot smallint NOT NULL CHECK (effect_snapshot>=0),
    timing_seconds_snapshot smallint NOT NULL CHECK (
        timing_seconds_snapshot>0
    ),
    target_shielded boolean NOT NULL,
    defender_die_one smallint CHECK (defender_die_one BETWEEN 1 AND 6),
    defender_die_two smallint CHECK (defender_die_two BETWEEN 1 AND 6),
    attacker_opposed_total smallint,
    defender_opposed_total smallint,
    shield_penetrated boolean NOT NULL,
    damage_die_one smallint CHECK (damage_die_one BETWEEN 1 AND 6),
    damage_die_two smallint CHECK (damage_die_two BETWEEN 1 AND 6),
    raw_damage smallint NOT NULL CHECK (raw_damage>=0),
    psionic_strength_before smallint CHECK (psionic_strength_before>=0),
    psionic_strength_after smallint CHECK (psionic_strength_after>=0),
    psionic_strength_damage smallint NOT NULL CHECK (
        psionic_strength_damage>=0
    ),
    intelligence_before smallint NOT NULL CHECK (intelligence_before>=0),
    intelligence_after smallint NOT NULL CHECK (intelligence_after>=0),
    intelligence_damage smallint NOT NULL CHECK (intelligence_damage>=0),
    endurance_before smallint NOT NULL CHECK (endurance_before>=0),
    endurance_after smallint NOT NULL CHECK (endurance_after>=0),
    endurance_damage smallint NOT NULL CHECK (endurance_damage>=0),
    rendered_unconscious boolean NOT NULL,
    assaulted_at timestamptz NOT NULL,
    FOREIGN KEY (actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    FOREIGN KEY (target_actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    CHECK (
        (target_shielded
         AND defender_die_one IS NOT NULL AND defender_die_two IS NOT NULL
         AND attacker_opposed_total IS NOT NULL
         AND defender_opposed_total IS NOT NULL
         AND shield_penetrated=(attacker_opposed_total>defender_opposed_total))
        OR
        (NOT target_shielded
         AND defender_die_one IS NULL AND defender_die_two IS NULL
         AND attacker_opposed_total IS NULL
         AND defender_opposed_total IS NULL AND shield_penetrated)
    ),
    CHECK (
        (shield_penetrated
         AND damage_die_one IS NOT NULL AND damage_die_two IS NOT NULL
         AND raw_damage=damage_die_one+damage_die_two+effect_snapshot
         AND rendered_unconscious)
        OR
        (NOT shield_penetrated
         AND damage_die_one IS NULL AND damage_die_two IS NULL
         AND raw_damage=0 AND NOT rendered_unconscious)
    ),
    CHECK (
        (psionic_strength_before IS NULL
         AND psionic_strength_after IS NULL
         AND psionic_strength_damage=0)
        OR
        (psionic_strength_before IS NOT NULL
         AND psionic_strength_after=
             psionic_strength_before-psionic_strength_damage)
    ),
    CHECK (intelligence_after=intelligence_before-intelligence_damage),
    CHECK (endurance_after=endurance_before-endurance_damage),
    CHECK (
        psionic_strength_damage+intelligence_damage+endurance_damage
        <=raw_damage
    )
);

CREATE FUNCTION cmd_validate_psi_assault() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE activation cmd_psionic_activation_receipt%ROWTYPE;
BEGIN
 SELECT * INTO STRICT activation FROM cmd_psionic_activation_receipt
  WHERE command_id=NEW.activation_command_id;
 PERFORM 1 FROM rule_psi_assault
  WHERE power_rule_id=activation.power_rule_id;
 IF NOT activation.succeeded OR activation.actor_id<>NEW.actor_id
    OR activation.target_actor_id<>NEW.target_actor_id
    OR activation.effect<>NEW.effect_snapshot
    OR activation.timing_total<>NEW.timing_seconds_snapshot
    OR activation.timing_unit<>'seconds' THEN
   RAISE EXCEPTION 'Assault receipt does not match activation';
 END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER cmd_psi_assault_valid
BEFORE INSERT ON cmd_psi_assault_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_validate_psi_assault();

CREATE FUNCTION cmd_reject_psi_assault_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Assault receipts are immutable'; END; $$;
CREATE TRIGGER cmd_psi_assault_immutable
BEFORE UPDATE OR DELETE ON cmd_psi_assault_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_psi_assault_mutation();

CREATE OR REPLACE FUNCTION cmd_validate_personal_condition_transition()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE command_type text;
BEGIN
 SELECT command.command_type INTO STRICT command_type
   FROM cmd_command command WHERE command.command_id=NEW.command_id;
 IF (NEW.transition_kind IN (
       'fatigue_started','fatigue_repeated_unconscious')
     AND command_type<>'apply_personal_fatigue')
    OR (NEW.transition_kind='fatigue_rest_completed'
        AND command_type<>'complete_personal_fatigue_rest')
    OR (NEW.transition_kind IN (
          'consciousness_recovered','consciousness_recovery_failed')
        AND command_type<>'resolve_personal_unconscious_recovery')
    OR (NEW.transition_kind='psi_assault_unconscious'
        AND command_type<>'activate_psionic_power')
 THEN
   RAISE EXCEPTION 'Personal-condition transition has wrong command type';
 END IF;
 RETURN NEW;
END; $$;

COMMENT ON TABLE cmd_psi_assault_receipt IS
    'Immutable Assault opposition, damage allocation, and unconsciousness receipt.';
