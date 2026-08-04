INSERT INTO src_record_provenance(
 rule_id,content_package_id,source_locator_id,provenance_class,is_primary_citation
)
SELECT rule.rule_id,rule.content_package_id,locator.source_locator_id,
       'interpretation',work.work_code='cepheus-engine.ogn'
FROM rule_rule rule
JOIN src_locator locator ON locator.heading_path='Equipment > Armor'
JOIN src_work work USING(source_work_id)
WHERE rule.rule_code='combat.armor.unarmored'
  AND work.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1')
ON CONFLICT DO NOTHING;
