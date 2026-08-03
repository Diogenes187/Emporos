CREATE TABLE rule_personal_computer_catalogue (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    simultaneous_program_capacity_equals_model boolean NOT NULL CHECK (
        simultaneous_program_capacity_equals_model
    ),
    unlimited_storage_minimum_tech_level integer NOT NULL CHECK (
        unlimited_storage_minimum_tech_level=9
    ),
    desktop_mechanical_rating_bonus integer NOT NULL CHECK (
        desktop_mechanical_rating_bonus=0
    ),
    desktop_obsolete_during_tech_level integer NOT NULL CHECK (
        desktop_obsolete_during_tech_level=8
    )
);

CREATE TABLE inv_personal_computer_definition (
    item_rule_id bigint PRIMARY KEY REFERENCES
        inv_item_definition(rule_id),
    computer_kind text NOT NULL CHECK (
        computer_kind IN ('laptop','hand-computer','terminal')
    ),
    optimum_tech_level integer NOT NULL CHECK (optimum_tech_level>=0),
    model_rating integer NOT NULL CHECK (model_rating>=0),
    battery_duration_seconds integer CHECK (
        battery_duration_seconds>0
    ),
    battery_basis text NOT NULL CHECK (
        battery_basis IN (
            'finite','effectively-unlimited','not-stated'
        )
    ),
    battery_effectively_unlimited boolean NOT NULL,
    storage_effectively_unlimited boolean NOT NULL,
    cost_basis text NOT NULL CHECK (
        cost_basis IN (
            'published-table','twice-standard-same-tl','fixed-description'
        )
    ),
    source_mass_is_unquantified boolean NOT NULL,
    operates_without_network boolean NOT NULL,
    interface_only boolean NOT NULL,
    one_hand_operation boolean NOT NULL,
    CHECK (
        (battery_basis='finite'
         AND battery_duration_seconds IS NOT NULL
         AND NOT battery_effectively_unlimited)
        OR
        (battery_basis='effectively-unlimited'
         AND battery_duration_seconds IS NULL
         AND battery_effectively_unlimited)
        OR
        (battery_basis='not-stated'
         AND battery_duration_seconds IS NULL
         AND NOT battery_effectively_unlimited)
    ),
    CHECK (
        storage_effectively_unlimited=(optimum_tech_level>=9)
    ),
    CHECK (
        (computer_kind='laptop'
         AND cost_basis='published-table'
         AND NOT source_mass_is_unquantified
         AND operates_without_network
         AND NOT interface_only
         AND NOT one_hand_operation)
        OR
        (computer_kind='hand-computer'
         AND cost_basis='twice-standard-same-tl'
         AND source_mass_is_unquantified
         AND operates_without_network
         AND NOT interface_only
         AND one_hand_operation)
        OR
        (computer_kind='terminal'
         AND cost_basis='fixed-description'
         AND source_mass_is_unquantified
         AND NOT operates_without_network
         AND interface_only
         AND NOT one_hand_operation)
    ),
    CHECK (
        (computer_kind='terminal')=(battery_basis='not-stated')
    )
);

CREATE TABLE rule_personal_computer_form_factor (
    form_factor_code text PRIMARY KEY CHECK (
        form_factor_code IN ('laptop','desktop')
    ),
    same_cost_as_laptop boolean NOT NULL CHECK (same_cost_as_laptop),
    mechanical_rating_modifier integer NOT NULL CHECK (
        mechanical_rating_modifier=0
    ),
    obsolete_during_tech_level integer,
    CHECK (
        (form_factor_code='laptop'
         AND obsolete_during_tech_level IS NULL)
        OR
        (form_factor_code='desktop'
         AND obsolete_during_tech_level=8)
    )
);

COMMENT ON TABLE inv_personal_computer_definition IS
    'CE-EQUIP-005 exact standard, handheld, and terminal computer profiles.';
