ALTER TABLE enc_personal_combatant
    ADD COLUMN delayed_first_next_round boolean NOT NULL DEFAULT false;

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
        'begin_personal_turn', 'hasten_personal_combatant',
        'delay_personal_turn', 'resume_delayed_personal_turn',
        'forfeit_delayed_personal_turn'
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
        'personal_turn_begun', 'personal_combatant_hastened',
        'personal_turn_delayed', 'delayed_personal_turn_resumed',
        'delayed_personal_turn_forfeited'
    )
);

CREATE TABLE cmd_personal_delay_forfeit_receipt (
    command_id          bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    encounter_id        bigint NOT NULL REFERENCES enc_personal_combat(encounter_id),
    actor_id            bigint NOT NULL REFERENCES actor_actor(actor_id),
    round_number        integer NOT NULL CHECK (round_number > 0),
    initiative_forfeited integer NOT NULL,
    significant_actions_forfeited smallint NOT NULL CHECK (
                            significant_actions_forfeited >= 0
                        ),
    minor_actions_forfeited smallint NOT NULL CHECK (
                            minor_actions_forfeited >= 0
                        ),
    FOREIGN KEY (encounter_id, actor_id)
        REFERENCES enc_personal_combatant(encounter_id, actor_id),
    UNIQUE (encounter_id, actor_id, round_number)
);
