CREATE TABLE rule_book1_vehicle_capability (
    vehicle_profile_rule_id bigint PRIMARY KEY REFERENCES
        rule_book1_vehicle_profile(rule_id),
    cargo_capacity_kg integer CHECK (cargo_capacity_kg>=0),
    orbit_duration_basis text CHECK (
        orbit_duration_basis IN ('world-size-hours','one-hour')),
    vacc_suit_required_at_orbit_altitude boolean NOT NULL DEFAULT false,
    pressurized boolean NOT NULL DEFAULT false,
    floats_on_calm_water boolean NOT NULL DEFAULT false,
    built_in_sensors boolean NOT NULL DEFAULT false,
    built_in_communications boolean NOT NULL DEFAULT false,
    unarmed_turret_hardpoint boolean NOT NULL DEFAULT false,
    minimum_atmosphere_density_code text CHECK (
        minimum_atmosphere_density_code='thin'),
    battery_duration_seconds integer CHECK (battery_duration_seconds>0),
    vehicle_options_prohibited boolean NOT NULL DEFAULT false,
    serious_firepower_rules boolean NOT NULL DEFAULT false,
    weapon_radiation_leak boolean,
    ubiquitous_reliable_flexible boolean NOT NULL DEFAULT false
);

CREATE TABLE rule_book1_grav_belt_battery (
    vehicle_profile_rule_id bigint NOT NULL REFERENCES
        rule_book1_vehicle_profile(rule_id),
    minimum_tech_level smallint NOT NULL CHECK (
        minimum_tech_level IN (12,15)),
    duration_seconds integer NOT NULL CHECK (
        (minimum_tech_level=12 AND duration_seconds=14400)
        OR
        (minimum_tech_level=15 AND duration_seconds=43200)),
    PRIMARY KEY (vehicle_profile_rule_id,minimum_tech_level)
);

CREATE TABLE rule_book1_afv_laser_fire (
    vehicle_profile_rule_id bigint PRIMARY KEY REFERENCES
        rule_book1_vehicle_profile(rule_id),
    attack_skill_rule_id bigint NOT NULL REFERENCES rule_skill(rule_id),
    damage_dice_count smallint NOT NULL CHECK (damage_dice_count=4),
    damage_die_sides smallint NOT NULL CHECK (damage_die_sides=6),
    range_profile_code text NOT NULL CHECK (
        range_profile_code='ranged-rifle'),
    minimum_lasers_per_attack smallint NOT NULL CHECK (
        minimum_lasers_per_attack=1),
    maximum_lasers_per_attack smallint NOT NULL CHECK (
        maximum_lasers_per_attack=3),
    single_attack_action boolean NOT NULL CHECK (single_attack_action)
);

COMMENT ON TABLE rule_book1_vehicle_capability IS
    'CE-EQUIP-026 Book 1 profile-specific vehicle operating capabilities.';
