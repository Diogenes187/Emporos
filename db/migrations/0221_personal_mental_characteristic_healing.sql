CREATE TABLE rule_personal_mental_healing (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    points_per_characteristic_per_day integer NOT NULL CHECK (
        points_per_characteristic_per_day=1
    ),
    psionic_strength_excluded boolean NOT NULL CHECK (
        psionic_strength_excluded
    )
);

CREATE TABLE rule_personal_mental_healing_characteristic (
    rule_id bigint NOT NULL REFERENCES
        rule_personal_mental_healing(rule_id),
    characteristic_rule_id bigint NOT NULL UNIQUE REFERENCES
        rule_characteristic(rule_id),
    points_per_day integer NOT NULL CHECK (points_per_day=1),
    PRIMARY KEY (rule_id,characteristic_rule_id)
);

CREATE TABLE cmd_personal_mental_healing_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    campaign_day_number bigint NOT NULL,
    damaged_characteristic_count integer NOT NULL CHECK (
        damaged_characteristic_count BETWEEN 1 AND 2
    ),
    applied_point_count integer NOT NULL CHECK (
        applied_point_count=damaged_characteristic_count
    ),
    actor_version_before bigint NOT NULL,
    actor_version_after bigint NOT NULL CHECK (
        actor_version_after=actor_version_before+1
    ),
    UNIQUE (actor_id,campaign_day_number)
);

CREATE TABLE cmd_personal_mental_healing_allocation (
    command_id bigint NOT NULL REFERENCES
        cmd_personal_mental_healing_receipt(command_id),
    allocation_order integer NOT NULL CHECK (allocation_order BETWEEN 1 AND 2),
    characteristic_rule_id bigint NOT NULL REFERENCES
        rule_personal_mental_healing_characteristic(characteristic_rule_id),
    point_change integer NOT NULL CHECK (point_change=1),
    value_before integer NOT NULL CHECK (value_before>=0),
    value_after integer NOT NULL CHECK (value_after=value_before+1),
    PRIMARY KEY (command_id,allocation_order),
    UNIQUE (command_id,characteristic_rule_id)
);

ALTER TABLE cmd_command DROP CONSTRAINT cmd_command_command_type_check;
ALTER TABLE cmd_command ADD CONSTRAINT cmd_command_command_type_check CHECK (
    command_type IN (
        'resolve_personal_attack','apply_personal_damage','create_encounter',
        'transition_encounter_mode','add_encounter_participant',
        'set_encounter_attitude','attempt_attitude_influence',
        'set_animal_reaction_context','resolve_animal_reaction',
        'check_starship_encounter','initialize_personal_combat',
        'spend_personal_action','declare_personal_reaction',
        'complete_personal_turn','advance_personal_combat_round',
        'declare_personal_attack','begin_personal_turn',
        'hasten_personal_combatant','delay_personal_turn',
        'resume_delayed_personal_turn','forfeit_delayed_personal_turn',
        'aim_personal_attack','change_personal_stance','set_personal_cover',
        'move_personal_combatant','aim_personal_attack_for_kill',
        'advance_weapon_reload','activate_psionic_power',
        'recover_psionic_strength','set_telepathic_shield',
        'attempt_career_entry','resolve_failed_career_entry',
        'apply_career_basic_training','attempt_career_survival',
        'apply_career_rank_zero_award','resolve_survival_mishap',
        'determine_career_injury','apply_career_injury',
        'determine_injury_crisis_cost','resolve_injury_crisis',
        'resolve_career_rank_attempt','apply_career_term_training',
        'complete_career_term','determine_career_aging','apply_career_aging',
        'determine_career_reenlistment','decide_career_reenlistment',
        'initialize_career_muster','roll_career_benefit',
        'resolve_career_weapon_benefit','finish_character_creation',
        'determine_aging_crisis_cost','resolve_aging_crisis',
        'resolve_career_medical_care','declare_career_anagathics',
        'update_character_final_details','assign_actor_species',
        'resolve_species_great_leap','move_species_flyer',
        'resolve_actor_task','resolve_species_hive_mentality',
        'resolve_species_naturally_curious',
        'evaluate_species_low_light_visibility',
        'advance_species_environmental_exposure',
        'set_battlefield_communication','apply_personal_initiative_support',
        'set_personal_battlefield_conditions',
        'declare_personal_explosion',
        'declare_personal_explosion_reaction',
        'resolve_personal_explosion','authorize_extreme_range',
        'resolve_personal_grapple_check','apply_personal_grapple_option',
        'apply_personal_fatigue','complete_personal_fatigue_rest',
        'resolve_personal_unconscious_recovery',
        'resolve_personal_natural_healing',
        'apply_personal_first_aid','resolve_personal_surgery',
        'apply_personal_medical_care',
        'resolve_personal_mental_healing'
    )
);

COMMENT ON TABLE cmd_personal_mental_healing_receipt IS
    'CE-COMBAT-015 immutable daily Intelligence/Education healing.';
