CREATE TABLE inv_item_definition (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    item_kind text NOT NULL CHECK (item_kind IN ('weapon','armor','equipment')),
    minimum_tech_level smallint CHECK (minimum_tech_level >= 0),
    cost_credits bigint CHECK (cost_credits >= 0),
    mass_grams integer CHECK (mass_grams >= 0)
);

CREATE TABLE combat_damage_type (
    damage_type_code text PRIMARY KEY CHECK (
        damage_type_code IN ('bludgeoning','energy','piercing','slashing')),
    name text NOT NULL UNIQUE
);
INSERT INTO combat_damage_type VALUES
    ('bludgeoning','Bludgeoning'), ('energy','Energy'),
    ('piercing','Piercing'), ('slashing','Slashing');

CREATE TABLE inv_armor_definition (
    item_rule_id bigint PRIMARY KEY REFERENCES inv_item_definition(rule_id),
    general_armor_rating smallint NOT NULL CHECK (general_armor_rating >= 0),
    laser_armor_rating smallint CHECK (laser_armor_rating >= 0),
    required_skill_rule_id bigint REFERENCES rule_skill(rule_id)
);

CREATE TABLE inv_weapon_definition (
    item_rule_id bigint PRIMARY KEY REFERENCES inv_item_definition(rule_id),
    damage_dice_count smallint NOT NULL CHECK (damage_dice_count > 0),
    damage_die_sides smallint NOT NULL CHECK (damage_die_sides > 1),
    illegal_at_law_level smallint CHECK (illegal_at_law_level >= 0)
);

CREATE TABLE inv_weapon_damage_type (
    item_rule_id bigint NOT NULL REFERENCES inv_weapon_definition(item_rule_id),
    damage_type_code text NOT NULL REFERENCES combat_damage_type(damage_type_code),
    PRIMARY KEY (item_rule_id, damage_type_code)
);

CREATE TABLE combat_range_band (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    printed_minimum_metres numeric,
    printed_maximum_metres numeric,
    printed_distance text NOT NULL CHECK (btrim(printed_distance) <> ''),
    printed_squares text NOT NULL CHECK (btrim(printed_squares) <> ''),
    display_order smallint NOT NULL UNIQUE CHECK (display_order > 0),
    CHECK (printed_minimum_metres IS NULL OR printed_maximum_metres IS NULL
           OR printed_minimum_metres <= printed_maximum_metres)
);

CREATE TABLE combat_attack_profile (
    attack_profile_code text PRIMARY KEY,
    name text NOT NULL UNIQUE,
    required_skill_rule_id bigint NOT NULL REFERENCES rule_skill(rule_id)
);

CREATE TABLE combat_attack_profile_difficulty (
    attack_profile_code text NOT NULL REFERENCES combat_attack_profile,
    range_band_rule_id bigint NOT NULL REFERENCES combat_range_band(rule_id),
    difficulty_rule_id bigint REFERENCES rule_difficulty(rule_id),
    permitted boolean NOT NULL,
    PRIMARY KEY (attack_profile_code, range_band_rule_id),
    CHECK ((permitted AND difficulty_rule_id IS NOT NULL)
           OR (NOT permitted AND difficulty_rule_id IS NULL))
);

CREATE TABLE inv_weapon_attack_mode (
    item_rule_id bigint NOT NULL REFERENCES inv_weapon_definition(item_rule_id),
    attack_profile_code text NOT NULL REFERENCES combat_attack_profile,
    display_order smallint NOT NULL CHECK (display_order > 0),
    PRIMARY KEY (item_rule_id, attack_profile_code),
    UNIQUE (item_rule_id, display_order)
);

COMMENT ON TABLE combat_range_band IS
    'Printed Cepheus bands; exact boundary inclusivity remains unasserted.';
COMMENT ON TABLE inv_weapon_attack_mode IS
    'A weapon may expose multiple source-defined attack modes.';
