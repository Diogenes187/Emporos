CREATE TABLE rule_personal_survival_equipment_capability (
    survival_equipment_rule_id bigint PRIMARY KEY REFERENCES
        inv_personal_survival_equipment_definition(item_rule_id),
    cold_threshold_celsius integer,
    endurance_check_modifier integer,
    mass_reduction_grams_per_tech_interval integer,
    tech_level_interval integer,
    operating_duration_seconds integer,
    duration_is_unlimited boolean NOT NULL DEFAULT false,
    refill_cost_credits integer,
    units_per_full_set integer,
    life_support_person_hours integer,
    diameter_metres numeric,
    protects_from_smoke boolean NOT NULL DEFAULT false,
    protects_from_dust boolean NOT NULL DEFAULT false,
    protects_from_gas boolean NOT NULL DEFAULT false,
    protects_from_extreme_cold boolean NOT NULL DEFAULT false,
    protects_from_extreme_heat boolean NOT NULL DEFAULT false,
    face_exposed_in_normal_operation boolean NOT NULL DEFAULT false,
    pressurized boolean NOT NULL DEFAULT false,
    self_repairing_emergency_airlock boolean NOT NULL DEFAULT false,
    movement_recharges_batteries boolean NOT NULL DEFAULT false,
    distress_beacon boolean NOT NULL DEFAULT false,
    recharges_weapons_and_equipment boolean NOT NULL DEFAULT false,
    microgravity_only boolean NOT NULL DEFAULT false,
    adjacent_spacecraft_journeys_only boolean NOT NULL DEFAULT false,
    CHECK (operating_duration_seconds IS NULL OR operating_duration_seconds>0),
    CHECK (refill_cost_credits IS NULL OR refill_cost_credits>=0),
    CHECK (units_per_full_set IS NULL OR units_per_full_set>0),
    CHECK (life_support_person_hours IS NULL OR life_support_person_hours>0),
    CHECK (diameter_metres IS NULL OR diameter_metres>0)
);

CREATE TABLE rule_personal_survival_equipment_atmosphere (
    survival_equipment_rule_id bigint NOT NULL REFERENCES
        inv_personal_survival_equipment_definition(item_rule_id),
    atmosphere_code smallint NOT NULL REFERENCES
        rule_world_atmosphere(atmosphere_code),
    PRIMARY KEY (survival_equipment_rule_id,atmosphere_code)
);

CREATE TABLE rule_personal_survival_equipment_skill (
    survival_equipment_rule_id bigint NOT NULL REFERENCES
        inv_personal_survival_equipment_definition(item_rule_id),
    skill_rule_id bigint NOT NULL REFERENCES rule_skill(rule_id),
    task_modifier integer,
    check_required_for_accurate_use boolean NOT NULL DEFAULT false,
    PRIMARY KEY (survival_equipment_rule_id,skill_rule_id)
);

COMMENT ON TABLE rule_personal_survival_equipment_capability IS
    'CE-EQUIP-023 normalized Survival Equipment operating mechanics.';
