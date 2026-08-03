CREATE TABLE rule_book1_ranged_weapon_capability (
    weapon_item_rule_id bigint PRIMARY KEY REFERENCES
        inv_weapon_definition(item_rule_id),
    designed_for_zero_gravity boolean NOT NULL DEFAULT false,
    adjustable_single_fire boolean NOT NULL DEFAULT false,
    nonmetallic boolean NOT NULL DEFAULT false,
    evades_most_weapon_detectors boolean NOT NULL DEFAULT false,
    uses_external_power_pack boolean NOT NULL DEFAULT false,
    power_pack_connected_by_cable boolean NOT NULL DEFAULT false,
    integrated_optic_sights boolean NOT NULL DEFAULT false,
    beam_diameter_mm numeric CHECK (beam_diameter_mm>0),
    CHECK (NOT evades_most_weapon_detectors OR nonmetallic),
    CHECK (NOT power_pack_connected_by_cable OR uses_external_power_pack)
);

CREATE TABLE rule_book1_crossbow_reload_profile (
    weapon_item_rule_id bigint NOT NULL REFERENCES
        inv_weapon_definition(item_rule_id),
    minimum_tech_level smallint NOT NULL CHECK (
        minimum_tech_level IN (2,4,9)),
    reload_minor_actions smallint CHECK (reload_minor_actions>0),
    self_loading boolean NOT NULL,
    PRIMARY KEY (weapon_item_rule_id,minimum_tech_level),
    CHECK ((minimum_tech_level=9)=self_loading),
    CHECK (self_loading=(reload_minor_actions IS NULL))
);

CREATE TABLE rule_book1_ranged_mode_switch (
    weapon_item_rule_id bigint PRIMARY KEY REFERENCES
        inv_weapon_definition(item_rule_id),
    switch_timing text NOT NULL CHECK (
        switch_timing='end-of-round-after-all-firing'),
    alternate_mode_attack_profile_code text NOT NULL REFERENCES
        combat_attack_profile(attack_profile_code),
    alternate_single_shot_rounds smallint NOT NULL CHECK (
        alternate_single_shot_rounds=1)
);

CREATE TABLE rule_book1_revolver_reload_choice (
    weapon_item_rule_id bigint PRIMARY KEY REFERENCES
        inv_weapon_definition(item_rule_id),
    normal_reload_combat_rounds smallint NOT NULL CHECK (
        normal_reload_combat_rounds=2),
    expedited_reload_combat_rounds smallint NOT NULL CHECK (
        expedited_reload_combat_rounds=1),
    expedited_reload_forfeits_evasion boolean NOT NULL CHECK (
        expedited_reload_forfeits_evasion)
);

CREATE TABLE rule_book1_ammunition_compatibility (
    first_weapon_rule_id bigint NOT NULL REFERENCES
        inv_weapon_definition(item_rule_id),
    second_weapon_rule_id bigint NOT NULL REFERENCES
        inv_weapon_definition(item_rule_id),
    ammunition_interchangeable boolean NOT NULL,
    magazines_interchangeable boolean NOT NULL,
    PRIMARY KEY (first_weapon_rule_id,second_weapon_rule_id),
    CHECK (first_weapon_rule_id<second_weapon_rule_id),
    CHECK (NOT magazines_interchangeable OR ammunition_interchangeable)
);

COMMENT ON TABLE rule_book1_ranged_weapon_capability IS
    'CE-EQUIP-031 typed operational facts from ranged weapon descriptions.';
