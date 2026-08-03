CREATE TABLE rule_personal_natural_healing (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    full_rest_dice_count integer NOT NULL CHECK (full_rest_dice_count=1),
    full_rest_die_sides integer NOT NULL CHECK (full_rest_die_sides=6),
    full_rest_adds_endurance_modifier boolean NOT NULL CHECK (
        full_rest_adds_endurance_modifier
    ),
    active_base_points integer NOT NULL CHECK (active_base_points=1),
    active_adds_endurance_modifier boolean NOT NULL CHECK (
        active_adds_endurance_modifier
    ),
    serious_rest_uses_endurance_modifier_only boolean NOT NULL CHECK (
        serious_rest_uses_endurance_modifier_only
    ),
    serious_movement_limit_metres numeric NOT NULL CHECK (
        serious_movement_limit_metres=1.5
    ),
    serious_minor_action_loss integer NOT NULL CHECK (
        serious_minor_action_loss=1
    )
);

CREATE VIEW health_actor_injury_status AS
SELECT actor.actor_id,actor.public_id AS actor_public_id,
       count(*) FILTER (
         WHERE characteristic.current_value<
               characteristic.maximum_value
       ) AS damaged_physical_count,
       count(*) FILTER (
         WHERE characteristic.current_value=0
       ) AS zero_physical_count,
       CASE
         WHEN count(*) FILTER (
           WHERE characteristic.current_value<
                 characteristic.maximum_value)=3
           THEN 'seriously_wounded'
         WHEN count(*) FILTER (
           WHERE characteristic.current_value<
                 characteristic.maximum_value)>0
           THEN 'wounded'
         ELSE 'uninjured'
       END AS injury_status
  FROM actor_actor actor
  JOIN actor_characteristic characteristic
    ON characteristic.actor_id=actor.actor_id
  JOIN rule_rule rule
    ON rule.rule_id=characteristic.characteristic_rule_id
   AND rule.rule_code IN (
       'characteristic.strength','characteristic.dexterity',
       'characteristic.endurance')
 GROUP BY actor.actor_id,actor.public_id
HAVING count(*)=3;

CREATE TABLE cmd_personal_natural_healing_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    campaign_day_number bigint NOT NULL,
    lifestyle text NOT NULL CHECK (lifestyle IN ('full_rest','active')),
    injury_status_before text NOT NULL CHECK (
        injury_status_before IN ('wounded','seriously_wounded')
    ),
    endurance_value integer NOT NULL CHECK (endurance_value>=0),
    endurance_modifier integer NOT NULL,
    healing_die_result integer CHECK (healing_die_result BETWEEN 1 AND 6),
    signed_points integer NOT NULL,
    applied_point_magnitude integer NOT NULL CHECK (
        applied_point_magnitude>=0
    ),
    unapplied_point_magnitude integer NOT NULL CHECK (
        unapplied_point_magnitude>=0
    ),
    injury_status_after text NOT NULL CHECK (
        injury_status_after IN (
            'uninjured','wounded','seriously_wounded')
    ),
    actor_version_before bigint NOT NULL,
    actor_version_after bigint NOT NULL CHECK (
        actor_version_after=actor_version_before+1
    ),
    UNIQUE (actor_id,campaign_day_number),
    CHECK (
        (lifestyle='full_rest' AND injury_status_before='wounded'
         AND healing_die_result IS NOT NULL)
        OR healing_die_result IS NULL
    ),
    CHECK (
        applied_point_magnitude+unapplied_point_magnitude=abs(signed_points)
    )
);

CREATE TABLE cmd_personal_natural_healing_allocation (
    command_id bigint NOT NULL
        REFERENCES cmd_personal_natural_healing_receipt(command_id),
    allocation_order integer NOT NULL CHECK (allocation_order>0),
    characteristic_rule_id bigint NOT NULL
        REFERENCES rule_characteristic(rule_id),
    point_change integer NOT NULL CHECK (point_change<>0),
    value_before integer NOT NULL CHECK (value_before>=0),
    value_after integer NOT NULL CHECK (value_after>=0),
    PRIMARY KEY (command_id,allocation_order),
    UNIQUE (command_id,characteristic_rule_id),
    CHECK (value_after=value_before+point_change)
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
        'resolve_personal_natural_healing'
    )
);

COMMENT ON VIEW health_actor_injury_status IS
    'Derived CE-COMBAT-013 physical-characteristic injury classification.';
