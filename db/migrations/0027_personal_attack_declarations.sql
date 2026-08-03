CREATE TABLE rule_personal_attack_sequence (
    rule_id             bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    consumes_significant_action boolean NOT NULL,
    target_declared_before_reaction boolean NOT NULL,
    reaction_before_attack_check boolean NOT NULL,
    damage_after_successful_check boolean NOT NULL
);

ALTER TABLE cmd_command DROP CONSTRAINT cmd_command_command_type_check;
ALTER TABLE cmd_command ADD CONSTRAINT cmd_command_command_type_check CHECK (
    command_type IN (
        'resolve_personal_attack', 'apply_personal_damage',
        'create_encounter', 'transition_encounter_mode',
        'add_encounter_participant', 'set_encounter_attitude',
        'attempt_attitude_influence', 'set_animal_reaction_context',
        'resolve_animal_reaction', 'check_starship_encounter',
        'initialize_personal_combat', 'spend_personal_action',
        'declare_personal_reaction', 'complete_personal_turn',
        'advance_personal_combat_round', 'declare_personal_attack'
    )
);

ALTER TABLE cmd_domain_event DROP CONSTRAINT cmd_domain_event_event_type_check;
ALTER TABLE cmd_domain_event ADD CONSTRAINT cmd_domain_event_event_type_check CHECK (
    event_type IN (
        'personal_attack_hit', 'personal_attack_missed',
        'personal_damage_applied', 'encounter_created',
        'encounter_mode_transitioned', 'encounter_participant_added',
        'encounter_attitude_set', 'encounter_attitude_changed',
        'encounter_attitude_unchanged', 'animal_reaction_context_set',
        'animal_reaction_resolved', 'starship_encounter_checked',
        'starship_contact_created', 'personal_combat_initialized',
        'personal_action_spent', 'personal_action_converted',
        'personal_reaction_declared', 'personal_turn_completed',
        'personal_combat_round_advanced', 'personal_attack_declared'
    )
);

CREATE TABLE enc_personal_attack (
    personal_attack_id  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id           uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    encounter_id        bigint NOT NULL REFERENCES enc_personal_combat(encounter_id),
    round_number        integer NOT NULL CHECK (round_number > 0),
    attacker_actor_id   bigint NOT NULL REFERENCES actor_actor(actor_id),
    target_actor_id     bigint NOT NULL REFERENCES actor_actor(actor_id),
    weapon_rule_id      bigint NOT NULL REFERENCES inv_weapon_definition(item_rule_id),
    attack_profile_code text NOT NULL REFERENCES combat_attack_profile,
    range_band_rule_id  bigint NOT NULL REFERENCES combat_range_band(rule_id),
    target_has_cover    boolean NOT NULL,
    attack_status       text NOT NULL DEFAULT 'awaiting_reactions' CHECK (
                            attack_status IN (
                                'awaiting_reactions', 'resolved', 'cancelled'
                            )
                        ),
    declared_at         timestamptz NOT NULL DEFAULT clock_timestamp(),
    resolved_at         timestamptz,
    CHECK (attacker_actor_id <> target_actor_id),
    FOREIGN KEY (encounter_id, attacker_actor_id)
        REFERENCES enc_personal_combatant(encounter_id, actor_id),
    FOREIGN KEY (encounter_id, target_actor_id)
        REFERENCES enc_personal_combatant(encounter_id, actor_id)
);

CREATE TABLE cmd_personal_attack_declaration_receipt (
    command_id          bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    personal_attack_id  bigint NOT NULL UNIQUE
                        REFERENCES enc_personal_attack(personal_attack_id),
    significant_before smallint NOT NULL CHECK (significant_before > 0),
    significant_after  smallint NOT NULL CHECK (significant_after >= 0)
);

ALTER TABLE cmd_personal_reaction_receipt
    ADD COLUMN personal_attack_id bigint
        REFERENCES enc_personal_attack(personal_attack_id);

CREATE UNIQUE INDEX cmd_personal_reaction_one_per_declared_attack
    ON cmd_personal_reaction_receipt(personal_attack_id, actor_id)
    WHERE personal_attack_id IS NOT NULL;

COMMENT ON TABLE enc_personal_attack IS
    'Declared attack awaiting defender reactions before its mechanical check.';
