CREATE TABLE rule_personal_medical_treatment (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    ordinary_target_number integer NOT NULL CHECK (ordinary_target_number=8),
    first_aid_full_minutes integer NOT NULL CHECK (first_aid_full_minutes=5),
    first_aid_late_minutes integer NOT NULL CHECK (first_aid_late_minutes=60),
    first_aid_full_effect_multiplier integer NOT NULL CHECK (
        first_aid_full_effect_multiplier=2
    ),
    first_aid_late_effect_multiplier integer NOT NULL CHECK (
        first_aid_late_effect_multiplier=1
    ),
    first_aid_self_modifier integer NOT NULL CHECK (
        first_aid_self_modifier=-2
    ),
    surgery_effect_multiplier integer NOT NULL CHECK (
        surgery_effect_multiplier=2
    ),
    surgery_self_modifier integer NOT NULL CHECK (
        surgery_self_modifier=-4
    ),
    cross_species_modifier integer NOT NULL CHECK (
        cross_species_modifier=-2
    ),
    medical_care_base_points integer NOT NULL CHECK (
        medical_care_base_points=2
    )
);

CREATE TABLE health_medical_facility (
    medical_facility_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    facility_reference text NOT NULL CHECK (btrim(facility_reference)<>''),
    facility_type text NOT NULL CHECK (
        facility_type IN ('hospital','sickbay')
    ),
    location_id bigint REFERENCES loc_location(location_id),
    vehicle_id bigint REFERENCES vehicle_vehicle(vehicle_id),
    spacecraft_id bigint REFERENCES ship_ship(ship_id),
    active boolean NOT NULL DEFAULT true,
    UNIQUE (campaign_id,facility_reference),
    CHECK (
        num_nonnulls(location_id,vehicle_id,spacecraft_id)<=1
    )
);

ALTER TABLE health_damage_instance
    ADD COLUMN applied_campaign_day bigint,
    ADD COLUMN applied_campaign_second integer CHECK (
        applied_campaign_second BETWEEN 0 AND 86399
    ),
    ADD CONSTRAINT health_damage_instance_campaign_time_check CHECK (
        (allocation_status='pending'
         AND applied_campaign_day IS NULL
         AND applied_campaign_second IS NULL)
        OR
        (allocation_status='applied'
         AND applied_campaign_day IS NOT NULL
         AND applied_campaign_second IS NOT NULL)
    );

CREATE TABLE cmd_personal_medical_treatment_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    procedure_code text NOT NULL CHECK (
        procedure_code IN ('first_aid','surgery','medical_care')
    ),
    patient_actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    doctor_actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    medical_facility_id bigint REFERENCES
        health_medical_facility(medical_facility_id),
    campaign_day_number bigint NOT NULL,
    campaign_second_of_day integer NOT NULL CHECK (
        campaign_second_of_day BETWEEN 0 AND 86399
    ),
    injury_status_before text NOT NULL CHECK (
        injury_status_before IN ('wounded','seriously_wounded')
    ),
    medicine_skill_modifier integer NOT NULL,
    endurance_modifier integer,
    self_treatment_modifier integer NOT NULL,
    cross_species_modifier integer NOT NULL,
    check_total integer,
    target_number integer,
    effect integer,
    succeeded boolean,
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
    CHECK (
        applied_point_magnitude+unapplied_point_magnitude=abs(signed_points)
    ),
    CHECK (
        (procedure_code='first_aid' AND medical_facility_id IS NULL)
        OR
        (procedure_code IN ('surgery','medical_care')
         AND medical_facility_id IS NOT NULL)
    ),
    CHECK (
        (procedure_code='medical_care'
         AND check_total IS NULL AND target_number IS NULL
         AND effect IS NULL AND succeeded IS NULL
         AND endurance_modifier IS NOT NULL)
        OR
        (procedure_code IN ('first_aid','surgery')
         AND check_total IS NOT NULL AND target_number IS NOT NULL
         AND effect=check_total-target_number
         AND succeeded=(check_total>=target_number))
    )
);

CREATE TABLE cmd_personal_medical_treatment_allocation (
    command_id bigint NOT NULL REFERENCES
        cmd_personal_medical_treatment_receipt(command_id),
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

CREATE TABLE cmd_personal_first_aid_link (
    command_id bigint PRIMARY KEY REFERENCES
        cmd_personal_medical_treatment_receipt(command_id),
    damage_instance_id bigint NOT NULL UNIQUE REFERENCES
        health_damage_instance(damage_instance_id),
    elapsed_seconds integer NOT NULL CHECK (elapsed_seconds>=0),
    effectiveness_tier text NOT NULL CHECK (
        effectiveness_tier IN ('full','late','expired')
    ),
    effect_multiplier integer NOT NULL CHECK (
        effect_multiplier IN (0,1,2)
    )
);

CREATE TABLE cmd_personal_surgery_link (
    command_id bigint PRIMARY KEY REFERENCES
        cmd_personal_medical_treatment_receipt(command_id),
    first_aid_command_id bigint NOT NULL UNIQUE REFERENCES
        cmd_personal_first_aid_link(command_id)
);

CREATE TABLE cmd_personal_medical_care_link (
    command_id bigint PRIMARY KEY REFERENCES
        cmd_personal_medical_treatment_receipt(command_id),
    full_bed_rest boolean NOT NULL CHECK (full_bed_rest),
    even_base_share integer NOT NULL CHECK (even_base_share>=0),
    remainder_points integer NOT NULL CHECK (remainder_points>=0),
    UNIQUE (command_id,full_bed_rest)
);
CREATE UNIQUE INDEX cmd_personal_medical_care_actor_day_unique
ON cmd_personal_medical_treatment_receipt (
    patient_actor_id,campaign_day_number
) WHERE procedure_code='medical_care';

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
        'apply_personal_medical_care'
    )
);

COMMENT ON TABLE cmd_personal_medical_treatment_receipt IS
    'CE-COMBAT-014 immutable First Aid, Surgery, and Medical Care outcomes.';
