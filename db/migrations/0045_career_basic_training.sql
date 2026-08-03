ALTER TABLE actor_career_stint
    ADD COLUMN basic_training_completed boolean NOT NULL DEFAULT false;

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
        'recover_psionic_strength', 'set_telepathic_shield',
        'attempt_career_entry', 'resolve_failed_career_entry',
        'apply_career_basic_training'
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
        'psionic_strength_recovered', 'psionic_strength_unchanged',
        'telepathic_shield_raised', 'telepathic_shield_lowered',
        'career_entry_qualified', 'career_entry_failed',
        'career_entry_fallback_resolved', 'career_basic_training_applied'
    )
);

CREATE TABLE cmd_career_basic_training_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    career_stint_id bigint NOT NULL UNIQUE REFERENCES actor_career_stint(
        career_stint_id
    ),
    actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    career_rule_id bigint NOT NULL REFERENCES rule_career(career_rule_id),
    first_career boolean NOT NULL,
    selected_training_entry_id bigint REFERENCES rule_career_training_entry(
        career_training_entry_id
    ),
    CHECK (
        (first_career AND selected_training_entry_id IS NULL)
        OR (NOT first_career AND selected_training_entry_id IS NOT NULL)
    )
);

CREATE TABLE cmd_career_basic_training_grant (
    command_id bigint NOT NULL REFERENCES cmd_career_basic_training_receipt(
        command_id
    ),
    grant_order smallint NOT NULL CHECK (grant_order > 0),
    source_training_entry_id bigint NOT NULL
        REFERENCES rule_career_training_entry(career_training_entry_id),
    granted_skill_rule_id bigint NOT NULL REFERENCES rule_skill(rule_id),
    prior_skill_level smallint,
    resulting_skill_level smallint NOT NULL CHECK (resulting_skill_level >= 0),
    PRIMARY KEY (command_id,grant_order)
);
