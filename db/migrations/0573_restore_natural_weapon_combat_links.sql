INSERT INTO combat_attack_profile_difficulty (
    attack_profile_code,range_band_rule_id,difficulty_rule_id,permitted
)
SELECT 'natural-weapon',range.rule_id,
       CASE WHEN range.rule_code='combat.range.personal'
            THEN difficulty.rule_id ELSE NULL END,
       range.rule_code='combat.range.personal'
FROM combat_range_band band
JOIN rule_rule range ON range.rule_id=band.rule_id
LEFT JOIN rule_rule difficulty ON difficulty.rule_code='difficulty.average'
ON CONFLICT (attack_profile_code,range_band_rule_id) DO NOTHING;

INSERT INTO inv_weapon_attack_mode (
    item_rule_id,attack_profile_code,display_order
)
SELECT rule_id,'natural-weapon',1
FROM rule_rule
WHERE rule_code='equipment.weapon.species-natural-weapon'
ON CONFLICT (item_rule_id,attack_profile_code) DO NOTHING;
