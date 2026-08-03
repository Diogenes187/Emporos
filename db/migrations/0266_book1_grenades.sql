CREATE TABLE rule_book1_grenade (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    grenade_code text NOT NULL UNIQUE CHECK (
        grenade_code IN ('frag','smoke','aerosol','stun')),
    minimum_tech_level smallint NOT NULL CHECK (minimum_tech_level>=0),
    case_cost_credits bigint NOT NULL CHECK (case_cost_credits>=0),
    grenades_per_case smallint NOT NULL CHECK (grenades_per_case=6),
    mass_grams_per_grenade integer NOT NULL CHECK (mass_grams_per_grenade=500),
    illegal_at_law_level smallint NOT NULL CHECK (illegal_at_law_level=1),
    effect_kind text NOT NULL CHECK (
        effect_kind IN ('blast-damage','obscurant','laser-diffusion','stun'))
);

CREATE TABLE rule_book1_grenade_delivery_mode (
    grenade_rule_id bigint NOT NULL REFERENCES rule_book1_grenade(rule_id),
    delivery_code text NOT NULL CHECK (delivery_code IN ('thrown','launcher')),
    attack_profile_code text NOT NULL REFERENCES combat_attack_profile,
    PRIMARY KEY (grenade_rule_id,delivery_code),
    CHECK ((delivery_code='thrown' AND attack_profile_code='thrown')
        OR (delivery_code='launcher' AND attack_profile_code='shotgun'))
);

CREATE TABLE rule_book1_frag_grenade_damage_band (
    grenade_rule_id bigint NOT NULL REFERENCES rule_book1_grenade(rule_id),
    maximum_distance_metres smallint NOT NULL CHECK (
        maximum_distance_metres IN (3,6,9)),
    damage_dice_count smallint NOT NULL CHECK (damage_dice_count IN (1,3,5)),
    damage_die_sides smallint NOT NULL CHECK (damage_die_sides=6),
    PRIMARY KEY (grenade_rule_id,maximum_distance_metres),
    UNIQUE (grenade_rule_id,damage_dice_count)
);

CREATE TABLE rule_book1_grenade_field_effect (
    grenade_rule_id bigint PRIMARY KEY REFERENCES rule_book1_grenade(rule_id),
    radius_metres smallint NOT NULL CHECK (radius_metres=6),
    duration_dice_count smallint NOT NULL CHECK (duration_dice_count=1),
    duration_die_sides smallint NOT NULL CHECK (duration_die_sides=6),
    duration_multiplier_rounds smallint NOT NULL CHECK (
        duration_multiplier_rounds=3),
    attack_modifier smallint,
    laser_attack_modifier smallint,
    laser_damage_reduction integer,
    blocks_normal_vision boolean NOT NULL,
    blocks_laser_communications boolean NOT NULL,
    extreme_weather_may_shorten boolean NOT NULL CHECK (
        extreme_weather_may_shorten),
    CHECK (
        (attack_modifier=-2 AND laser_attack_modifier=-4
         AND laser_damage_reduction IS NULL
         AND blocks_normal_vision AND NOT blocks_laser_communications)
        OR
        (attack_modifier IS NULL AND laser_attack_modifier IS NULL
         AND laser_damage_reduction=10
         AND NOT blocks_normal_vision AND blocks_laser_communications))
);

CREATE TABLE rule_book1_stun_grenade_effect (
    grenade_rule_id bigint PRIMARY KEY REFERENCES rule_book1_grenade(rule_id),
    radius_metres smallint NOT NULL CHECK (radius_metres=6),
    stun_damage_dice_count smallint NOT NULL CHECK (stun_damage_dice_count=3),
    stun_damage_die_sides smallint NOT NULL CHECK (stun_damage_die_sides=6),
    resistance_characteristic_rule_id bigint NOT NULL REFERENCES
        rule_characteristic(rule_id),
    check_modifier_equals_post_armor_damage boolean NOT NULL CHECK (
        check_modifier_equals_post_armor_damage),
    failed_check_causes_unconsciousness boolean NOT NULL CHECK (
        failed_check_causes_unconsciousness),
    successful_check_ignores_stun_damage boolean NOT NULL CHECK (
        successful_check_ignores_stun_damage),
    inflicts_normal_damage boolean NOT NULL CHECK (NOT inflicts_normal_damage)
);

COMMENT ON TABLE rule_book1_grenade IS
 'CE-EQUIP-033 paired-source four-grenade catalogue; prices are cases of six and mass is per grenade.';
COMMENT ON TABLE rule_book1_grenade_field_effect IS
 'CE-EQUIP-033 typed smoke and aerosol persistence and interference.';
