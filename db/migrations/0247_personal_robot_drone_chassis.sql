CREATE TABLE inv_personal_robot_drone_chassis (
    item_rule_id bigint PRIMARY KEY REFERENCES inv_item_definition(rule_id),
    chassis_code text NOT NULL UNIQUE CHECK (
        chassis_code IN (
            'cargo-robot','repair-robot','personal-drone','probe-drone',
            'autodoc','combat-drone','servitor')),
    kind_code text NOT NULL CHECK (kind_code IN ('robot','drone')),
    strength integer NOT NULL CHECK (strength>=0),
    dexterity integer NOT NULL CHECK (dexterity>=0),
    hull integer NOT NULL CHECK (hull>0),
    structure integer NOT NULL CHECK (structure>0),
    intelligence integer,
    education integer,
    social_standing integer,
    armor integer CHECK (armor>=0),
    price_excludes_selected_weapon boolean NOT NULL DEFAULT false,
    cargo_drone_variant_minimum_tech_level integer,
    cargo_drone_pre_intellect_utility_extremely_limited boolean NOT NULL
        DEFAULT false,
    CHECK (
        (kind_code='robot' AND intelligence IS NOT NULL
         AND education IS NOT NULL AND social_standing IS NOT NULL)
        OR
        (kind_code='drone' AND intelligence IS NULL
         AND education IS NULL AND social_standing IS NULL)),
    CHECK (
        (chassis_code='combat-drone' AND price_excludes_selected_weapon)
        OR
        (chassis_code<>'combat-drone' AND NOT price_excludes_selected_weapon)),
    CHECK (
        (chassis_code='cargo-robot'
         AND cargo_drone_variant_minimum_tech_level=9
         AND cargo_drone_pre_intellect_utility_extremely_limited)
        OR
        (chassis_code<>'cargo-robot'
         AND cargo_drone_variant_minimum_tech_level IS NULL
         AND NOT cargo_drone_pre_intellect_utility_extremely_limited))
);

COMMENT ON TABLE inv_personal_robot_drone_chassis IS
    'CE-EQUIP-016 exact paired-source chassis characteristics and base prices.';
