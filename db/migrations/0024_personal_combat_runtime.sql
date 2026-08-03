CREATE TABLE enc_personal_combat (
    encounter_id        bigint PRIMARY KEY REFERENCES enc_encounter(encounter_id),
    current_round       integer NOT NULL DEFAULT 1 CHECK (current_round > 0),
    combat_status       text NOT NULL DEFAULT 'active' CHECK (
                            combat_status IN ('active', 'completed')
                        ),
    round_started_at    timestamptz NOT NULL DEFAULT clock_timestamp(),
    completed_at        timestamptz
);

CREATE TABLE enc_personal_combatant (
    encounter_id        bigint NOT NULL REFERENCES enc_personal_combat(encounter_id),
    actor_id            bigint NOT NULL REFERENCES actor_actor(actor_id),
    aware_at_start      boolean NOT NULL,
    initiative_method   text NOT NULL CHECK (
                            initiative_method IN ('rolled', 'automatic_12')
                        ),
    dexterity_value     smallint NOT NULL CHECK (dexterity_value >= 0),
    dexterity_modifier  integer NOT NULL,
    initiative_base     integer NOT NULL,
    initiative_current  integer NOT NULL,
    significant_actions_remaining smallint NOT NULL CHECK (
                            significant_actions_remaining >= 0
                        ),
    minor_actions_remaining smallint NOT NULL CHECK (
                            minor_actions_remaining >= 0
                        ),
    significant_converted boolean NOT NULL DEFAULT false,
    reactions_this_round smallint NOT NULL DEFAULT 0 CHECK (
                            reactions_this_round >= 0
                        ),
    reaction_check_modifier integer NOT NULL DEFAULT 0,
    PRIMARY KEY (encounter_id, actor_id),
    FOREIGN KEY (encounter_id, actor_id)
        REFERENCES enc_participant(encounter_id, actor_id)
);

ALTER TABLE cmd_command DROP CONSTRAINT cmd_command_command_type_check;
ALTER TABLE cmd_command ADD CONSTRAINT cmd_command_command_type_check CHECK (
    command_type IN (
        'resolve_personal_attack', 'apply_personal_damage',
        'create_encounter', 'transition_encounter_mode',
        'add_encounter_participant', 'set_encounter_attitude',
        'attempt_attitude_influence', 'set_animal_reaction_context',
        'resolve_animal_reaction', 'check_starship_encounter',
        'initialize_personal_combat'
    )
);

ALTER TABLE cmd_random_draw DROP CONSTRAINT cmd_random_draw_draw_group_check;
ALTER TABLE cmd_random_draw ADD CONSTRAINT cmd_random_draw_draw_group_check CHECK (
    draw_group IN (
        'attack', 'damage', 'task', 'occurrence', 'encounter_type',
        'initiative'
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
        'starship_contact_created', 'personal_combat_initialized'
    )
);

CREATE TABLE cmd_combat_initialization_receipt (
    command_id          bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    encounter_id        bigint NOT NULL UNIQUE REFERENCES enc_personal_combat(encounter_id),
    round_number        integer NOT NULL CHECK (round_number = 1),
    combatant_count     integer NOT NULL CHECK (combatant_count > 1)
);

CREATE TABLE cmd_combat_initialization_combatant (
    command_id          bigint NOT NULL
                        REFERENCES cmd_combat_initialization_receipt(command_id),
    actor_id            bigint NOT NULL REFERENCES actor_actor(actor_id),
    initiative_method   text NOT NULL,
    first_draw_order    smallint,
    draw_count          smallint NOT NULL CHECK (draw_count >= 0),
    initiative_base     integer NOT NULL,
    PRIMARY KEY (command_id, actor_id),
    CHECK (
        (initiative_method = 'rolled' AND first_draw_order IS NOT NULL
         AND draw_count > 0)
        OR (initiative_method = 'automatic_12'
            AND first_draw_order IS NULL AND draw_count = 0)
    )
);

COMMENT ON TABLE enc_personal_combatant IS
    'Current round initiative, actions, and reaction burden for one combatant.';
