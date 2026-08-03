CREATE TABLE rule_career_system (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    starting_age_years smallint NOT NULL CHECK (starting_age_years > 0),
    term_years smallint NOT NULL CHECK (term_years > 0),
    retirement_terms smallint NOT NULL CHECK (retirement_terms > 0),
    previous_career_qualification_modifier smallint NOT NULL,
    draft_uses_allowed smallint NOT NULL CHECK (draft_uses_allowed >= 0),
    drifter_always_open boolean NOT NULL,
    survival_natural_two_fails boolean NOT NULL
);

CREATE TABLE rule_career_draft_roll (
    roll_value smallint PRIMARY KEY CHECK (roll_value BETWEEN 1 AND 6),
    career_rule_id bigint NOT NULL REFERENCES rule_career(career_rule_id)
);

CREATE TABLE src_career_draft_roll_provenance (
    roll_value smallint NOT NULL REFERENCES rule_career_draft_roll(roll_value),
    source_locator_id bigint NOT NULL REFERENCES src_locator(source_locator_id),
    import_candidate_id bigint REFERENCES src_import_candidate(import_candidate_id),
    source_review_id bigint REFERENCES src_review(source_review_id),
    provenance_class text NOT NULL CHECK (
        provenance_class IN ('direct','corroborating')
    ),
    is_primary_citation boolean NOT NULL DEFAULT false,
    PRIMARY KEY (roll_value,source_locator_id,provenance_class)
);

CREATE TABLE actor_lifepath_state (
    actor_id bigint PRIMARY KEY REFERENCES actor_actor(actor_id),
    age_years smallint NOT NULL CHECK (age_years > 0),
    total_terms smallint NOT NULL DEFAULT 0 CHECK (total_terms >= 0),
    draft_uses smallint NOT NULL DEFAULT 0 CHECK (draft_uses >= 0),
    lifepath_status text NOT NULL DEFAULT 'active' CHECK (
        lifepath_status IN ('active','completed')
    )
);

CREATE TABLE actor_career_stint (
    career_stint_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    career_rule_id bigint NOT NULL REFERENCES rule_career(career_rule_id),
    assignment_rule_id bigint REFERENCES rule_career_assignment(
        assignment_rule_id
    ),
    entry_method text NOT NULL CHECK (
        entry_method IN ('qualified','drifter_fallback','draft')
    ),
    stint_order smallint NOT NULL CHECK (stint_order > 0),
    terms_completed smallint NOT NULL DEFAULT 0 CHECK (terms_completed >= 0),
    rank_number smallint NOT NULL DEFAULT 0 CHECK (rank_number BETWEEN 0 AND 6),
    stint_status text NOT NULL DEFAULT 'active' CHECK (
        stint_status IN ('active','left')
    ),
    UNIQUE (actor_id,stint_order)
);

CREATE UNIQUE INDEX actor_career_stint_one_active_uq
    ON actor_career_stint(actor_id) WHERE stint_status='active';

CREATE TABLE actor_career_entry_attempt (
    career_entry_attempt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    attempted_career_rule_id bigint NOT NULL REFERENCES rule_career(
        career_rule_id
    ),
    assignment_rule_id bigint REFERENCES rule_career_assignment(
        assignment_rule_id
    ),
    previous_careers smallint NOT NULL CHECK (previous_careers >= 0),
    qualification_modifier smallint NOT NULL,
    characteristic_modifier smallint NOT NULL,
    check_total smallint,
    target_number smallint,
    qualified boolean NOT NULL,
    attempt_status text NOT NULL CHECK (
        attempt_status IN ('qualified','awaiting_fallback','resolved')
    ),
    resolved_stint_id bigint REFERENCES actor_career_stint(career_stint_id),
    CHECK (
        (qualified AND attempt_status='qualified'
         AND resolved_stint_id IS NOT NULL)
        OR
        (NOT qualified AND attempt_status='awaiting_fallback'
         AND resolved_stint_id IS NULL)
        OR
        (NOT qualified AND attempt_status='resolved'
         AND resolved_stint_id IS NOT NULL)
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
        'attempt_career_entry', 'resolve_failed_career_entry'
    )
);

ALTER TABLE cmd_random_draw DROP CONSTRAINT cmd_random_draw_draw_group_check;
ALTER TABLE cmd_random_draw ADD CONSTRAINT cmd_random_draw_draw_group_check CHECK (
    draw_group IN (
        'attack', 'damage', 'task', 'occurrence', 'encounter_type',
        'initiative', 'psionic_activation', 'psionic_timing',
        'career_qualification', 'career_draft'
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
        'career_entry_fallback_resolved'
    )
);

CREATE TABLE cmd_career_entry_attempt_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    career_entry_attempt_id bigint NOT NULL UNIQUE
        REFERENCES actor_career_entry_attempt(career_entry_attempt_id)
);

CREATE TABLE cmd_career_entry_fallback_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    career_entry_attempt_id bigint NOT NULL UNIQUE
        REFERENCES actor_career_entry_attempt(career_entry_attempt_id),
    fallback_kind text NOT NULL CHECK (
        fallback_kind IN ('drifter','draft')
    ),
    draft_roll smallint CHECK (draft_roll BETWEEN 1 AND 6),
    resulting_career_rule_id bigint NOT NULL REFERENCES rule_career(
        career_rule_id
    ),
    resulting_stint_id bigint NOT NULL REFERENCES actor_career_stint(
        career_stint_id
    ),
    CHECK (
        (fallback_kind='draft' AND draft_roll IS NOT NULL)
        OR (fallback_kind='drifter' AND draft_roll IS NULL)
    )
);
