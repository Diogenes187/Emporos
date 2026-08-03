CREATE TABLE rule_book1_melee_attack (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    entry_code text NOT NULL UNIQUE CHECK (entry_code IN (
        'unarmed-strike','cudgel','dagger','spear','pike','sword',
        'broadsword','halberd','bayonet','blade','cutlass','foil')),
    weapon_item_rule_id bigint UNIQUE REFERENCES
        inv_weapon_definition(item_rule_id),
    source_tech_level_is_unquantified boolean NOT NULL,
    source_cost_is_unquantified boolean NOT NULL,
    source_mass_is_unquantified boolean NOT NULL,
    damage_dice_count smallint NOT NULL CHECK (damage_dice_count>0),
    damage_die_sides smallint NOT NULL CHECK (damage_die_sides=6),
    illegal_at_law_level smallint CHECK (illegal_at_law_level>=0),
    CHECK (
        (entry_code='unarmed-strike' AND weapon_item_rule_id IS NULL
         AND source_tech_level_is_unquantified
         AND source_cost_is_unquantified
         AND source_mass_is_unquantified
         AND illegal_at_law_level IS NULL)
        OR
        (entry_code<>'unarmed-strike' AND weapon_item_rule_id=rule_id
         AND NOT source_tech_level_is_unquantified
         AND NOT source_cost_is_unquantified
         AND NOT source_mass_is_unquantified))
);

CREATE TABLE rule_book1_melee_attack_mode (
    melee_attack_rule_id bigint NOT NULL REFERENCES
        rule_book1_melee_attack(rule_id),
    attack_profile_code text NOT NULL REFERENCES
        combat_attack_profile(attack_profile_code),
    display_order smallint NOT NULL CHECK (display_order>0),
    PRIMARY KEY (melee_attack_rule_id,attack_profile_code),
    UNIQUE (melee_attack_rule_id,display_order),
    CHECK (attack_profile_code IN (
        'close-quarters','extended-reach','thrown'))
);

COMMENT ON TABLE rule_book1_melee_attack IS
    'CE-EQUIP-028 exact Book 1 melee table; Unarmed Strike is not inventory.';
