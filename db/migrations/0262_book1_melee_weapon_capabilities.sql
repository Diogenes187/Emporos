CREATE TABLE rule_book1_melee_weapon_capability (
    weapon_item_rule_id bigint PRIMARY KEY REFERENCES
        inv_weapon_definition(item_rule_id),
    minimum_length_mm integer CHECK (minimum_length_mm>0),
    maximum_length_mm integer CHECK (
        maximum_length_mm>=minimum_length_mm),
    length_measurement_basis text CHECK (
        length_measurement_basis IN ('exact','approximate','range')),
    requires_two_hands boolean NOT NULL DEFAULT false,
    worn_mass_ignored_for_load boolean NOT NULL DEFAULT false,
    utility_tool boolean NOT NULL DEFAULT false,
    survival_tool boolean NOT NULL DEFAULT false,
    commonly_found_in_emergency_kits boolean NOT NULL DEFAULT false,
    commonly_found_in_lifeboats boolean NOT NULL DEFAULT false,
    standard_shipboard_blade boolean NOT NULL DEFAULT false,
    frequently_attached_to_rifle boolean NOT NULL DEFAULT false,
    unattached_equivalent_weapon_rule_id bigint REFERENCES
        inv_weapon_definition(item_rule_id),
    improvisable_from_standing_tree boolean NOT NULL DEFAULT false,
    improvisable_from_unloaded_long_gun boolean NOT NULL DEFAULT false,
    laser_long_gun_prohibited boolean NOT NULL DEFAULT false,
    CHECK (
        (minimum_length_mm IS NULL AND maximum_length_mm IS NULL
         AND length_measurement_basis IS NULL)
        OR
        (minimum_length_mm IS NOT NULL AND maximum_length_mm IS NOT NULL
         AND length_measurement_basis IS NOT NULL)),
    CHECK (
        NOT laser_long_gun_prohibited
        OR improvisable_from_unloaded_long_gun)
);

COMMENT ON TABLE rule_book1_melee_weapon_capability IS
    'CE-EQUIP-029 exact mechanical facts from Book 1 melee descriptions.';
