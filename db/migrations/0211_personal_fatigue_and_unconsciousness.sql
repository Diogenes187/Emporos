CREATE TABLE rule_personal_fatigue (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    check_modifier integer NOT NULL CHECK (check_modifier=-2),
    rest_base_hours integer NOT NULL CHECK (rest_base_hours=3),
    rest_uses_endurance_modifier boolean NOT NULL CHECK (
        rest_uses_endurance_modifier
    ),
    repeated_fatigue_causes_unconsciousness boolean NOT NULL CHECK (
        repeated_fatigue_causes_unconsciousness
    )
);

CREATE TABLE rule_personal_unconsciousness (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    recovery_interval_minutes integer NOT NULL CHECK (
        recovery_interval_minutes=1
    ),
    recovery_difficulty_rule_id bigint NOT NULL
        REFERENCES rule_difficulty(rule_id),
    prior_failure_modifier integer NOT NULL CHECK (
        prior_failure_modifier=1
    ),
    waking_clears_fatigue boolean NOT NULL CHECK (
        NOT waking_clears_fatigue
    )
);

CREATE TABLE actor_personal_condition (
    actor_id bigint PRIMARY KEY REFERENCES actor_actor(actor_id),
    fatigued boolean NOT NULL DEFAULT false,
    fatigue_sequence integer NOT NULL DEFAULT 0 CHECK (fatigue_sequence>=0),
    fatigue_endurance_modifier integer,
    fatigue_rest_required_hours integer CHECK (
        fatigue_rest_required_hours>=0
    ),
    unconscious boolean NOT NULL DEFAULT false,
    unconscious_cause text CHECK (
        unconscious_cause IN ('repeated_fatigue')
    ),
    unconscious_recovery_failures integer NOT NULL DEFAULT 0 CHECK (
        unconscious_recovery_failures>=0
    ),
    unconscious_minutes_elapsed integer NOT NULL DEFAULT 0 CHECK (
        unconscious_minutes_elapsed>=0
    ),
    condition_version bigint NOT NULL DEFAULT 1 CHECK (condition_version>0),
    CHECK (
        (fatigued AND fatigue_sequence>0
         AND fatigue_endurance_modifier IS NOT NULL
         AND fatigue_rest_required_hours IS NOT NULL)
        OR
        (NOT fatigued AND fatigue_endurance_modifier IS NULL
         AND fatigue_rest_required_hours IS NULL
         AND NOT unconscious)
    ),
    CHECK (
        (unconscious AND fatigued
         AND unconscious_cause='repeated_fatigue')
        OR
        (NOT unconscious AND unconscious_cause IS NULL
         AND unconscious_recovery_failures=0
         AND unconscious_minutes_elapsed=0)
    )
);

CREATE TABLE actor_personal_condition_transition (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    actor_id bigint NOT NULL REFERENCES actor_personal_condition(actor_id),
    transition_kind text NOT NULL CHECK (
        transition_kind IN (
            'fatigue_started','fatigue_repeated_unconscious',
            'fatigue_rest_completed','consciousness_recovered',
            'consciousness_recovery_failed'
        )
    ),
    version_before bigint NOT NULL,
    version_after bigint NOT NULL CHECK (version_after=version_before+1),
    fatigued_before boolean NOT NULL,
    fatigued_after boolean NOT NULL,
    unconscious_before boolean NOT NULL,
    unconscious_after boolean NOT NULL,
    recovery_failures_before integer NOT NULL,
    recovery_failures_after integer NOT NULL,
    minutes_elapsed_before integer NOT NULL,
    minutes_elapsed_after integer NOT NULL
);

CREATE TABLE cmd_personal_fatigue_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    fatigue_sequence integer NOT NULL CHECK (fatigue_sequence>0),
    already_fatigued boolean NOT NULL,
    endurance_modifier integer NOT NULL,
    rest_required_hours integer NOT NULL CHECK (rest_required_hours>=0),
    check_modifier integer NOT NULL CHECK (check_modifier=-2),
    became_unconscious boolean NOT NULL,
    transition_kind text NOT NULL CHECK (
        transition_kind IN (
            'fatigue_started','fatigue_repeated_unconscious'
        )
    ),
    CHECK (
        already_fatigued=became_unconscious
        AND (
            (already_fatigued
             AND transition_kind='fatigue_repeated_unconscious')
            OR
            (NOT already_fatigued AND transition_kind='fatigue_started')
        )
    )
);

CREATE TABLE cmd_personal_fatigue_rest_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    fatigue_sequence integer NOT NULL CHECK (fatigue_sequence>0),
    required_hours integer NOT NULL CHECK (required_hours>=0),
    completed_hours numeric NOT NULL CHECK (completed_hours>=0),
    fatigue_cleared boolean NOT NULL CHECK (fatigue_cleared),
    CHECK (completed_hours>=required_hours)
);

CREATE TABLE cmd_personal_unconscious_recovery_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    attempt_number integer NOT NULL CHECK (attempt_number>0),
    minutes_elapsed integer NOT NULL CHECK (minutes_elapsed>0),
    endurance_modifier integer NOT NULL,
    prior_failure_modifier integer NOT NULL CHECK (
        prior_failure_modifier>=0
    ),
    check_total integer NOT NULL,
    target_number integer NOT NULL,
    effect integer NOT NULL,
    succeeded boolean NOT NULL,
    remains_fatigued boolean NOT NULL CHECK (remains_fatigued),
    CHECK (effect=check_total-target_number)
);

ALTER TABLE enc_personal_attack
    ADD COLUMN fatigue_attack_modifier integer NOT NULL DEFAULT 0 CHECK (
        fatigue_attack_modifier IN (0,-2)
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
        'resolve_personal_unconscious_recovery'
    )
);

COMMENT ON TABLE actor_personal_condition IS
    'CE-COMBAT-012 campaign-safe fatigue and repeated-fatigue unconsciousness.';
