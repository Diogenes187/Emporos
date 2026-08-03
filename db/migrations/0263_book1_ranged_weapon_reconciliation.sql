CREATE TABLE rule_book1_ranged_weapon_fire_profile (
    weapon_item_rule_id bigint PRIMARY KEY REFERENCES
        inv_weapon_definition(item_rule_id),
    single_shot_rounds smallint CHECK (single_shot_rounds>=0),
    burst_shot_rounds smallint CHECK (burst_shot_rounds>0),
    automatic_fire_rounds smallint CHECK (automatic_fire_rounds>0),
    CHECK (single_shot_rounds IS NOT NULL),
    CHECK (
        automatic_fire_rounds IS NULL OR burst_shot_rounds IS NOT NULL)
);

CREATE TABLE rule_book1_ranged_ammunition_listing (
    ammunition_rule_id bigint PRIMARY KEY REFERENCES
        inv_ammunition_definition(ammunition_rule_id),
    source_listing_code text NOT NULL CHECK (btrim(source_listing_code)<>''),
    capacity_variant_rounds smallint NOT NULL CHECK (
        capacity_variant_rounds>0),
    UNIQUE (source_listing_code,capacity_variant_rounds)
);

COMMENT ON TABLE rule_book1_ranged_weapon_fire_profile IS
    'CE-EQUIP-030 normalized single/burst/automatic values from Book 1 RoF.';
COMMENT ON TABLE rule_book1_ranged_ammunition_listing IS
    'CE-EQUIP-030 maps 19 capacity variants to 18 published ammunition rows.';
