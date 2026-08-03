CREATE TABLE rule_psi_suspended_animation (
    power_rule_id bigint PRIMARY KEY REFERENCES psi_power(power_rule_id),
    duration_days smallint NOT NULL CHECK (duration_days=7),
    food_required boolean NOT NULL CHECK (NOT food_required),
    water_required boolean NOT NULL CHECK (NOT water_required),
    air_requirement text NOT NULL CHECK (air_requirement='minimal'),
    early_waking_requires_external_stimulus boolean NOT NULL CHECK (
        early_waking_requires_external_stimulus
    ),
    cold_sleep_death_risk boolean NOT NULL CHECK (NOT cold_sleep_death_risk),
    self_only boolean NOT NULL CHECK (self_only)
);

CREATE TABLE rule_psi_characteristic_enhancement (
    power_rule_id bigint PRIMARY KEY REFERENCES psi_power(power_rule_id),
    characteristic_rule_id bigint NOT NULL UNIQUE
        REFERENCES rule_characteristic(rule_id),
    psionic_cost_per_point smallint NOT NULL CHECK (
        psionic_cost_per_point=1
    ),
    points_capped_by_awareness_level boolean NOT NULL CHECK (
        points_capped_by_awareness_level
    ),
    racial_maximum_applies boolean NOT NULL CHECK (racial_maximum_applies),
    peak_duration_minutes smallint NOT NULL CHECK (
        peak_duration_minutes=10
    ),
    decline_points smallint NOT NULL CHECK (decline_points=1),
    decline_interval_minutes smallint NOT NULL CHECK (
        decline_interval_minutes=1
    ),
    returns_to_wounded_value boolean NOT NULL CHECK (
        returns_to_wounded_value
    ),
    permits_healing boolean NOT NULL CHECK (NOT permits_healing),
    self_only boolean NOT NULL CHECK (self_only)
);

CREATE TABLE rule_psi_regeneration (
    power_rule_id bigint PRIMARY KEY REFERENCES psi_power(power_rule_id),
    psionic_cost_per_point smallint NOT NULL CHECK (
        psionic_cost_per_point=1
    ),
    maximum_per_use smallint,
    reusable_after_all_spent_psi_recovered boolean NOT NULL CHECK (
        reusable_after_all_spent_psi_recovered
    ),
    permits_new_limbs_or_organs boolean NOT NULL CHECK (
        permits_new_limbs_or_organs
    ),
    permits_old_wound_healing boolean NOT NULL CHECK (
        permits_old_wound_healing
    ),
    permits_aging_reversal boolean NOT NULL CHECK (
        NOT permits_aging_reversal
    ),
    self_only boolean NOT NULL CHECK (self_only),
    CHECK (maximum_per_use IS NULL OR maximum_per_use>0)
);

CREATE TABLE rule_psi_regeneration_characteristic (
    power_rule_id bigint NOT NULL REFERENCES
        rule_psi_regeneration(power_rule_id),
    characteristic_rule_id bigint NOT NULL REFERENCES
        rule_characteristic(rule_id),
    PRIMARY KEY (power_rule_id,characteristic_rule_id)
);

COMMENT ON TABLE rule_psi_suspended_animation IS
    'CE-PSI-002 paired-source Awareness suspended-animation mechanics.';
COMMENT ON TABLE rule_psi_characteristic_enhancement IS
    'CE-PSI-002 paired-source Awareness Strength and Endurance enhancement mechanics.';
COMMENT ON TABLE rule_psi_regeneration IS
    'CE-PSI-002 paired-source Awareness regeneration mechanics.';
