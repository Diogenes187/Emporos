ALTER TABLE actor_financial_state
    ADD COLUMN anagathic_debt_credits bigint NOT NULL DEFAULT 0 CHECK (
        anagathic_debt_credits >= 0
    );

ALTER TABLE actor_financial_state
    ADD CONSTRAINT actor_financial_creation_debt_subsets_check CHECK (
        medical_debt_credits + anagathic_debt_credits <= debt_credits
    );

CREATE TABLE actor_career_anagathic_term (
    career_anagathic_term_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    career_stint_id bigint NOT NULL REFERENCES actor_career_stint(
        career_stint_id
    ),
    career_term_id bigint UNIQUE REFERENCES actor_career_term(career_term_id),
    term_number smallint NOT NULL CHECK (term_number > 0),
    uses_anagathics boolean NOT NULL,
    continuous_course_terms smallint NOT NULL CHECK (
        continuous_course_terms >= 0
    ),
    cost_die smallint,
    cost_credits integer NOT NULL CHECK (cost_credits >= 0),
    declaration_status text NOT NULL CHECK (
        declaration_status IN ('ready','shock_required','resolved')
    ),
    UNIQUE (career_stint_id,term_number),
    CHECK (
        (
            uses_anagathics
            AND continuous_course_terms > 0
            AND cost_die BETWEEN 1 AND 6
            AND cost_credits=cost_die*2500
            AND declaration_status='ready'
        )
        OR
        (
            NOT uses_anagathics
            AND continuous_course_terms=0
            AND cost_die IS NULL
            AND cost_credits=0
        )
    )
);

ALTER TABLE actor_career_term
    ADD COLUMN anagathic_term_id bigint UNIQUE REFERENCES
        actor_career_anagathic_term(career_anagathic_term_id),
    ADD COLUMN second_survival_check_required boolean NOT NULL DEFAULT false,
    ADD COLUMN second_survival_check_total smallint,
    ADD COLUMN second_survival_natural_two boolean,
    ADD COLUMN second_survival_passed boolean,
    ADD CONSTRAINT actor_career_term_second_survival_check CHECK (
        (
            NOT second_survival_check_required
            AND second_survival_check_total IS NULL
            AND second_survival_natural_two IS NULL
            AND second_survival_passed IS NULL
        )
        OR
        (
            second_survival_check_required
            AND second_survival_check_total IS NOT NULL
            AND second_survival_natural_two IS NOT NULL
            AND second_survival_passed IS NOT NULL
        )
    );

ALTER TABLE actor_career_aging
    DROP CONSTRAINT actor_career_aging_term_modifier_check,
    ADD COLUMN anagathic_modifier smallint NOT NULL DEFAULT 0 CHECK (
        anagathic_modifier >= 0
    );

CREATE TABLE cmd_career_anagathic_declaration_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    career_anagathic_term_id bigint NOT NULL UNIQUE REFERENCES
        actor_career_anagathic_term(career_anagathic_term_id)
);

ALTER TABLE actor_career_benefit_roll
    ADD COLUMN anagathic_debt_paid bigint NOT NULL DEFAULT 0 CHECK (
        anagathic_debt_paid >= 0
    );

ALTER TABLE actor_career_benefit_roll
    DROP CONSTRAINT actor_career_benefit_cash_distribution_check,
    ADD CONSTRAINT actor_career_benefit_cash_distribution_check CHECK (
        cash_awarded=medical_debt_paid+anagathic_debt_paid+cash_retained
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
        'decide_career_reenlistment', 'initialize_career_muster',
        'roll_career_benefit', 'resolve_career_weapon_benefit',
        'finish_character_creation', 'determine_aging_crisis_cost',
        'resolve_aging_crisis', 'resolve_career_medical_care',
        'declare_career_anagathics'
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
        'career_reenlistment', 'career_benefit',
        'career_benefit_ship_shares', 'career_aging_crisis_cost',
        'career_medical_employer', 'career_anagathic_cost',
        'career_anagathic_survival'
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
        'career_injury_determined', 'career_injury_applied',
        'career_injury_crisis_started', 'injury_crisis_cost_determined',
        'injury_crisis_paid', 'injury_crisis_death_accepted',
        'career_rank_attempt_declined', 'career_rank_attempt_failed',
        'career_rank_gained', 'career_term_training_applied',
        'career_term_completed', 'career_aging_determined',
        'career_aging_applied', 'career_aging_crisis_started',
        'career_reenlistment_forced_continue',
        'career_reenlistment_forced_departure',
        'career_reenlistment_choice_offered',
        'career_retirement_required', 'career_reenlistment_chosen',
        'career_departure_chosen', 'career_muster_initialized',
        'career_pension_awarded', 'career_benefit_awarded',
        'career_weapon_benefit_choice_required',
        'career_weapon_item_awarded', 'career_weapon_skill_awarded',
        'character_creation_completed', 'aging_crisis_cost_determined',
        'aging_crisis_paid', 'aging_crisis_death_accepted',
        'career_medical_care_declined', 'career_medical_care_purchased',
        'career_anagathics_declared'
    )
);
