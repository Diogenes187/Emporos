CREATE TABLE rule_personal_starting_range_context (
    context_code text PRIMARY KEY CHECK (
        context_code IN ('tight_quarters','outdoors','open_area')),
    context_order smallint NOT NULL UNIQUE CHECK (context_order>0),
    source_default_range_rule_id bigint REFERENCES combat_range_band(rule_id),
    referee_decides_between_options boolean NOT NULL
);

CREATE TABLE rule_personal_starting_range_option (
    context_code text NOT NULL REFERENCES rule_personal_starting_range_context,
    range_rule_id bigint NOT NULL REFERENCES combat_range_band(rule_id),
    option_order smallint NOT NULL CHECK (option_order>0),
    PRIMARY KEY (context_code,range_rule_id),
    UNIQUE (context_code,option_order)
);

CREATE TABLE rule_personal_starting_range_light_cap (
    light_condition text PRIMARY KEY CHECK (
        light_condition IN ('normal','partial_darkness','total_darkness')),
    maximum_range_rule_id bigint REFERENCES combat_range_band(rule_id),
    CHECK ((light_condition='normal')=(maximum_range_rule_id IS NULL))
);

COMMENT ON TABLE rule_personal_starting_range_context IS
    'CE-COMBAT-020 paired-source battlefield contexts and source defaults.';
COMMENT ON TABLE rule_personal_starting_range_light_cap IS
    'Source-defined visibility ceilings applied before combat initialization.';
