ALTER TABLE cmd_command DROP CONSTRAINT cmd_command_command_type_check;
ALTER TABLE cmd_command ADD CONSTRAINT cmd_command_command_type_check CHECK (
    command_type IN (
        'resolve_personal_attack', 'apply_personal_damage',
        'create_encounter', 'transition_encounter_mode',
        'add_encounter_participant', 'set_encounter_attitude',
        'attempt_attitude_influence', 'set_animal_reaction_context',
        'resolve_animal_reaction', 'check_starship_encounter',
        'initialize_personal_combat', 'spend_personal_action',
        'declare_personal_reaction'
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
        'personal_reaction_declared'
    )
);

CREATE TABLE cmd_personal_action_receipt (
    command_id          bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    encounter_id        bigint NOT NULL REFERENCES enc_personal_combat(encounter_id),
    actor_id            bigint NOT NULL REFERENCES actor_actor(actor_id),
    round_number        integer NOT NULL CHECK (round_number > 0),
    action_operation    text NOT NULL CHECK (
                            action_operation IN (
                                'spend_significant', 'spend_minor',
                                'convert_significant'
                            )
                        ),
    significant_before smallint NOT NULL CHECK (significant_before >= 0),
    significant_after  smallint NOT NULL CHECK (significant_after >= 0),
    minor_before       smallint NOT NULL CHECK (minor_before >= 0),
    minor_after        smallint NOT NULL CHECK (minor_after >= 0),
    FOREIGN KEY (encounter_id, actor_id)
        REFERENCES enc_personal_combatant(encounter_id, actor_id)
);

CREATE TABLE cmd_personal_reaction_receipt (
    command_id          bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    encounter_id        bigint NOT NULL REFERENCES enc_personal_combat(encounter_id),
    actor_id            bigint NOT NULL REFERENCES actor_actor(actor_id),
    round_number        integer NOT NULL CHECK (round_number > 0),
    attack_trigger_reference text NOT NULL CHECK (
                            btrim(attack_trigger_reference) <> ''
                        ),
    reaction_kind       text NOT NULL CHECK (
                            reaction_kind IN ('dodge', 'dodge_with_cover', 'parry')
                        ),
    reactions_before    smallint NOT NULL CHECK (reactions_before >= 0),
    reactions_after     smallint NOT NULL CHECK (reactions_after > 0),
    initiative_before   integer NOT NULL,
    initiative_after    integer NOT NULL,
    check_modifier_before integer NOT NULL,
    check_modifier_after integer NOT NULL,
    UNIQUE (encounter_id, actor_id, round_number, attack_trigger_reference),
    FOREIGN KEY (encounter_id, actor_id)
        REFERENCES enc_personal_combatant(encounter_id, actor_id)
);

COMMENT ON COLUMN cmd_personal_reaction_receipt.attack_trigger_reference IS
    'Stable identifier for the unresolved incoming attack; binds at most one reaction by this actor to that attack.';
