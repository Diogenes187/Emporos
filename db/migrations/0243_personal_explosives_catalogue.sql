CREATE TABLE inv_personal_explosive_definition (
    item_rule_id bigint PRIMARY KEY REFERENCES inv_item_definition(rule_id),
    explosive_code text NOT NULL UNIQUE CHECK (
        explosive_code IN ('plastic','pocket-nuke','tdx')),
    damage_dice_count smallint NOT NULL CHECK (damage_dice_count>0),
    damage_die_sides smallint NOT NULL CHECK (damage_die_sides=6),
    damage_multiplier smallint NOT NULL CHECK (damage_multiplier>0),
    radius_dice_count smallint NOT NULL CHECK (radius_dice_count>0),
    radius_die_sides smallint NOT NULL CHECK (radius_die_sides=6),
    radius_unit text NOT NULL CHECK (radius_unit='metre'),
    source_mass_is_unquantified boolean NOT NULL CHECK (
        source_mass_is_unquantified),
    source_states_horizontal_axis_only boolean NOT NULL,
    source_states_too_large_for_grenade_launcher boolean NOT NULL,
    CHECK (
        (explosive_code='plastic' AND damage_dice_count=3
         AND damage_multiplier=1 AND radius_dice_count=2
         AND NOT source_states_horizontal_axis_only
         AND NOT source_states_too_large_for_grenade_launcher)
        OR
        (explosive_code='pocket-nuke' AND damage_dice_count=2
         AND damage_multiplier=20 AND radius_dice_count=15
         AND NOT source_states_horizontal_axis_only
         AND source_states_too_large_for_grenade_launcher)
        OR
        (explosive_code='tdx' AND damage_dice_count=4
         AND damage_multiplier=1 AND radius_dice_count=4
         AND source_states_horizontal_axis_only
         AND NOT source_states_too_large_for_grenade_launcher)
    )
);

CREATE TABLE rule_personal_explosive_use (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    required_skill_rule_id bigint NOT NULL REFERENCES rule_skill(rule_id),
    effect_zero_multiplier smallint NOT NULL CHECK (
        effect_zero_multiplier=1),
    effect_one_multiplier smallint NOT NULL CHECK (
        effect_one_multiplier=1),
    positive_effect_value_is_damage_multiplier boolean NOT NULL CHECK (
        positive_effect_value_is_damage_multiplier),
    negative_effect_outcome_is_unquantified boolean NOT NULL CHECK (
        negative_effect_outcome_is_unquantified),
    unavailable_from_law_level smallint NOT NULL CHECK (
        unavailable_from_law_level=1)
);

COMMENT ON TABLE inv_personal_explosive_definition IS
    'CE-EQUIP-012 paired-source explosive catalogue; mass is not supplied.';
COMMENT ON TABLE rule_personal_explosive_use IS
    'CE-EQUIP-012 leaves negative-Effect damage outcome unquantified.';
