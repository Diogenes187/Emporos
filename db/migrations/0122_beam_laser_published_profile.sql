UPDATE ship_weapon_definition
SET damage_dice_count=1,
    damage_die_sides=6,
    minimum_tech_level=9,
    optimum_range_code='medium',
    unit_cost_minor=1000000,
    special_effect_code=NULL,
    calculation_status='published'
WHERE weapon_code='beam-laser';

INSERT INTO src_record_provenance (
    rule_id,content_package_id,source_locator_id,
    provenance_class,is_primary_citation
)
SELECT rule.rule_id,rule.content_package_id,
       locator.source_locator_id,'corroborating',false
FROM rule_rule rule
JOIN src_locator locator
  ON locator.heading_path='Space Combat > Damage'
WHERE rule.rule_code='ship.weapon.beam-laser';
