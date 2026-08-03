CREATE TABLE rule_species_cold_blooded_exposure (
    species_trait_rule_id bigint PRIMARY KEY REFERENCES
        rule_species_trait(species_trait_rule_id),
    initiative_modifier smallint NOT NULL CHECK (initiative_modifier=-2),
    interval_minutes smallint NOT NULL CHECK (interval_minutes=10),
    damage_dice_count smallint NOT NULL CHECK (damage_dice_count=1),
    damage_die_sides smallint NOT NULL CHECK (damage_die_sides=6),
    protective_equipment_prevents_effect boolean NOT NULL CHECK (
        protective_equipment_prevents_effect
    )
);

CREATE TABLE rule_species_heat_endurance (
    species_trait_rule_id bigint PRIMARY KEY REFERENCES
        rule_species_trait(species_trait_rule_id),
    damage_interval_minutes smallint NOT NULL CHECK (
        damage_interval_minutes=60
    ),
    prevents_hourly_hot_weather_damage boolean NOT NULL CHECK (
        prevents_hourly_hot_weather_damage
    )
);

INSERT INTO rule_species_cold_blooded_exposure
SELECT species_trait_rule_id,-2,10,1,6,true
FROM rule_species_trait WHERE trait_code='cold-blooded';

INSERT INTO rule_species_heat_endurance
SELECT species_trait_rule_id,60,true
FROM rule_species_trait WHERE trait_code='heat-endurance';

CREATE TABLE actor_species_environmental_exposure (
    exposure_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    environment_kind text NOT NULL CHECK (
        environment_kind IN ('extreme_cold','hot_weather')
    ),
    protective_equipment_active boolean NOT NULL,
    elapsed_minutes integer NOT NULL DEFAULT 0 CHECK (elapsed_minutes >= 0),
    processed_intervals integer NOT NULL DEFAULT 0 CHECK (
        processed_intervals >= 0
    ),
    exposure_status text NOT NULL DEFAULT 'active' CHECK (
        exposure_status IN ('active','ended')
    ),
    started_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    ended_at timestamptz,
    CHECK (
        (exposure_status='active' AND ended_at IS NULL)
        OR (exposure_status='ended' AND ended_at IS NOT NULL)
    )
);

CREATE UNIQUE INDEX actor_one_active_species_environmental_exposure
    ON actor_species_environmental_exposure(actor_id,environment_kind)
    WHERE exposure_status='active';

ALTER TABLE health_damage_instance
    ALTER COLUMN attack_command_id DROP NOT NULL,
    ADD COLUMN environmental_command_id bigint UNIQUE
        REFERENCES cmd_command(command_id),
    ADD CONSTRAINT health_damage_exactly_one_source_check CHECK (
        num_nonnulls(attack_command_id,environmental_command_id)=1
    );

ALTER TABLE cmd_damage_receipt
    ADD COLUMN unapplied_lethal_overflow integer NOT NULL DEFAULT 0 CHECK (
        unapplied_lethal_overflow >= 0
    );

CREATE TABLE cmd_species_environmental_exposure_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    exposure_id bigint NOT NULL REFERENCES
        actor_species_environmental_exposure(exposure_id),
    actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    environment_kind text NOT NULL CHECK (
        environment_kind IN ('extreme_cold','hot_weather')
    ),
    elapsed_minutes_before integer NOT NULL CHECK (
        elapsed_minutes_before >= 0
    ),
    elapsed_minutes_added integer NOT NULL CHECK (
        elapsed_minutes_added > 0
    ),
    elapsed_minutes_after integer NOT NULL CHECK (
        elapsed_minutes_after=
            elapsed_minutes_before+elapsed_minutes_added
    ),
    processed_intervals_before integer NOT NULL CHECK (
        processed_intervals_before >= 0
    ),
    processed_intervals_after integer NOT NULL CHECK (
        processed_intervals_after >= processed_intervals_before
    ),
    newly_processed_intervals integer NOT NULL CHECK (
        newly_processed_intervals=
            processed_intervals_after-processed_intervals_before
    ),
    protective_equipment_active boolean NOT NULL,
    initiative_modifier smallint,
    damage_prevented boolean NOT NULL,
    raw_damage integer NOT NULL CHECK (raw_damage >= 0),
    damage_instance_id bigint UNIQUE REFERENCES
        health_damage_instance(damage_instance_id),
    CHECK (
        (raw_damage=0 AND damage_instance_id IS NULL)
        OR (raw_damage>0 AND damage_instance_id IS NOT NULL)
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
        'determine_career_injury', 'apply_career_injury',
        'determine_injury_crisis_cost', 'resolve_injury_crisis',
        'resolve_career_rank_attempt', 'apply_career_term_training',
        'complete_career_term', 'determine_career_aging',
        'apply_career_aging', 'determine_career_reenlistment',
        'decide_career_reenlistment', 'initialize_career_muster',
        'roll_career_benefit', 'resolve_career_weapon_benefit',
        'finish_character_creation', 'determine_aging_crisis_cost',
        'resolve_aging_crisis', 'resolve_career_medical_care',
        'declare_career_anagathics', 'update_character_final_details',
        'assign_actor_species', 'resolve_species_great_leap',
        'move_species_flyer', 'resolve_actor_task',
        'resolve_species_hive_mentality',
        'resolve_species_naturally_curious',
        'evaluate_species_low_light_visibility',
        'advance_species_environmental_exposure'
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
        'career_anagathic_survival',
        'environment_damage'
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
        'career_anagathics_declared', 'character_final_details_updated',
        'actor_species_assigned', 'species_great_leap_resolved',
        'species_flyer_moved', 'species_flyer_fell',
        'actor_task_succeeded', 'actor_task_failed',
        'species_hive_mentality_resisted',
        'species_hive_mentality_compelled',
        'species_natural_curiosity_resisted',
        'species_natural_curiosity_compelled',
        'species_low_light_visibility_evaluated',
        'species_environmental_exposure_advanced',
        'species_environmental_damage_created',
        'species_environmental_damage_prevented'
    )
);

COMMENT ON TABLE actor_species_environmental_exposure IS
    'Authoritative elapsed exposure counters independent of a future campaign clock.';
COMMENT ON COLUMN cmd_damage_receipt.unapplied_lethal_overflow IS
    'Damage beyond all remaining physical characteristics; the actor is dead at zero.';
