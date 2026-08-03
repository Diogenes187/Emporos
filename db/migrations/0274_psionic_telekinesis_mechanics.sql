CREATE TABLE rule_psi_telekinesis_system (
    talent_rule_id bigint PRIMARY KEY REFERENCES psi_talent(talent_rule_id),
    physical_manipulation_equivalent boolean NOT NULL CHECK (
        physical_manipulation_equivalent
    ),
    physical_danger_feedback boolean NOT NULL CHECK (
        NOT physical_danger_feedback
    ),
    pain_feedback boolean NOT NULL CHECK (NOT pain_feedback),
    limited_manipulation_sensory_awareness boolean NOT NULL CHECK (
        limited_manipulation_sensory_awareness
    ),
    effect_determines_duration_rounds boolean NOT NULL CHECK (
        effect_determines_duration_rounds
    ),
    throwing_skill_rule_id bigint NOT NULL REFERENCES rule_skill(rule_id),
    throwing_uses_greater_distance boolean NOT NULL CHECK (
        throwing_uses_greater_distance
    ),
    effect_added_to_throw_damage boolean NOT NULL CHECK (
        effect_added_to_throw_damage
    ),
    creature_and_target_take_equal_damage boolean NOT NULL CHECK (
        creature_and_target_take_equal_damage
    )
);

CREATE TABLE rule_psi_telekinesis_mass_profile (
    power_rule_id bigint PRIMARY KEY REFERENCES psi_power(power_rule_id),
    maximum_mass_grams bigint NOT NULL UNIQUE CHECK (
        maximum_mass_grams IN (10,100,1000,10000,100000,1000000)
    ),
    throwing_damage_dice_count smallint,
    throwing_damage_die_sides smallint,
    throwing_damage_flat smallint,
    can_inflict_throwing_damage boolean NOT NULL,
    CHECK (
        (NOT can_inflict_throwing_damage
         AND throwing_damage_dice_count IS NULL
         AND throwing_damage_die_sides IS NULL
         AND throwing_damage_flat IS NULL)
        OR
        (can_inflict_throwing_damage
         AND num_nonnulls(
           throwing_damage_dice_count,throwing_damage_flat)=1
         AND (throwing_damage_dice_count IS NULL
              OR (throwing_damage_dice_count>0
                  AND throwing_damage_die_sides=6))
         AND (throwing_damage_flat IS NULL OR throwing_damage_flat=1))
    )
);

COMMENT ON TABLE rule_psi_telekinesis_system IS
    'CE-PSI-005 paired-source manipulation, duration, range, and throwing rules.';
COMMENT ON TABLE rule_psi_telekinesis_mass_profile IS
    'Six exact Telekinesis mass bands and their published throwing damage.';
