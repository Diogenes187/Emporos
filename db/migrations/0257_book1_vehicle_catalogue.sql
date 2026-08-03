CREATE TABLE rule_book1_vehicle_profile (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    profile_code text NOT NULL UNIQUE,
    vehicle_class_rule_id bigint REFERENCES vehicle_class(vehicle_class_rule_id),
    minimum_tech_level smallint NOT NULL CHECK (minimum_tech_level>=0),
    operating_skill_rule_id bigint NOT NULL REFERENCES rule_skill(rule_id),
    agility_modifier smallint NOT NULL,
    maximum_speed numeric NOT NULL CHECK (maximum_speed>0),
    speed_unit text CHECK (speed_unit='kph'),
    source_speed_unit_is_unquantified boolean NOT NULL,
    configuration text NOT NULL CHECK (configuration IN ('open','closed')),
    armor smallint CHECK (armor>=0),
    hull smallint CHECK (hull>0),
    structure smallint NOT NULL CHECK (structure>0),
    cost_credits bigint NOT NULL CHECK (cost_credits>0),
    CHECK ((speed_unit IS NULL)=source_speed_unit_is_unquantified)
);

CREATE TABLE rule_book1_vehicle_occupancy (
    vehicle_profile_rule_id bigint NOT NULL REFERENCES
        rule_book1_vehicle_profile(rule_id),
    occupant_role text NOT NULL CHECK (
        occupant_role IN ('pilot','driver','crew','gunner','passenger','rider',
                          'wearer')),
    quantity smallint NOT NULL CHECK (quantity>0),
    PRIMARY KEY (vehicle_profile_rule_id,occupant_role)
);

CREATE TABLE rule_book1_vehicle_weapon_summary (
    vehicle_profile_rule_id bigint PRIMARY KEY REFERENCES
        rule_book1_vehicle_profile(rule_id),
    weapon_code text NOT NULL CHECK (
        weapon_code IN ('none','triple-laser','fusion-gun')),
    mount_code text CHECK (mount_code='turret'),
    weapon_count smallint NOT NULL CHECK (weapon_count>=0),
    CHECK (
        (weapon_code='none' AND mount_code IS NULL AND weapon_count=0)
        OR
        (weapon_code<>'none' AND mount_code='turret' AND weapon_count>0))
);

COMMENT ON TABLE rule_book1_vehicle_profile IS
    'CE-EQUIP-025 Book 1 vehicle profiles, distinct from VDS designs.';
