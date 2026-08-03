ALTER TABLE inv_item_definition
    ADD COLUMN inherent boolean NOT NULL DEFAULT false;

ALTER TABLE inv_weapon_definition
    DROP CONSTRAINT inv_weapon_definition_damage_dice_count_check,
    ADD CONSTRAINT inv_weapon_definition_damage_dice_count_check CHECK (
        damage_dice_count >= 0
    ),
    ADD COLUMN flat_damage_bonus smallint NOT NULL DEFAULT 0 CHECK (
        flat_damage_bonus >= 0
    ),
    ADD CONSTRAINT inv_weapon_damage_expression_check CHECK (
        damage_dice_count > 0 OR flat_damage_bonus > 0
    );

ALTER TABLE cmd_attack_receipt
    ADD COLUMN weapon_flat_damage_bonus smallint NOT NULL DEFAULT 0 CHECK (
        weapon_flat_damage_bonus >= 0
    );

ALTER TABLE cmd_attack_receipt
    DROP CONSTRAINT cmd_attack_receipt_damage_components_check,
    ADD CONSTRAINT cmd_attack_receipt_damage_components_check CHECK (
        (
            hit AND raw_damage=rolled_damage+effect_damage
                +kill_aim_damage_bonus+weapon_flat_damage_bonus
        )
        OR
        (
            NOT hit AND rolled_damage=0 AND effect_damage=0
            AND kill_aim_damage_bonus=0 AND weapon_flat_damage_bonus=0
            AND raw_damage=0 AND penetrating_damage=0
        )
    );

INSERT INTO rule_rule (
    content_package_id,rule_code,name,rule_category,rule_status,description
)
SELECT content_package_id,'equipment.weapon.species-natural-weapon',
       'Species Natural Weapon','equipment','approved',
       'An inherent claw, bite, stinger, or equivalent species weapon.'
FROM sys_content_package WHERE package_code='cepheus-engine';

INSERT INTO inv_item_definition (
    rule_id,item_kind,minimum_tech_level,cost_credits,mass_grams,inherent
)
SELECT rule_id,'weapon',NULL,NULL,NULL,true
FROM rule_rule WHERE rule_code='equipment.weapon.species-natural-weapon';

INSERT INTO inv_weapon_definition (
    item_rule_id,damage_dice_count,damage_die_sides,
    illegal_at_law_level,flat_damage_bonus
)
SELECT rule_id,0,6,NULL,1
FROM rule_rule WHERE rule_code='equipment.weapon.species-natural-weapon';

INSERT INTO inv_weapon_damage_type
SELECT rule_id,'piercing'
FROM rule_rule WHERE rule_code='equipment.weapon.species-natural-weapon';

INSERT INTO combat_attack_profile (
    attack_profile_code,name,required_skill_rule_id
)
SELECT 'natural-weapon','Natural Weapon',rule_id
FROM rule_rule WHERE rule_code='skill.natural-weapons';

INSERT INTO combat_attack_profile_difficulty (
    attack_profile_code,range_band_rule_id,difficulty_rule_id,permitted
)
SELECT 'natural-weapon',range.rule_id,
       CASE WHEN range.rule_code='combat.range.personal'
            THEN difficulty.rule_id ELSE NULL END,
       range.rule_code='combat.range.personal'
FROM combat_range_band band
JOIN rule_rule range ON range.rule_id=band.rule_id
LEFT JOIN rule_rule difficulty
  ON difficulty.rule_code='difficulty.average';

INSERT INTO inv_weapon_attack_mode
SELECT rule_id,'natural-weapon',1
FROM rule_rule WHERE rule_code='equipment.weapon.species-natural-weapon';
