CREATE TABLE rule_book1_heavy_weapon (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    weapon_code text NOT NULL UNIQUE CHECK (weapon_code IN (
        'grenade-launcher','rocket-launcher','ram-grenade-launcher',
        'pgmp','fgmp')),
    minimum_tech_level smallint NOT NULL CHECK (minimum_tech_level>=0),
    cost_credits bigint NOT NULL CHECK (cost_credits>=0),
    mass_grams integer NOT NULL CHECK (mass_grams>0),
    attack_profile_code text NOT NULL REFERENCES combat_attack_profile,
    damage_basis text NOT NULL CHECK (
        damage_basis IN ('fixed-dice','selected-grenade')),
    damage_dice_count smallint,
    damage_die_sides smallint,
    has_recoil boolean NOT NULL,
    illegal_at_law_level smallint NOT NULL CHECK (
        illegal_at_law_level IN (2,3)),
    CHECK ((damage_basis='fixed-dice' AND damage_dice_count>0
            AND damage_die_sides=6)
        OR (damage_basis='selected-grenade' AND damage_dice_count IS NULL
            AND damage_die_sides IS NULL))
);
CREATE TABLE rule_book1_heavy_weapon_fire_profile (
    weapon_rule_id bigint PRIMARY KEY REFERENCES rule_book1_heavy_weapon(rule_id),
    single_fire_rounds smallint NOT NULL CHECK (single_fire_rounds=1),
    automatic_fire_rounds smallint CHECK (automatic_fire_rounds IN (3,4))
);
CREATE TABLE rule_book1_heavy_ammunition (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    weapon_rule_id bigint NOT NULL UNIQUE REFERENCES rule_book1_heavy_weapon(rule_id),
    ammunition_code text NOT NULL UNIQUE,
    minimum_tech_level smallint NOT NULL CHECK (minimum_tech_level>=0),
    cost_credits bigint NOT NULL CHECK (cost_credits>=0),
    mass_grams integer NOT NULL CHECK (mass_grams>0),
    capacity_rounds smallint NOT NULL CHECK (capacity_rounds>0)
);
COMMENT ON TABLE rule_book1_heavy_weapon IS
 'CE-EQUIP-034 paired-source carried heavy weapons, distinct from VDS weapon designs.';
COMMENT ON COLUMN rule_book1_heavy_weapon.damage_basis IS
 'Selected-grenade damage is relationally deferred and never replaced by invented dice.';
