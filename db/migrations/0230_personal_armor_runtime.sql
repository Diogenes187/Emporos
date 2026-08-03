CREATE TABLE inv_armor_instance_state (
    item_instance_id bigint PRIMARY KEY,
    campaign_id bigint NOT NULL,
    current_laser_armor_rating integer NOT NULL CHECK (
        current_laser_armor_rating>=0
    ),
    life_support_seconds_remaining integer CHECK (
        life_support_seconds_remaining>=0
    ),
    concurrency_version bigint NOT NULL DEFAULT 1 CHECK (
        concurrency_version>0
    ),
    UNIQUE (item_instance_id,campaign_id),
    FOREIGN KEY (item_instance_id,campaign_id)
        REFERENCES inv_item_instance(item_instance_id,campaign_id)
);

CREATE TABLE inv_actor_armor_layer (
    actor_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    item_instance_id bigint PRIMARY KEY,
    layer_order integer NOT NULL CHECK (layer_order BETWEEN 1 AND 2),
    equipped_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    source_command_id bigint NOT NULL REFERENCES cmd_command(command_id),
    FOREIGN KEY (actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    FOREIGN KEY (item_instance_id,campaign_id)
        REFERENCES inv_armor_instance_state(item_instance_id,campaign_id),
    UNIQUE (actor_id,layer_order)
);

CREATE TABLE cmd_personal_armor_equip_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    actor_id bigint NOT NULL,
    item_instance_id bigint NOT NULL,
    equip_action text NOT NULL CHECK (
        equip_action IN ('equip','unequip')
    ),
    requested_layer_order integer CHECK (
        requested_layer_order BETWEEN 1 AND 2
    ),
    layer_count_before integer NOT NULL CHECK (
        layer_count_before BETWEEN 0 AND 2
    ),
    layer_count_after integer NOT NULL CHECK (
        layer_count_after BETWEEN 0 AND 2
    ),
    FOREIGN KEY (actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    FOREIGN KEY (item_instance_id,campaign_id)
        REFERENCES inv_item_instance(item_instance_id,campaign_id),
    CHECK (
        (equip_action='equip'
         AND requested_layer_order IS NOT NULL
         AND layer_count_after=layer_count_before+1)
        OR
        (equip_action='unequip'
         AND requested_layer_order IS NULL
         AND layer_count_after=layer_count_before-1)
    )
);

CREATE TABLE cmd_personal_armor_layer_receipt (
    command_id bigint NOT NULL REFERENCES
        cmd_personal_armor_equip_receipt(command_id),
    item_instance_id bigint NOT NULL REFERENCES
        inv_item_instance(item_instance_id),
    layer_order integer NOT NULL CHECK (layer_order BETWEEN 1 AND 2),
    PRIMARY KEY (command_id,item_instance_id),
    UNIQUE (command_id,layer_order)
);

CREATE TABLE cmd_personal_armor_usage_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    actor_id bigint NOT NULL,
    item_instance_id bigint NOT NULL,
    laser_hits integer NOT NULL CHECK (laser_hits>=0),
    life_support_seconds_used integer NOT NULL CHECK (
        life_support_seconds_used>=0
    ),
    laser_rating_before integer NOT NULL,
    laser_rating_after integer NOT NULL,
    life_support_before integer,
    life_support_after integer,
    state_version_before bigint NOT NULL,
    state_version_after bigint NOT NULL CHECK (
        state_version_after=state_version_before+1
    ),
    FOREIGN KEY (actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    FOREIGN KEY (item_instance_id,campaign_id)
        REFERENCES inv_armor_instance_state(item_instance_id,campaign_id),
    CHECK (laser_hits+life_support_seconds_used>0),
    CHECK (laser_rating_after<=laser_rating_before),
    CHECK (
        (life_support_before IS NULL AND life_support_after IS NULL
         AND life_support_seconds_used=0)
        OR
        (life_support_before IS NOT NULL
         AND life_support_after=
             greatest(life_support_before-life_support_seconds_used,0))
    )
);

CREATE VIEW actor_effective_armor_characteristic AS
SELECT state.actor_id,state.characteristic_rule_id,
       state.current_value AS damage_tracking_value,
       COALESCE(max(modifier.modifier),0)::integer AS armor_modifier,
       state.current_value+
         COALESCE(max(modifier.modifier),0)::integer AS effective_value
FROM actor_characteristic state
LEFT JOIN inv_actor_armor_layer layer ON layer.actor_id=state.actor_id
LEFT JOIN inv_item_instance item
  ON item.item_instance_id=layer.item_instance_id
LEFT JOIN rule_armor_characteristic_modifier modifier
  ON modifier.armor_rule_id=item.item_rule_id
 AND modifier.characteristic_rule_id=state.characteristic_rule_id
GROUP BY state.actor_id,state.characteristic_rule_id,state.current_value;

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
        'resolve_personal_mental_healing',
        'resolve_ground_starship_volley_attacks',
        'finalize_ground_starship_volley',
        'equip_personal_armor','unequip_personal_armor',
        'apply_personal_armor_usage'
    )
);

COMMENT ON TABLE inv_armor_instance_state IS
    'Campaign-safe mutable armor resources; history lives in command receipts.';
