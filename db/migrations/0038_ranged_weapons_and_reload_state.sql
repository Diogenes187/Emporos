ALTER TABLE inv_weapon_definition
    ADD COLUMN rate_of_fire_text text,
    ADD COLUMN has_recoil boolean;

ALTER TABLE inv_weapon_attack_mode
    ADD COLUMN required_skill_rule_id bigint REFERENCES rule_skill(rule_id);

CREATE TABLE inv_ammunition_definition (
    ammunition_rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    weapon_rule_id bigint NOT NULL REFERENCES inv_weapon_definition(item_rule_id),
    ammunition_code text NOT NULL CHECK (btrim(ammunition_code) <> ''),
    capacity_rounds smallint NOT NULL CHECK (capacity_rounds > 0),
    minimum_tech_level smallint NOT NULL CHECK (minimum_tech_level >= 0),
    cost_credits integer NOT NULL CHECK (cost_credits >= 0),
    mass_grams integer NOT NULL CHECK (mass_grams >= 0),
    reload_procedure text NOT NULL CHECK (
        reload_procedure IN (
            'minor_actions', 'full_rounds', 'recharge_hours', 'unspecified'
        )
    ),
    reload_units smallint CHECK (reload_units > 0),
    CHECK (
        (reload_procedure='unspecified' AND reload_units IS NULL)
        OR (reload_procedure<>'unspecified' AND reload_units IS NOT NULL)
    ),
    UNIQUE (weapon_rule_id, ammunition_code)
);

CREATE TABLE actor_weapon_state (
    actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    weapon_rule_id bigint NOT NULL REFERENCES inv_weapon_definition(item_rule_id),
    ready boolean NOT NULL DEFAULT false,
    loaded_ammunition_rule_id bigint REFERENCES inv_ammunition_definition(
        ammunition_rule_id
    ),
    rounds_loaded smallint NOT NULL DEFAULT 0 CHECK (rounds_loaded >= 0),
    reload_progress smallint NOT NULL DEFAULT 0 CHECK (reload_progress >= 0),
    PRIMARY KEY (actor_id, weapon_rule_id)
);

CREATE TABLE actor_ammunition_supply (
    actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    ammunition_rule_id bigint NOT NULL REFERENCES inv_ammunition_definition(
        ammunition_rule_id
    ),
    reload_units_available smallint NOT NULL DEFAULT 0 CHECK (
        reload_units_available >= 0
    ),
    PRIMARY KEY (actor_id, ammunition_rule_id)
);

ALTER TABLE enc_personal_attack
    ADD COLUMN ammunition_consumed smallint NOT NULL DEFAULT 0 CHECK (
        ammunition_consumed >= 0
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
        'forfeit_delayed_personal_turn', 'aim_personal_attack',
        'change_personal_stance', 'set_personal_cover',
        'move_personal_combatant', 'aim_personal_attack_for_kill',
        'advance_weapon_reload'
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
        'personal_stance_changed', 'personal_cover_set',
        'personal_combatant_moved', 'personal_attack_kill_aimed',
        'weapon_reload_advanced', 'weapon_reloaded'
    )
);

CREATE TABLE cmd_weapon_reload_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    encounter_id bigint NOT NULL REFERENCES enc_personal_combat(encounter_id),
    actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    weapon_rule_id bigint NOT NULL REFERENCES inv_weapon_definition(item_rule_id),
    ammunition_rule_id bigint NOT NULL REFERENCES inv_ammunition_definition(
        ammunition_rule_id
    ),
    round_number integer NOT NULL CHECK (round_number > 0),
    reload_procedure text NOT NULL,
    progress_before smallint NOT NULL CHECK (progress_before >= 0),
    progress_after smallint NOT NULL CHECK (progress_after >= 0),
    completed boolean NOT NULL,
    rounds_loaded_after smallint NOT NULL CHECK (rounds_loaded_after >= 0),
    reload_units_available_after smallint NOT NULL CHECK (
        reload_units_available_after >= 0
    )
);
