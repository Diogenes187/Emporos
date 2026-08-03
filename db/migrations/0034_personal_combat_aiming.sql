CREATE TABLE rule_personal_aim (
    rule_id             bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    minor_actions_per_step smallint NOT NULL CHECK (minor_actions_per_step > 0),
    modifier_per_step   integer NOT NULL,
    maximum_modifier    integer NOT NULL CHECK (maximum_modifier > 0),
    requires_same_target boolean NOT NULL,
    lost_on_other_action boolean NOT NULL
);

ALTER TABLE enc_personal_combatant
    ADD COLUMN aim_target_actor_id bigint REFERENCES actor_actor(actor_id),
    ADD COLUMN aim_modifier integer NOT NULL DEFAULT 0 CHECK (
        aim_modifier BETWEEN 0 AND 6
    ),
    ADD CONSTRAINT enc_personal_combatant_aim_pair_check CHECK (
        (aim_target_actor_id IS NULL AND aim_modifier = 0)
        OR (aim_target_actor_id IS NOT NULL AND aim_modifier > 0)
    );

ALTER TABLE enc_personal_attack
    ADD COLUMN aim_modifier integer NOT NULL DEFAULT 0 CHECK (
        aim_modifier BETWEEN 0 AND 6
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
        'advance_personal_combat_round', 'declare_personal_attack',
        'begin_personal_turn', 'hasten_personal_combatant',
        'delay_personal_turn', 'resume_delayed_personal_turn',
        'forfeit_delayed_personal_turn', 'aim_personal_attack'
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
        'delayed_personal_turn_forfeited', 'personal_attack_aimed'
    )
);

CREATE TABLE cmd_personal_aim_receipt (
    command_id          bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    encounter_id        bigint NOT NULL REFERENCES enc_personal_combat(encounter_id),
    actor_id            bigint NOT NULL REFERENCES actor_actor(actor_id),
    target_actor_id     bigint NOT NULL REFERENCES actor_actor(actor_id),
    round_number        integer NOT NULL CHECK (round_number > 0),
    minor_actions_before smallint NOT NULL CHECK (minor_actions_before > 0),
    minor_actions_after smallint NOT NULL CHECK (minor_actions_after >= 0),
    aim_modifier_before integer NOT NULL CHECK (aim_modifier_before >= 0),
    aim_modifier_after  integer NOT NULL CHECK (aim_modifier_after > 0),
    FOREIGN KEY (encounter_id, actor_id)
        REFERENCES enc_personal_combatant(encounter_id, actor_id)
);
