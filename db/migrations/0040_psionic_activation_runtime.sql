CREATE TABLE actor_psionic_state (
    actor_id bigint PRIMARY KEY REFERENCES actor_actor(actor_id),
    last_talent_use_at timestamptz,
    next_recovery_at timestamptz,
    CHECK (
        (last_talent_use_at IS NULL AND next_recovery_at IS NULL)
        OR
        (last_talent_use_at IS NOT NULL AND next_recovery_at IS NOT NULL
         AND next_recovery_at >= last_talent_use_at)
    )
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
        'advance_weapon_reload', 'activate_psionic_power',
        'recover_psionic_strength'
    )
);

ALTER TABLE cmd_random_draw DROP CONSTRAINT cmd_random_draw_draw_group_check;
ALTER TABLE cmd_random_draw ADD CONSTRAINT cmd_random_draw_draw_group_check CHECK (
    draw_group IN (
        'attack', 'damage', 'task', 'occurrence', 'encounter_type',
        'initiative', 'psionic_activation', 'psionic_timing'
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
        'weapon_reload_advanced', 'weapon_reloaded',
        'psionic_power_activated', 'psionic_power_failed',
        'psionic_strength_recovered', 'psionic_strength_unchanged'
    )
);

CREATE TABLE cmd_psionic_activation_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    power_rule_id bigint NOT NULL REFERENCES psi_power(power_rule_id),
    range_band_rule_id bigint REFERENCES psi_range_band(range_band_rule_id),
    encounter_id bigint REFERENCES enc_personal_combat(encounter_id),
    round_number integer CHECK (round_number > 0),
    skill_modifier smallint NOT NULL,
    characteristic_modifier smallint NOT NULL,
    difficulty_modifier smallint NOT NULL,
    circumstance_modifier_total smallint NOT NULL,
    check_total smallint NOT NULL,
    target_number smallint NOT NULL,
    effect smallint NOT NULL,
    succeeded boolean NOT NULL,
    variable_points smallint NOT NULL CHECK (variable_points >= 0),
    base_cost smallint NOT NULL CHECK (base_cost >= 0),
    range_cost smallint NOT NULL CHECK (range_cost >= 0),
    psionic_cost smallint NOT NULL CHECK (psionic_cost >= 0),
    psionic_strength_before smallint NOT NULL CHECK (
        psionic_strength_before > 0
    ),
    psionic_strength_after smallint NOT NULL CHECK (
        psionic_strength_after >= 0
    ),
    overexertion_damage smallint NOT NULL CHECK (overexertion_damage >= 0),
    endurance_before smallint NOT NULL CHECK (endurance_before >= 0),
    endurance_after smallint NOT NULL CHECK (endurance_after >= 0),
    timing_total smallint CHECK (timing_total > 0),
    timing_unit text CHECK (timing_unit IN ('seconds','rounds','minutes')),
    significant_actions_before smallint,
    significant_actions_after smallint,
    CHECK (
        (encounter_id IS NULL AND round_number IS NULL
         AND significant_actions_before IS NULL
         AND significant_actions_after IS NULL)
        OR
        (encounter_id IS NOT NULL AND round_number IS NOT NULL
         AND significant_actions_before IS NOT NULL
         AND significant_actions_after IS NOT NULL
         AND significant_actions_after=significant_actions_before-1)
    ),
    CHECK (
        (timing_total IS NULL AND timing_unit IS NULL)
        OR (timing_total IS NOT NULL AND timing_unit IS NOT NULL)
    )
);

CREATE TABLE cmd_psionic_recovery_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    recovered_at timestamptz NOT NULL,
    psionic_strength_before smallint NOT NULL CHECK (
        psionic_strength_before >= 0
    ),
    points_available smallint NOT NULL CHECK (points_available >= 0),
    points_recovered smallint NOT NULL CHECK (points_recovered >= 0),
    psionic_strength_after smallint NOT NULL CHECK (
        psionic_strength_after >= psionic_strength_before
    ),
    next_recovery_at timestamptz
);
