CREATE TABLE rule_career_medical_coverage (
    career_rule_id bigint PRIMARY KEY REFERENCES rule_career(career_rule_id),
    percent_at_4 smallint NOT NULL CHECK (percent_at_4 BETWEEN 0 AND 100),
    percent_at_8 smallint NOT NULL CHECK (percent_at_8 BETWEEN 0 AND 100),
    percent_at_12 smallint NOT NULL CHECK (percent_at_12 BETWEEN 0 AND 100),
    CHECK (percent_at_4 <= percent_at_8 AND percent_at_8 <= percent_at_12)
);

INSERT INTO rule_career_medical_coverage
    (career_rule_id,percent_at_4,percent_at_8,percent_at_12)
SELECT career_rule_id,75,100,100 FROM rule_career
WHERE career_code IN (
    'aerospace-defense','marine','maritime-defense','navy','scout',
    'surface-defense'
);

INSERT INTO rule_career_medical_coverage
    (career_rule_id,percent_at_4,percent_at_8,percent_at_12)
SELECT career_rule_id,50,75,100 FROM rule_career
WHERE career_code IN (
    'agent','athlete','bureaucrat','diplomat','entertainer','hunter',
    'mercenary','merchant','noble','physician','pirate','scientist',
    'technician'
);

INSERT INTO rule_career_medical_coverage
    (career_rule_id,percent_at_4,percent_at_8,percent_at_12)
SELECT career_rule_id,0,50,75 FROM rule_career
WHERE career_code IN ('barbarian','belter','colonist','drifter','rogue');

ALTER TABLE actor_financial_state
    ADD COLUMN medical_debt_credits bigint NOT NULL DEFAULT 0 CHECK (
        medical_debt_credits >= 0 AND medical_debt_credits <= debt_credits
    );

CREATE TABLE actor_career_medical_care (
    career_medical_care_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    injury_result_id bigint NOT NULL UNIQUE REFERENCES actor_career_injury_result(
        injury_result_id
    ),
    decision text NOT NULL CHECK (decision IN ('purchase','decline')),
    employer_roll_total smallint,
    employer_coverage_percent smallint NOT NULL CHECK (
        employer_coverage_percent BETWEEN 0 AND 100
    ),
    gross_cost_credits integer NOT NULL CHECK (gross_cost_credits >= 0),
    employer_paid_credits integer NOT NULL CHECK (employer_paid_credits >= 0),
    character_cost_credits integer NOT NULL CHECK (character_cost_credits >= 0),
    medical_debt_before bigint NOT NULL CHECK (medical_debt_before >= 0),
    medical_debt_after bigint NOT NULL CHECK (medical_debt_after >= 0),
    CHECK (
        gross_cost_credits=employer_paid_credits+character_cost_credits
        AND medical_debt_after=medical_debt_before+character_cost_credits
        AND (
            (
                decision='decline' AND employer_roll_total IS NULL
                AND employer_coverage_percent=0 AND gross_cost_credits=0
            )
            OR
            (
                decision='purchase' AND employer_roll_total IS NOT NULL
                AND gross_cost_credits > 0
            )
        )
    )
);

CREATE TABLE actor_career_medical_restoration (
    career_medical_care_id bigint NOT NULL REFERENCES actor_career_medical_care(
        career_medical_care_id
    ),
    restoration_order smallint NOT NULL CHECK (restoration_order > 0),
    characteristic_rule_id bigint NOT NULL REFERENCES rule_characteristic(
        rule_id
    ),
    points_restored smallint NOT NULL CHECK (points_restored > 0),
    prior_maximum_value smallint NOT NULL CHECK (prior_maximum_value >= 0),
    prior_current_value smallint NOT NULL CHECK (prior_current_value >= 0),
    resulting_maximum_value smallint NOT NULL CHECK (
        resulting_maximum_value >= prior_maximum_value
    ),
    resulting_current_value smallint NOT NULL CHECK (
        resulting_current_value >= prior_current_value
    ),
    PRIMARY KEY (career_medical_care_id,restoration_order),
    UNIQUE (career_medical_care_id,characteristic_rule_id)
);

CREATE TABLE cmd_career_medical_care_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    career_medical_care_id bigint NOT NULL UNIQUE
        REFERENCES actor_career_medical_care(career_medical_care_id)
);

ALTER TABLE actor_career_benefit_roll
    ADD COLUMN medical_debt_paid bigint NOT NULL DEFAULT 0 CHECK (
        medical_debt_paid >= 0
    ),
    ADD COLUMN cash_retained bigint NOT NULL DEFAULT 0 CHECK (
        cash_retained >= 0
    );

UPDATE actor_career_benefit_roll
SET cash_retained=cash_awarded
WHERE cash_awarded > 0;

ALTER TABLE actor_career_benefit_roll
    ADD CONSTRAINT actor_career_benefit_cash_distribution_check CHECK (
        cash_awarded=medical_debt_paid+cash_retained
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
        'resolve_aging_crisis', 'resolve_career_medical_care'
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
        'career_medical_employer'
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
        'career_departure_chosen', 'career_muster_initialized',
        'career_pension_awarded', 'career_benefit_awarded',
        'career_weapon_benefit_choice_required',
        'career_weapon_item_awarded', 'career_weapon_skill_awarded',
        'character_creation_completed',
        'aging_crisis_cost_determined', 'aging_crisis_paid',
        'aging_crisis_death_accepted', 'career_medical_care_declined',
        'career_medical_care_purchased'
    )
);
