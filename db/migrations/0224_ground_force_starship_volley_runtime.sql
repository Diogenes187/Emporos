CREATE TABLE gf_ground_weapon_battery (
    ground_weapon_battery_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    battery_reference text NOT NULL CHECK (btrim(battery_reference)<>''),
    vehicle_id bigint,
    location_id bigint,
    operator_actor_id bigint NOT NULL,
    weapon_rule_id bigint NOT NULL REFERENCES
        rule_vehicle_weapon_definition(weapon_rule_id),
    governing_skill_rule_id bigint NOT NULL REFERENCES rule_skill(rule_id),
    operational_weapon_count integer NOT NULL CHECK (
        operational_weapon_count>0
    ),
    ammunition_remaining integer CHECK (ammunition_remaining>=0),
    active boolean NOT NULL DEFAULT true,
    concurrency_version bigint NOT NULL DEFAULT 1 CHECK (
        concurrency_version>0
    ),
    FOREIGN KEY (vehicle_id,campaign_id)
        REFERENCES vehicle_vehicle(vehicle_id,campaign_id),
    FOREIGN KEY (location_id,campaign_id)
        REFERENCES loc_location(location_id,campaign_id),
    FOREIGN KEY (operator_actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    UNIQUE (campaign_id,battery_reference),
    CHECK (num_nonnulls(vehicle_id,location_id)=1)
);

CREATE TABLE cmd_ground_starship_volley (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    target_ship_id bigint NOT NULL REFERENCES ship_ship(ship_id),
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    campaign_day_number bigint NOT NULL,
    campaign_second_of_day integer NOT NULL CHECK (
        campaign_second_of_day BETWEEN 0 AND 86399
    ),
    target_range_code text NOT NULL REFERENCES
        rule_vehicle_weapon_target_range(target_range_code),
    attack_modifier integer NOT NULL CHECK (attack_modifier=4),
    volley_status text NOT NULL CHECK (
        volley_status IN ('awaiting_primary','finalized','missed')
    ),
    successful_attack_count integer NOT NULL CHECK (
        successful_attack_count>=0
    ),
    UNIQUE (command_id,campaign_id),
    FOREIGN KEY (target_ship_id,campaign_id)
        REFERENCES ship_ship(ship_id,campaign_id),
    CHECK (
        (successful_attack_count=0 AND volley_status='missed')
        OR
        (successful_attack_count>0
         AND volley_status IN ('awaiting_primary','finalized'))
    )
);

CREATE TABLE cmd_ground_starship_volley_attack (
    command_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    attack_order integer NOT NULL CHECK (attack_order>0),
    ground_weapon_battery_id bigint NOT NULL REFERENCES
        gf_ground_weapon_battery(ground_weapon_battery_id),
    weapon_unit_order integer NOT NULL CHECK (weapon_unit_order>0),
    weapon_rule_id bigint NOT NULL REFERENCES
        rule_vehicle_weapon_definition(weapon_rule_id),
    difficulty_rule_id bigint NOT NULL REFERENCES rule_difficulty(rule_id),
    attack_die_one integer NOT NULL CHECK (attack_die_one BETWEEN 1 AND 6),
    attack_die_two integer NOT NULL CHECK (attack_die_two BETWEEN 1 AND 6),
    skill_modifier integer NOT NULL,
    characteristic_modifier integer NOT NULL,
    difficulty_modifier integer NOT NULL,
    scale_modifier integer NOT NULL CHECK (scale_modifier=4),
    attack_total integer NOT NULL,
    target_number integer NOT NULL CHECK (target_number=8),
    effect integer NOT NULL CHECK (effect=attack_total-target_number),
    hit boolean NOT NULL CHECK (hit=(attack_total>=target_number)),
    damage_dice_count integer NOT NULL CHECK (damage_dice_count>0),
    ammunition_before integer,
    ammunition_after integer,
    PRIMARY KEY (command_id,attack_order),
    UNIQUE (command_id,ground_weapon_battery_id,weapon_unit_order),
    FOREIGN KEY (command_id,campaign_id)
        REFERENCES cmd_ground_starship_volley(command_id,campaign_id),
    CHECK (
        attack_total=attack_die_one+attack_die_two+skill_modifier+
            characteristic_modifier+difficulty_modifier+scale_modifier
    ),
    CHECK (
        (ammunition_before IS NULL AND ammunition_after IS NULL)
        OR ammunition_after=ammunition_before-1
    )
);

CREATE TABLE cmd_ground_starship_volley_final_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    volley_command_id bigint NOT NULL UNIQUE REFERENCES
        cmd_ground_starship_volley(command_id),
    primary_attack_order integer NOT NULL,
    primary_damage_dice integer NOT NULL CHECK (primary_damage_dice>0),
    additional_successful_damage_dice integer NOT NULL CHECK (
        additional_successful_damage_dice>=0
    ),
    contributed_additional_dice integer NOT NULL CHECK (
        contributed_additional_dice=
            additional_successful_damage_dice/2
    ),
    combined_damage_dice integer NOT NULL CHECK (
        combined_damage_dice=
            primary_damage_dice+contributed_additional_dice
    ),
    personal_scale_damage integer NOT NULL CHECK (
        personal_scale_damage>=0
    ),
    converted_damage integer NOT NULL CHECK (
        converted_damage=personal_scale_damage/50
    ),
    armor_rating integer NOT NULL CHECK (armor_rating>=0),
    hull_damage integer NOT NULL CHECK (
        hull_damage=greatest(converted_damage-armor_rating,0)
    ),
    hull_before integer NOT NULL CHECK (hull_before>=0),
    hull_after integer NOT NULL CHECK (
        hull_after=greatest(hull_before-hull_damage,0)
    ),
    unapplied_hull_damage integer NOT NULL CHECK (
        unapplied_hull_damage=greatest(hull_damage-hull_before,0)
    ),
    ship_version_before bigint NOT NULL,
    ship_version_after bigint NOT NULL CHECK (
        ship_version_after=ship_version_before+1
    ),
    ship_damage_id bigint UNIQUE REFERENCES ship_damage(ship_damage_id),
    CHECK (
        (hull_damage>0 AND ship_damage_id IS NOT NULL)
        OR (hull_damage=0 AND ship_damage_id IS NULL)
    ),
    FOREIGN KEY (volley_command_id,primary_attack_order)
        REFERENCES cmd_ground_starship_volley_attack(
            command_id,attack_order)
);

CREATE TABLE cmd_ground_starship_volley_damage_die (
    command_id bigint NOT NULL REFERENCES
        cmd_ground_starship_volley_final_receipt(command_id),
    die_order integer NOT NULL CHECK (die_order>0),
    result integer NOT NULL CHECK (result BETWEEN 1 AND 6),
    PRIMARY KEY (command_id,die_order)
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
        'resolve_personal_mental_healing',
        'resolve_ground_starship_volley_attacks',
        'finalize_ground_starship_volley'
    )
);
