ALTER TABLE actor_lifepath_state
    ADD COLUMN retirement_required boolean NOT NULL DEFAULT false;

CREATE TABLE actor_career_reenlistment (
    career_reenlistment_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    career_term_id bigint NOT NULL UNIQUE REFERENCES actor_career_term(
        career_term_id
    ),
    target_number smallint NOT NULL CHECK (target_number > 0),
    natural_total smallint NOT NULL CHECK (natural_total BETWEEN 2 AND 12),
    total_terms_snapshot smallint NOT NULL CHECK (total_terms_snapshot > 0),
    outcome text NOT NULL CHECK (
        outcome IN (
            'forced_continue_natural_12', 'forced_leave_failed',
            'mandatory_retirement', 'choice_available'
        )
    ),
    decision_status text NOT NULL CHECK (
        decision_status IN ('awaiting_choice','resolved')
    ),
    continuation boolean,
    retirement_required boolean NOT NULL DEFAULT false,
    CHECK (
        (
            outcome='choice_available'
            AND NOT retirement_required
            AND (
                (
                    decision_status='awaiting_choice'
                    AND continuation IS NULL
                )
                OR
                (
                    decision_status='resolved'
                    AND continuation IS NOT NULL
                )
            )
        )
        OR
        (
            outcome='forced_continue_natural_12'
            AND decision_status='resolved'
            AND continuation IS TRUE
            AND NOT retirement_required
        )
        OR
        (
            outcome='forced_leave_failed'
            AND decision_status='resolved'
            AND continuation IS FALSE
            AND NOT retirement_required
        )
        OR
        (
            outcome='mandatory_retirement'
            AND decision_status='resolved'
            AND continuation IS FALSE
            AND retirement_required
        )
    )
);

CREATE TABLE cmd_career_reenlistment_determination_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    career_reenlistment_id bigint NOT NULL UNIQUE
        REFERENCES actor_career_reenlistment(career_reenlistment_id)
);

CREATE TABLE cmd_career_reenlistment_decision_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    career_reenlistment_id bigint NOT NULL UNIQUE
        REFERENCES actor_career_reenlistment(career_reenlistment_id),
    selected_continuation boolean NOT NULL
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
        'determine_career_injury', 'apply_career_injury',
        'determine_injury_crisis_cost', 'resolve_injury_crisis',
        'resolve_career_rank_attempt', 'apply_career_term_training',
        'complete_career_term', 'determine_career_aging',
        'apply_career_aging', 'determine_career_reenlistment',
        'decide_career_reenlistment'
    )
);

ALTER TABLE cmd_random_draw DROP CONSTRAINT cmd_random_draw_draw_group_check;
ALTER TABLE cmd_random_draw ADD CONSTRAINT cmd_random_draw_draw_group_check CHECK (
    draw_group IN (
        'attack', 'damage', 'task', 'occurrence', 'encounter_type',
        'initiative', 'psionic_activation', 'psionic_timing',
        'career_qualification', 'career_draft', 'career_survival',
        'career_mishap', 'career_injury', 'career_injury_reduction',
        'career_injury_crisis_cost', 'career_commission',
        'career_advancement', 'career_training', 'career_aging',
        'career_reenlistment'
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
        'delayed_personal_turn_forfeited',
        'personal_attack_aimed', 'personal_stance_changed',
        'personal_cover_set', 'personal_combatant_moved',
        'personal_attack_kill_aimed', 'weapon_reload_advanced',
        'weapon_reloaded', 'psionic_power_activated',
        'psionic_power_failed', 'psionic_strength_recovered',
        'psionic_strength_unchanged', 'telepathic_shield_raised',
        'telepathic_shield_lowered', 'career_entry_qualified',
        'career_entry_failed', 'career_entry_fallback_resolved',
        'career_basic_training_applied', 'career_survival_passed',
        'career_survival_failed', 'career_rank_zero_award_applied',
        'survival_mishap_resolved', 'career_injury_determined',
        'career_injury_applied', 'career_injury_crisis_started',
        'injury_crisis_cost_determined', 'injury_crisis_paid',
        'injury_crisis_death_accepted', 'career_rank_attempt_declined',
        'career_rank_attempt_failed', 'career_rank_gained',
        'career_term_training_applied', 'career_term_completed',
        'career_aging_determined', 'career_aging_applied',
        'career_aging_crisis_started',
        'career_reenlistment_forced_continue',
        'career_reenlistment_forced_departure',
        'career_reenlistment_choice_offered',
        'career_retirement_required', 'career_reenlistment_chosen',
        'career_departure_chosen'
    )
);
