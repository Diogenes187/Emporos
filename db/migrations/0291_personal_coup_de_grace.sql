CREATE TABLE rule_personal_coup_de_grace (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    helpless_target_required boolean NOT NULL CHECK (helpless_target_required),
    melee_weapon_permitted boolean NOT NULL CHECK (melee_weapon_permitted),
    melee_maximum_range_code text NOT NULL CHECK (
        melee_maximum_range_code='close-quarters'
    ),
    ranged_weapon_permitted boolean NOT NULL CHECK (ranged_weapon_permitted),
    ranged_requires_adjacency boolean NOT NULL CHECK (
        ranged_requires_adjacency
    ),
    attack_roll_required boolean NOT NULL CHECK (NOT attack_roll_required),
    automatic_hit boolean NOT NULL CHECK (automatic_hit),
    target_dies boolean NOT NULL CHECK (target_dies)
);

COMMENT ON TABLE rule_personal_coup_de_grace IS
    'CE-COMBAT-017 paired-source helpless-target automatic-hit and death rule.';
