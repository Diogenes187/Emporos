CREATE TABLE inv_personal_shelter_definition (
    item_rule_id bigint PRIMARY KEY REFERENCES inv_item_definition(rule_id),
    shelter_code text NOT NULL UNIQUE CHECK (
        shelter_code IN (
            'tarpaulin','tent','pre-fabricated-cabin',
            'basic-life-support-supplies','pressure-tent','advanced-base'))
);

CREATE TABLE rule_personal_shelter_capability (
    shelter_rule_id bigint PRIMARY KEY REFERENCES
        inv_personal_shelter_definition(item_rule_id),
    person_capacity integer CHECK (person_capacity>0),
    pressurization_code text NOT NULL CHECK (
        pressurization_code IN (
            'not-applicable','unpressurized','pressurized-standard')),
    precipitation_protection boolean NOT NULL,
    storm_protection boolean NOT NULL,
    wind_resistance_code text NOT NULL CHECK (
        wind_resistance_code IN (
            'not-stated','light-to-moderate','light-to-severe',
            'up-to-strong','below-hurricane')),
    temperature_protection_code text NOT NULL CHECK (
        temperature_protection_code IN (
            'not-stated','down-to-celsius','all-but-most-extreme')),
    minimum_temperature_celsius integer,
    assembly_person_hours integer CHECK (assembly_person_hours>0),
    dismantling_person_hours integer CHECK (dismantling_person_hours>0),
    included_life_support_person_days integer CHECK (
        included_life_support_person_days>0),
    supplied_life_support_person_days integer CHECK (
        supplied_life_support_person_days>0),
    has_airlock boolean,
    depressurize_to_enter_or_leave boolean,
    length_metres numeric CHECK (length_metres>0),
    width_metres numeric CHECK (width_metres>0),
    CHECK (
        (temperature_protection_code='down-to-celsius'
         AND minimum_temperature_celsius IS NOT NULL)
        OR
        (temperature_protection_code<>'down-to-celsius'
         AND minimum_temperature_celsius IS NULL)),
    CHECK (
        has_airlock IS NULL
        OR pressurization_code='pressurized-standard'),
    CHECK (
        depressurize_to_enter_or_leave IS NULL
        OR pressurization_code='pressurized-standard')
);

CREATE TABLE rule_personal_modular_shelter_geometry (
    shelter_rule_id bigint PRIMARY KEY REFERENCES
        inv_personal_shelter_definition(item_rule_id),
    module_count integer NOT NULL CHECK (module_count=16),
    module_width_metres numeric NOT NULL CHECK (module_width_metres=1.5),
    module_length_metres numeric NOT NULL CHECK (module_length_metres=1.5),
    module_height_metres numeric NOT NULL CHECK (module_height_metres=2),
    layout_is_reconfigurable boolean NOT NULL CHECK (layout_is_reconfigurable)
);

COMMENT ON TABLE inv_personal_shelter_definition IS
    'CE-EQUIP-021 exact paired-source Shelters catalogue.';
