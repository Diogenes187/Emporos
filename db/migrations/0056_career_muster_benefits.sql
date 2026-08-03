ALTER TABLE rule_career_benefit
    ADD COLUMN outcome_kind text,
    ADD COLUMN characteristic_rule_id bigint
        REFERENCES rule_characteristic(rule_id),
    ADD COLUMN characteristic_increase smallint,
    ADD COLUMN passage_class text,
    ADD COLUMN ship_share_dice_count smallint,
    ADD COLUMN ship_share_die_sides smallint,
    ADD COLUMN membership_code text,
    ADD COLUMN vessel_access_code text;

UPDATE rule_career_benefit
SET outcome_kind='cash'
WHERE benefit_table_code='cash';

UPDATE rule_career_benefit
SET outcome_kind='no_award'
WHERE benefit_table_code='material' AND source_outcome_text='—';

UPDATE rule_career_benefit benefit
SET outcome_kind='characteristic',
    characteristic_rule_id=rule.rule_id,
    characteristic_increase=1
FROM rule_rule rule
WHERE benefit.benefit_table_code='material'
  AND (
      (benefit.source_outcome_text='+1 End'
       AND rule.rule_code='characteristic.endurance')
      OR
      (benefit.source_outcome_text='+1 Int'
       AND rule.rule_code='characteristic.intelligence')
      OR
      (benefit.source_outcome_text='+1 Edu'
       AND rule.rule_code='characteristic.education')
      OR
      (benefit.source_outcome_text='+1 Soc'
       AND rule.rule_code='characteristic.social-standing')
  );

UPDATE rule_career_benefit
SET outcome_kind='passage',
    passage_class=lower(split_part(source_outcome_text,' ',1))
WHERE benefit_table_code='material'
  AND source_outcome_text IN ('Low Passage','Mid Passage','High Passage');

UPDATE rule_career_benefit
SET outcome_kind='ship_shares',
    ship_share_dice_count=1,
    ship_share_die_sides=6
WHERE benefit_table_code='material'
  AND source_outcome_text='1D6 Ship Shares';

UPDATE rule_career_benefit
SET outcome_kind='membership',
    membership_code='explorers_society'
WHERE benefit_table_code='material'
  AND source_outcome_text='Explorers'' Society';

UPDATE rule_career_benefit
SET outcome_kind='vessel_access',
    vessel_access_code=CASE source_outcome_text
        WHEN 'Courier Vessel' THEN 'courier_vessel'
        WHEN 'Research Vessel' THEN 'research_vessel'
    END
WHERE benefit_table_code='material'
  AND source_outcome_text IN ('Courier Vessel','Research Vessel');

UPDATE rule_career_benefit
SET outcome_kind='weapon'
WHERE benefit_table_code='material' AND source_outcome_text='Weapon';

ALTER TABLE rule_career_benefit
    ALTER COLUMN outcome_kind SET NOT NULL,
    ADD CONSTRAINT rule_career_benefit_outcome_kind_check CHECK (
        outcome_kind IN (
            'cash','no_award','characteristic','passage','ship_shares',
            'membership','vessel_access','weapon'
        )
    ),
    ADD CONSTRAINT rule_career_benefit_normalized_outcome_check CHECK (
        (
            outcome_kind='cash' AND cash_credits IS NOT NULL
            AND characteristic_rule_id IS NULL
            AND characteristic_increase IS NULL
            AND passage_class IS NULL
            AND ship_share_dice_count IS NULL
            AND ship_share_die_sides IS NULL
            AND membership_code IS NULL
            AND vessel_access_code IS NULL
        )
        OR
        (
            outcome_kind='characteristic'
            AND characteristic_rule_id IS NOT NULL
            AND characteristic_increase > 0
        )
        OR
        (
            outcome_kind='passage'
            AND passage_class IN ('low','mid','high')
        )
        OR
        (
            outcome_kind='ship_shares'
            AND ship_share_dice_count > 0
            AND ship_share_die_sides > 1
        )
        OR
        (
            outcome_kind='membership' AND membership_code IS NOT NULL
        )
        OR
        (
            outcome_kind='vessel_access' AND vessel_access_code IS NOT NULL
        )
        OR outcome_kind IN ('no_award','weapon')
    );

CREATE TABLE actor_career_muster (
    career_muster_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    career_stint_id bigint NOT NULL UNIQUE REFERENCES actor_career_stint(
        career_stint_id
    ),
    eligible_term_benefits smallint NOT NULL CHECK (
        eligible_term_benefits >= 0
    ),
    rank_bonus_benefits smallint NOT NULL CHECK (
        rank_bonus_benefits BETWEEN 0 AND 3
    ),
    total_benefit_rolls smallint NOT NULL CHECK (total_benefit_rolls >= 0),
    rolls_completed smallint NOT NULL DEFAULT 0 CHECK (rolls_completed >= 0),
    cash_rolls_taken smallint NOT NULL DEFAULT 0 CHECK (
        cash_rolls_taken BETWEEN 0 AND 3
    ),
    muster_status text NOT NULL CHECK (
        muster_status IN ('rolling','awaiting_weapon_choice','completed')
    ),
    CHECK (
        total_benefit_rolls=eligible_term_benefits+rank_bonus_benefits
        AND rolls_completed <= total_benefit_rolls
        AND (
            (muster_status='completed'
             AND rolls_completed=total_benefit_rolls)
            OR
            (muster_status<>'completed'
             AND rolls_completed<total_benefit_rolls)
        )
    )
);

