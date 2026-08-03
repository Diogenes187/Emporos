CREATE TABLE rule_ground_force_starship_attack (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    attack_modifier integer NOT NULL CHECK (attack_modifier=4),
    personal_damage_divisor integer NOT NULL CHECK (
        personal_damage_divisor=50
    ),
    converted_damage_rounding text NOT NULL CHECK (
        converted_damage_rounding='floor'
    ),
    armor_applied_after_conversion boolean NOT NULL CHECK (
        armor_applied_after_conversion
    ),
    minimum_damage_exception boolean NOT NULL CHECK (
        NOT minimum_damage_exception
    ),
    resulting_damage_target text NOT NULL CHECK (
        resulting_damage_target='hull'
    )
);

CREATE TABLE rule_ground_force_starship_volley_contribution (
    rule_id bigint PRIMARY KEY REFERENCES
        rule_ground_force_starship_attack(rule_id),
    primary_weapon_numerator integer NOT NULL CHECK (
        primary_weapon_numerator=1
    ),
    primary_weapon_denominator integer NOT NULL CHECK (
        primary_weapon_denominator=1
    ),
    additional_weapon_numerator integer NOT NULL CHECK (
        additional_weapon_numerator=1
    ),
    additional_weapon_denominator integer NOT NULL CHECK (
        additional_weapon_denominator=2
    ),
    additional_dice_aggregated_before_rounding boolean NOT NULL CHECK (
        additional_dice_aggregated_before_rounding
    ),
    fractional_die_rounding text NOT NULL CHECK (
        fractional_die_rounding='floor'
    ),
    successful_attacks_only boolean NOT NULL CHECK (
        successful_attacks_only
    ),
    primary_must_be_successful boolean NOT NULL CHECK (
        primary_must_be_successful
    ),
    simultaneous_target_required boolean NOT NULL CHECK (
        simultaneous_target_required
    )
);

COMMENT ON TABLE rule_ground_force_starship_attack IS
    'Source mechanics plus CE-COMBAT-016 scale-conversion adjudication.';
