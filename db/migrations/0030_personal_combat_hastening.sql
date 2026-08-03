CREATE TABLE rule_personal_hasten (
    rule_id             bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    initiative_modifier integer NOT NULL,
    check_modifier      integer NOT NULL,
    maximum_per_round   smallint NOT NULL CHECK (maximum_per_round > 0),
    lasts_current_round_only boolean NOT NULL,
    declared_at_round_start boolean NOT NULL
);

ALTER TABLE enc_personal_combatant
    ADD COLUMN hastened_this_round boolean NOT NULL DEFAULT false,
    ADD COLUMN hasten_check_modifier integer NOT NULL DEFAULT 0;

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
        'advance_personal_combat_round', 'declare_personal_attack',
        'begin_personal_turn', 'hasten_personal_combatant'
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
        'personal_combat_round_advanced', 'personal_attack_declared',
        'personal_turn_begun', 'personal_combatant_hastened'
    )
);

CREATE TABLE cmd_personal_hasten_receipt (
    command_id          bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    encounter_id        bigint NOT NULL REFERENCES enc_personal_combat(encounter_id),
    actor_id            bigint NOT NULL REFERENCES actor_actor(actor_id),
    round_number        integer NOT NULL CHECK (round_number > 0),
    initiative_before   integer NOT NULL,
    initiative_after    integer NOT NULL,
    check_modifier      integer NOT NULL,
    FOREIGN KEY (encounter_id, actor_id)
        REFERENCES enc_personal_combatant(encounter_id, actor_id),
    UNIQUE (encounter_id, actor_id, round_number)
);
