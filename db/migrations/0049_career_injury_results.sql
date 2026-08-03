CREATE TABLE rule_career_injury (
    injury_rule_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    roll_value smallint NOT NULL UNIQUE CHECK (roll_value BETWEEN 1 AND 6),
    outcome_code text NOT NULL UNIQUE,
    outcome_text text NOT NULL CHECK (btrim(outcome_text) <> ''),
    reduction_kind text NOT NULL CHECK (
        reduction_kind IN (
            'one_physical_d6_and_others',
            'one_physical_d6', 'strength_or_dexterity_two',
            'one_physical_two', 'one_physical_one', 'none'
        )
    )
);

INSERT INTO rule_career_injury
    (roll_value,outcome_code,outcome_text,reduction_kind)
VALUES
    (1,'nearly_killed','Nearly killed.',
     'one_physical_d6_and_others'),
    (2,'severely_injured','Severely injured.','one_physical_d6'),
    (3,'missing_eye_or_limb','Missing eye or limb.',
     'strength_or_dexterity_two'),
    (4,'scarred','Scarred and injured.','one_physical_two'),
    (5,'injured','Injured.','one_physical_one'),
    (6,'lightly_injured','Lightly injured.','none');

CREATE TABLE actor_career_injury_result (
    injury_result_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    injury_requirement_id bigint NOT NULL UNIQUE
        REFERENCES actor_career_injury_requirement(injury_requirement_id),
    injury_rule_id bigint NOT NULL REFERENCES rule_career_injury(
        injury_rule_id
    ),
    determination_kind text NOT NULL CHECK (
        determination_kind IN ('fixed_two','roll_once','roll_twice_lower')
    ),
    consequence_status text NOT NULL DEFAULT 'awaiting_application' CHECK (
        consequence_status IN (
            'awaiting_application','applied','awaiting_crisis','resolved'
        )
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
        'recover_psionic_strength', 'set_telepathic_shield',
        'attempt_career_entry', 'resolve_failed_career_entry',
        'apply_career_basic_training', 'attempt_career_survival',
        'apply_career_rank_zero_award', 'resolve_survival_mishap',
        'determine_career_injury'
    )
);

ALTER TABLE cmd_random_draw DROP CONSTRAINT cmd_random_draw_draw_group_check;
ALTER TABLE cmd_random_draw ADD CONSTRAINT cmd_random_draw_draw_group_check CHECK (
    draw_group IN (
        'attack', 'damage', 'task', 'occurrence', 'encounter_type',
        'initiative', 'psionic_activation', 'psionic_timing',
        'career_qualification', 'career_draft', 'career_survival',
        'career_mishap', 'career_injury'
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
        'career_entry_fallback_resolved', 'career_basic_training_applied',
        'career_survival_passed', 'career_survival_failed',
        'career_rank_zero_award_applied', 'survival_mishap_resolved',
        'career_injury_determined'
    )
);

CREATE TABLE cmd_career_injury_determination_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    injury_result_id bigint NOT NULL UNIQUE REFERENCES actor_career_injury_result(
        injury_result_id
    )
);
