CREATE TABLE rule_personal_stance (
    rule_id             bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    stance_code         text NOT NULL UNIQUE CHECK (
                            stance_code IN ('standing', 'crouched', 'prone')
                        ),
    display_order       smallint NOT NULL UNIQUE CHECK (display_order > 0),
    cover_step_bonus    smallint NOT NULL CHECK (cover_step_bonus >= 0),
    may_dodge           boolean NOT NULL,
    may_make_melee_attack boolean NOT NULL,
    ranged_dm_personal  integer NOT NULL,
    ranged_dm_medium_or_greater integer NOT NULL
);

CREATE TABLE rule_personal_cover (
    rule_id             bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    cover_code          text NOT NULL UNIQUE CHECK (
                            cover_code IN (
                                'one_quarter', 'one_half',
                                'three_quarters', 'full'
                            )
                        ),
    display_order       smallint NOT NULL UNIQUE CHECK (display_order > 0),
    attack_modifier     integer NOT NULL
);

ALTER TABLE enc_personal_combatant
    ADD COLUMN stance_rule_id bigint REFERENCES rule_personal_stance(rule_id),
    ADD COLUMN cover_rule_id bigint REFERENCES rule_personal_cover(rule_id);

ALTER TABLE enc_personal_attack
    ADD COLUMN cover_modifier integer NOT NULL DEFAULT 0,
    ADD COLUMN stance_modifier integer NOT NULL DEFAULT 0;

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
        'forfeit_delayed_personal_turn', 'aim_personal_attack',
        'change_personal_stance', 'set_personal_cover'
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
        'delayed_personal_turn_forfeited', 'personal_attack_aimed',
        'personal_stance_changed', 'personal_cover_set'
    )
);

CREATE TABLE cmd_personal_stance_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    encounter_id bigint NOT NULL REFERENCES enc_personal_combat(encounter_id),
    actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    round_number integer NOT NULL CHECK (round_number > 0),
    stance_before_rule_id bigint NOT NULL REFERENCES rule_personal_stance(rule_id),
    stance_after_rule_id bigint NOT NULL REFERENCES rule_personal_stance(rule_id),
    minor_actions_before smallint NOT NULL CHECK (minor_actions_before > 0),
    minor_actions_after smallint NOT NULL CHECK (minor_actions_after >= 0)
);

CREATE TABLE cmd_personal_cover_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    encounter_id bigint NOT NULL REFERENCES enc_personal_combat(encounter_id),
    actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    round_number integer NOT NULL CHECK (round_number > 0),
    cover_before_rule_id bigint REFERENCES rule_personal_cover(rule_id),
    cover_after_rule_id bigint REFERENCES rule_personal_cover(rule_id)
);
