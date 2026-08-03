CREATE TABLE rule_survival_mishap (
    mishap_rule_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    roll_value smallint NOT NULL UNIQUE CHECK (roll_value BETWEEN 1 AND 6),
    outcome_code text NOT NULL UNIQUE CHECK (
        outcome_code IN (
            'injured_in_action', 'honorable_discharge',
            'legal_battle', 'dishonorable_discharge',
            'dishonorable_discharge_prison', 'medical_discharge'
        )
    ),
    outcome_text text NOT NULL CHECK (btrim(outcome_text) <> ''),
    elapsed_years smallint NOT NULL CHECK (elapsed_years >= 2),
    debt_credits integer NOT NULL DEFAULT 0 CHECK (debt_credits >= 0),
    forfeit_all_career_benefits boolean NOT NULL DEFAULT false,
    injury_mode text CHECK (
        injury_mode IN ('result_two_or_twice_lower','roll_once')
    )
);

INSERT INTO rule_survival_mishap
    (roll_value,outcome_code,outcome_text,elapsed_years,debt_credits,
     forfeit_all_career_benefits,injury_mode)
VALUES
    (1,'injured_in_action',
     'Injured in action.',2,0,false,'result_two_or_twice_lower'),
    (2,'honorable_discharge',
     'Honorably discharged from the service.',2,0,false,NULL),
    (3,'legal_battle',
     'Honorably discharged after a long legal battle.',2,10000,false,NULL),
    (4,'dishonorable_discharge',
     'Dishonorably discharged from the service.',2,0,true,NULL),
    (5,'dishonorable_discharge_prison',
     'Dishonorably discharged after four extra years in prison.',
     6,0,true,NULL),
    (6,'medical_discharge',
     'Medically discharged from the service.',2,0,false,'roll_once');

CREATE TABLE actor_financial_state (
    actor_id bigint PRIMARY KEY REFERENCES actor_actor(actor_id),
    cash_credits bigint NOT NULL DEFAULT 0,
    debt_credits bigint NOT NULL DEFAULT 0 CHECK (debt_credits >= 0)
);

ALTER TABLE actor_career_stint
    ADD COLUMN all_benefits_forfeited boolean NOT NULL DEFAULT false;

ALTER TABLE actor_career_term
    ADD COLUMN elapsed_years smallint,
    ADD COLUMN benefit_roll_eligible boolean,
    ADD COLUMN mishap_rule_id bigint REFERENCES rule_survival_mishap(
        mishap_rule_id
    );

ALTER TABLE actor_career_term ADD CONSTRAINT actor_career_term_mishap_check CHECK (
    (term_status<>'mishap' AND mishap_rule_id IS NULL)
    OR
    (term_status='mishap' AND mishap_rule_id IS NOT NULL
     AND elapsed_years IS NOT NULL AND benefit_roll_eligible=false)
);

CREATE TABLE actor_career_injury_requirement (
    injury_requirement_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    career_term_id bigint NOT NULL UNIQUE REFERENCES actor_career_term(
        career_term_id
    ),
    actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    injury_mode text NOT NULL CHECK (
        injury_mode IN ('result_two_or_twice_lower','roll_once')
    ),
    requirement_status text NOT NULL DEFAULT 'pending' CHECK (
        requirement_status IN ('pending','resolved')
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
        'apply_career_rank_zero_award', 'resolve_survival_mishap'
    )
);

ALTER TABLE cmd_random_draw DROP CONSTRAINT cmd_random_draw_draw_group_check;
ALTER TABLE cmd_random_draw ADD CONSTRAINT cmd_random_draw_draw_group_check CHECK (
    draw_group IN (
        'attack', 'damage', 'task', 'occurrence', 'encounter_type',
        'initiative', 'psionic_activation', 'psionic_timing',
        'career_qualification', 'career_draft', 'career_survival',
        'career_mishap'
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
        'career_rank_zero_award_applied', 'survival_mishap_resolved'
    )
);

CREATE TABLE cmd_survival_mishap_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    career_term_id bigint NOT NULL UNIQUE REFERENCES actor_career_term(
        career_term_id
    ),
    mishap_rule_id bigint NOT NULL REFERENCES rule_survival_mishap(
        mishap_rule_id
    ),
    debt_before bigint NOT NULL CHECK (debt_before >= 0),
    debt_after bigint NOT NULL CHECK (debt_after >= debt_before),
    injury_requirement_id bigint REFERENCES actor_career_injury_requirement(
        injury_requirement_id
    )
);
