CREATE TABLE rule_species_trait_task_modifier (
    trait_task_modifier_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    species_trait_rule_id bigint NOT NULL REFERENCES
        rule_species_trait(species_trait_rule_id),
    skill_rule_id bigint REFERENCES rule_skill(rule_id),
    task_context_code text CHECK (
        task_context_code ~ '^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$'
    ),
    modifier smallint NOT NULL,
    source_scope_text text NOT NULL CHECK (btrim(source_scope_text) <> ''),
    CHECK (
        (skill_rule_id IS NOT NULL)::integer
        + (task_context_code IS NOT NULL)::integer = 1
    ),
    UNIQUE NULLS NOT DISTINCT (
        species_trait_rule_id,skill_rule_id,task_context_code
    )
);

INSERT INTO rule_species_trait_task_modifier (
    species_trait_rule_id,skill_rule_id,task_context_code,modifier,
    source_scope_text
)
SELECT trait.species_trait_rule_id,skill.rule_id,value.context_code,
       2,value.scope_text
FROM (VALUES
    ('natural-pilot','skill.piloting',NULL::text,
     'All Piloting checks.'),
    ('natural-pilot','skill.navigation',NULL::text,
     'All Navigation checks.'),
    ('natural-swimmer',NULL::text,'swimming',
     'All skill checks related to swimming.')
) AS value(trait_code,skill_code,context_code,scope_text)
JOIN rule_species_trait trait ON trait.trait_code=value.trait_code
LEFT JOIN rule_rule skill ON skill.rule_code=value.skill_code;

CREATE TABLE cmd_actor_task_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    characteristic_rule_id bigint NOT NULL REFERENCES
        rule_characteristic(rule_id),
    skill_rule_id bigint NOT NULL REFERENCES rule_skill(rule_id),
    difficulty_rule_id bigint NOT NULL REFERENCES rule_difficulty(rule_id),
    task_context_code text CHECK (
        task_context_code IS NULL OR
        task_context_code ~ '^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$'
    ),
    skill_modifier smallint NOT NULL,
    characteristic_modifier smallint NOT NULL,
    difficulty_modifier smallint NOT NULL,
    circumstance_modifier smallint NOT NULL,
    species_modifier smallint NOT NULL,
    check_total smallint NOT NULL,
    target_number smallint NOT NULL,
    effect smallint NOT NULL,
    succeeded boolean NOT NULL,
    CHECK (
        effect=check_total-target_number
        AND succeeded=(check_total >= target_number)
    )
);

CREATE TABLE cmd_actor_task_species_modifier (
    command_id bigint NOT NULL REFERENCES cmd_actor_task_receipt(command_id),
    modifier_order smallint NOT NULL CHECK (modifier_order > 0),
    trait_task_modifier_id bigint NOT NULL REFERENCES
        rule_species_trait_task_modifier(trait_task_modifier_id),
    modifier smallint NOT NULL,
    PRIMARY KEY (command_id,modifier_order),
    UNIQUE (command_id,trait_task_modifier_id)
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
        'move_species_flyer', 'resolve_actor_task'
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
        'actor_task_succeeded', 'actor_task_failed'
    )
);
