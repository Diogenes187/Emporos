CREATE TABLE inv_personal_drug_definition (
    item_rule_id bigint PRIMARY KEY REFERENCES inv_item_definition(rule_id),
    drug_code text NOT NULL UNIQUE CHECK (
        drug_code IN (
            'medicinal','anti-radiation','panacea','stim','combat',
            'fast','metabolic-accelerator','medicinal-slow','anagathic')),
    catalogue_tech_level integer NOT NULL CHECK (catalogue_tech_level>=0),
    cost_basis text NOT NULL CHECK (
        cost_basis IN ('fixed','minimum-plus-variable')),
    minimum_cost_credits bigint NOT NULL CHECK (minimum_cost_credits>=0),
    fixed_cost_credits bigint CHECK (fixed_cost_credits>=0),
    variable_cost_dice_count integer,
    variable_cost_die_sides integer,
    variable_cost_multiplier_credits bigint,
    source_mass_is_unquantified boolean NOT NULL CHECK (
        source_mass_is_unquantified),
    CHECK (
        (cost_basis='fixed'
         AND fixed_cost_credits=minimum_cost_credits
         AND variable_cost_dice_count IS NULL
         AND variable_cost_die_sides IS NULL
         AND variable_cost_multiplier_credits IS NULL)
        OR
        (cost_basis='minimum-plus-variable'
         AND fixed_cost_credits IS NULL
         AND variable_cost_dice_count=1
         AND variable_cost_die_sides=6
         AND variable_cost_multiplier_credits=1000))
);

CREATE TABLE rule_anagathic_availability (
    drug_rule_id bigint PRIMARY KEY REFERENCES
        inv_personal_drug_definition(item_rule_id),
    catalogue_tech_level integer NOT NULL CHECK (catalogue_tech_level=11),
    synthetic_minimum_tech_level integer NOT NULL CHECK (
        synthetic_minimum_tech_level=15),
    natural_forms_all_tech_levels boolean NOT NULL CHECK (
        natural_forms_all_tech_levels),
    illegal_or_heavily_controlled_on_many_worlds boolean NOT NULL CHECK (
        illegal_or_heavily_controlled_on_many_worlds)
);

COMMENT ON TABLE inv_personal_drug_definition IS
    'CE-EQUIP-009 paired-source drug catalogue without invented mass.';