CREATE TABLE actor_retirement_pension (
    career_stint_id bigint PRIMARY KEY REFERENCES actor_career_stint(
        career_stint_id
    ),
    qualifying_terms smallint NOT NULL CHECK (qualifying_terms >= 5),
    annual_credits integer NOT NULL CHECK (annual_credits >= 10000)
);

CREATE TABLE actor_career_benefit_roll (
    career_benefit_roll_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    career_muster_id bigint NOT NULL REFERENCES actor_career_muster(
        career_muster_id
    ),
    roll_order smallint NOT NULL CHECK (roll_order > 0),
    benefit_table_code text NOT NULL CHECK (
        benefit_table_code IN ('cash','material')
    ),
    natural_roll smallint NOT NULL CHECK (natural_roll BETWEEN 1 AND 6),
    roll_modifier smallint NOT NULL CHECK (roll_modifier BETWEEN 0 AND 1),
    table_result smallint NOT NULL CHECK (table_result BETWEEN 1 AND 7),
    career_benefit_id bigint NOT NULL REFERENCES rule_career_benefit(
        career_benefit_id
    ),
    award_status text NOT NULL CHECK (
        award_status IN ('resolved','awaiting_weapon_choice')
    ),
    cash_awarded bigint NOT NULL DEFAULT 0 CHECK (cash_awarded >= 0),
    ship_shares_awarded smallint NOT NULL DEFAULT 0 CHECK (
        ship_shares_awarded >= 0
    ),
    UNIQUE (career_muster_id,roll_order)
);

CREATE TABLE actor_passage_holding (
    actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    passage_class text NOT NULL CHECK (
        passage_class IN ('low','mid','high')
    ),
    quantity integer NOT NULL CHECK (quantity >= 0),
    PRIMARY KEY (actor_id,passage_class)
);

CREATE TABLE actor_ship_share_state (
    actor_id bigint PRIMARY KEY REFERENCES actor_actor(actor_id),
    shares integer NOT NULL CHECK (shares >= 0)
);

CREATE TABLE actor_membership (
    actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    membership_code text NOT NULL CHECK (btrim(membership_code) <> ''),
    PRIMARY KEY (actor_id,membership_code)
);

CREATE TABLE actor_vessel_access (
    actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    vessel_access_code text NOT NULL CHECK (
        btrim(vessel_access_code) <> ''
    ),
    quantity integer NOT NULL CHECK (quantity >= 0),
    PRIMARY KEY (actor_id,vessel_access_code)
);

CREATE TABLE actor_item_holding (
    actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    item_rule_id bigint NOT NULL REFERENCES inv_item_definition(rule_id),
    quantity integer NOT NULL CHECK (quantity >= 0),
    PRIMARY KEY (actor_id,item_rule_id)
);

CREATE TABLE cmd_career_muster_initialization_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    career_muster_id bigint NOT NULL UNIQUE REFERENCES actor_career_muster(
        career_muster_id
    ),
    annual_pension_credits integer NOT NULL CHECK (
        annual_pension_credits >= 0
    )
);

CREATE TABLE cmd_career_benefit_roll_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    career_benefit_roll_id bigint NOT NULL UNIQUE
        REFERENCES actor_career_benefit_roll(career_benefit_roll_id)
);

CREATE TABLE cmd_career_weapon_benefit_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    career_benefit_roll_id bigint NOT NULL UNIQUE
        REFERENCES actor_career_benefit_roll(career_benefit_roll_id),
    weapon_rule_id bigint NOT NULL REFERENCES inv_weapon_definition(
        item_rule_id
    ),
    resolution_kind text NOT NULL CHECK (
        resolution_kind IN ('item','skill')
    ),
    skill_rule_id bigint REFERENCES rule_skill(rule_id),
    prior_value smallint,
    resulting_value smallint,
    CHECK (
        (resolution_kind='item' AND skill_rule_id IS NULL)
        OR
        (
            resolution_kind='skill' AND skill_rule_id IS NOT NULL
            AND resulting_value IS NOT NULL
        )
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
        'roll_career_benefit', 'resolve_career_weapon_benefit'
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
        'career_benefit_ship_shares'
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
        'career_weapon_item_awarded', 'career_weapon_skill_awarded'
    )
);
