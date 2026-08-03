CREATE TABLE rule_personal_fast_drug (
    drug_rule_id bigint PRIMARY KEY REFERENCES
        inv_personal_drug_definition(item_rule_id),
    metabolic_rate_divisor integer NOT NULL CHECK (
        metabolic_rate_divisor=60),
    subjective_days integer NOT NULL CHECK (subjective_days=1),
    corresponding_actual_months integer NOT NULL CHECK (
        corresponding_actual_months=2),
    prolongs_life_support boolean NOT NULL CHECK (prolongs_life_support),
    cryoberth_substitute boolean NOT NULL CHECK (cryoberth_substitute)
);

CREATE TABLE rule_personal_medicinal_drug (
    drug_rule_id bigint PRIMARY KEY REFERENCES
        inv_personal_drug_definition(item_rule_id),
    required_skill_rule_id bigint NOT NULL REFERENCES rule_skill(rule_id),
    successful_use_counteracts_most_poison_disease boolean NOT NULL CHECK (
        successful_use_counteracts_most_poison_disease),
    resistance_dm_is_positive boolean NOT NULL CHECK (
        resistance_dm_is_positive),
    resistance_dm_is_unquantified boolean NOT NULL CHECK (
        resistance_dm_is_unquantified),
    wrong_drug_difficulty_rule_id bigint NOT NULL REFERENCES
        rule_difficulty(rule_id),
    wrong_drug_poison_damage_dice integer NOT NULL CHECK (
        wrong_drug_poison_damage_dice=1),
    wrong_drug_poison_damage_die_sides integer NOT NULL CHECK (
        wrong_drug_poison_damage_die_sides=6)
);

CREATE TABLE rule_personal_medicinal_slow_drug (
    drug_rule_id bigint PRIMARY KEY REFERENCES
        inv_personal_drug_definition(item_rule_id),
    requires_medical_facility boolean NOT NULL CHECK (
        requires_medical_facility),
    requires_life_support boolean NOT NULL CHECK (requires_life_support),
    requires_cryo_technology boolean NOT NULL CHECK (
        requires_cryo_technology),
    approximate_metabolic_multiplier integer NOT NULL CHECK (
        approximate_metabolic_multiplier=30),
    metabolic_multiplier_is_approximate boolean NOT NULL CHECK (
        metabolic_multiplier_is_approximate),
    healing_months integer NOT NULL CHECK (healing_months=1),
    elapsed_days integer NOT NULL CHECK (elapsed_days=1)
);

CREATE TABLE rule_personal_panacea (
    drug_rule_id bigint PRIMARY KEY REFERENCES
        inv_personal_drug_definition(item_rule_id),
    applicable_to_any_wound_or_illness boolean NOT NULL CHECK (
        applicable_to_any_wound_or_illness),
    guaranteed_not_to_worsen boolean NOT NULL CHECK (
        guaranteed_not_to_worsen),
    granted_medic_skill_level integer NOT NULL CHECK (
        granted_medic_skill_level=0),
    treatment_scope text NOT NULL CHECK (
        treatment_scope='infection-or-disease')
);

CREATE TABLE rule_personal_anagathic_dosing (
    drug_rule_id bigint PRIMARY KEY REFERENCES
        inv_personal_drug_definition(item_rule_id),
    doses_per_interval integer NOT NULL CHECK (doses_per_interval=1),
    interval_unit text NOT NULL CHECK (interval_unit='calendar-month'),
    maintains_slowed_aging boolean NOT NULL CHECK (maintains_slowed_aging),
    missed_dose_immediate_aging_roll boolean NOT NULL CHECK (
        missed_dose_immediate_aging_roll)
);

COMMENT ON TABLE rule_personal_medicinal_drug IS
    'CE-EQUIP-011 preserves the unquantified positive resistance DM.';
