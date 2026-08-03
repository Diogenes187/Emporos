CREATE TABLE rule_career_aging_effect (
    aging_effect_code text PRIMARY KEY,
    maximum_table_result smallint NOT NULL UNIQUE,
    physical_reduction_pattern text NOT NULL CHECK (
        physical_reduction_pattern IN (
            'two_two_two','two_two_one','two_one_one',
            'one_one_one','one_one','one','none'
        )
    ),
    mental_reduction_amount smallint NOT NULL DEFAULT 0
        CHECK (mental_reduction_amount BETWEEN 0 AND 1),
    source_effect_text text NOT NULL CHECK (btrim(source_effect_text) <> '')
);

INSERT INTO rule_career_aging_effect VALUES
    ('minus_six_or_less',-6,'two_two_two',1,
     'Reduce three physical characteristics by 2 and one mental by 1.'),
    ('minus_five',-5,'two_two_two',0,
     'Reduce three physical characteristics by 2.'),
    ('minus_four',-4,'two_two_one',0,
     'Reduce two physical characteristics by 2 and one by 1.'),
    ('minus_three',-3,'two_one_one',0,
     'Reduce one physical characteristic by 2 and two by 1.'),
    ('minus_two',-2,'one_one_one',0,
     'Reduce three physical characteristics by 1.'),
    ('minus_one',-1,'one_one',0,
     'Reduce two physical characteristics by 1.'),
    ('zero',0,'one',0,'Reduce one physical characteristic by 1.'),
    ('one_or_more',32767,'none',0,'No effect.');

CREATE TABLE actor_career_aging (
    career_aging_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    career_term_id bigint NOT NULL UNIQUE REFERENCES actor_career_term(
        career_term_id
    ),
    aging_effect_code text NOT NULL REFERENCES rule_career_aging_effect(
        aging_effect_code
    ),
    natural_total smallint NOT NULL CHECK (natural_total BETWEEN 2 AND 12),
    term_modifier smallint NOT NULL CHECK (term_modifier <= 0),
    table_result smallint NOT NULL,
    aging_status text NOT NULL CHECK (
        aging_status IN ('no_effect','awaiting_allocation','applied','crisis')
    )
);

CREATE TABLE actor_career_aging_reduction (
    career_aging_id bigint NOT NULL REFERENCES actor_career_aging(
        career_aging_id
    ),
    reduction_order smallint NOT NULL CHECK (reduction_order > 0),
    characteristic_rule_id bigint NOT NULL REFERENCES rule_characteristic(
        rule_id
    ),
    reduction_amount smallint NOT NULL CHECK (reduction_amount > 0),
    prior_maximum_value smallint NOT NULL CHECK (prior_maximum_value >= 0),
    prior_current_value smallint NOT NULL CHECK (prior_current_value >= 0),
    resulting_maximum_value smallint NOT NULL CHECK (
        resulting_maximum_value >= 0
    ),
    resulting_current_value smallint NOT NULL CHECK (
        resulting_current_value >= 0
    ),
    PRIMARY KEY (career_aging_id,reduction_order),
    UNIQUE (career_aging_id,characteristic_rule_id)
);

CREATE TABLE cmd_career_aging_determination_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    career_aging_id bigint NOT NULL UNIQUE REFERENCES actor_career_aging(
        career_aging_id
    )
);

CREATE TABLE cmd_career_term_completion_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    career_term_id bigint NOT NULL UNIQUE REFERENCES actor_career_term(
        career_term_id
    ),
    prior_age_years smallint NOT NULL CHECK (prior_age_years > 0),
    resulting_age_years smallint NOT NULL CHECK (
        resulting_age_years > prior_age_years
    ),
    prior_total_terms smallint NOT NULL CHECK (prior_total_terms >= 0),
    resulting_total_terms smallint NOT NULL CHECK (
        resulting_total_terms=prior_total_terms+1
    )
);

CREATE TABLE cmd_career_aging_application_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    career_aging_id bigint NOT NULL UNIQUE REFERENCES actor_career_aging(
        career_aging_id
    ),
    crisis_started boolean NOT NULL
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
        'apply_career_aging'
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
        'career_advancement', 'career_training', 'career_aging'
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
        'career_aging_crisis_started'
    )
);
