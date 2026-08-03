CREATE TABLE rule_personal_communicator_usage (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    routine_use_requires_check boolean NOT NULL CHECK (
        NOT routine_use_requires_check
    ),
    exceptional_use_skill_rule_id bigint NOT NULL REFERENCES
        rule_skill(rule_id)
);

CREATE TABLE inv_communicator_definition (
    item_rule_id bigint PRIMARY KEY REFERENCES
        inv_item_definition(rule_id),
    channel_count integer NOT NULL CHECK (channel_count>0),
    nominal_range_meters integer CHECK (nominal_range_meters>0),
    range_kind text NOT NULL CHECK (
        range_kind IN ('fixed','satellite-network')
    ),
    minimum_operating_world_tech_level integer,
    private_channel boolean NOT NULL,
    secure_channel boolean NOT NULL,
    network_access_fee_required boolean NOT NULL,
    CHECK (
        (range_kind='fixed'
         AND nominal_range_meters IS NOT NULL
         AND minimum_operating_world_tech_level IS NULL)
        OR
        (range_kind='satellite-network'
         AND nominal_range_meters IS NULL
         AND minimum_operating_world_tech_level=8)
    )
);

CREATE TABLE inv_communicator_tech_profile (
    item_rule_id bigint NOT NULL REFERENCES
        inv_communicator_definition(item_rule_id),
    minimum_tech_level integer NOT NULL CHECK (minimum_tech_level>=0),
    mass_grams integer NOT NULL CHECK (mass_grams>0),
    form_factor text NOT NULL CHECK (
        form_factor IN (
            'backpack','belt-or-sling','belt','handheld'
        )
    ),
    PRIMARY KEY (item_rule_id,minimum_tech_level)
);

CREATE TABLE rule_communicator_contact_capability (
    item_rule_id bigint NOT NULL REFERENCES
        inv_communicator_definition(item_rule_id),
    capability_code text NOT NULL CHECK (
        capability_code IN (
            'orbital-ship-contact','official-radio-channels',
            'worldwide-satellite-addressing'
        )
    ),
    PRIMARY KEY (item_rule_id,capability_code)
);

CREATE TABLE rule_communicator_environment_effect (
    item_rule_id bigint NOT NULL REFERENCES
        inv_communicator_definition(item_rule_id),
    environment_code text NOT NULL CHECK (
        environment_code IN ('underground','underwater')
    ),
    effect_kind text NOT NULL CHECK (
        effect_kind='unquantified-range-reduction'
    ),
    PRIMARY KEY (item_rule_id,environment_code)
);

COMMENT ON TABLE inv_communicator_definition IS
    'CE-EQUIP-004 typed personal communications equipment.';
