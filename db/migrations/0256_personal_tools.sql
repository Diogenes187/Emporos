CREATE TABLE inv_personal_tool_definition (
    item_rule_id bigint PRIMARY KEY REFERENCES inv_item_definition(rule_id),
    tool_code text NOT NULL UNIQUE CHECK (
        tool_code IN (
            'mechanical-toolkit','electronics-toolkit','lock-pick-set',
            'medical-kit','forensics-toolkit','engineering-toolkit',
            'scientific-toolkit','surveying-toolkit')),
    catalogue_mass_is_unquantified boolean NOT NULL,
    CHECK (
        catalogue_mass_is_unquantified=(tool_code='lock-pick-set'))
);

CREATE TABLE rule_personal_tool_operation (
    tool_rule_id bigint NOT NULL REFERENCES
        inv_personal_tool_definition(item_rule_id),
    operation_code text NOT NULL CHECK (
        operation_code IN (
            'repairs','construction','electrical-repairs',
            'electrical-installations','ordinary-mechanical-lock-picking',
            'field-medicine','crime-scene-investigation','sample-testing',
            'equipment-repairs','equipment-installation',
            'scientific-testing','scientific-analysis',
            'planetary-survey','mapping')),
    required_for_operation boolean NOT NULL,
    skill_rule_id bigint REFERENCES rule_skill(rule_id),
    PRIMARY KEY (tool_rule_id,operation_code)
);

CREATE TABLE rule_personal_tool_law_price (
    tool_rule_id bigint PRIMARY KEY REFERENCES
        inv_personal_tool_definition(item_rule_id),
    illegal_at_or_above_law_level smallint NOT NULL REFERENCES
        rule_world_law_level(law_level_code),
    minimum_illegal_market_cost_credits bigint NOT NULL CHECK (
        minimum_illegal_market_cost_credits=100),
    illegal_market_cost_is_floor boolean NOT NULL CHECK (
        illegal_market_cost_is_floor)
);

COMMENT ON TABLE inv_personal_tool_definition IS
    'CE-EQUIP-024 paired-source Tools catalogue and relational functions.';
