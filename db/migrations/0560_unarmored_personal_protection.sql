WITH package AS (
 SELECT content_package_id FROM sys_content_package
 WHERE package_code='cepheus-engine' AND package_version='9.1-draft'
), inserted_rule AS (
 INSERT INTO rule_rule(content_package_id,rule_code,name,rule_category,rule_status,description)
 SELECT content_package_id,'combat.armor.unarmored','Unarmored','combat','released',
        'Computational zero-protection profile used only when no armor is worn.'
 FROM package
 ON CONFLICT(content_package_id,rule_code) DO UPDATE SET
  name=EXCLUDED.name,rule_category=EXCLUDED.rule_category,
  rule_status=EXCLUDED.rule_status,description=EXCLUDED.description
 RETURNING rule_id
)
INSERT INTO inv_item_definition(rule_id,item_kind,minimum_tech_level,cost_credits,mass_grams)
SELECT rule_id,'armor',NULL,NULL,0 FROM inserted_rule
ON CONFLICT(rule_id) DO UPDATE SET item_kind='armor',minimum_tech_level=NULL,cost_credits=NULL,mass_grams=0;

INSERT INTO inv_armor_definition(item_rule_id,general_armor_rating,laser_armor_rating,required_skill_rule_id,catalogue_display_order,laser_rating_explicit)
SELECT rule_id,0,0,NULL,NULL,false FROM rule_rule WHERE rule_code='combat.armor.unarmored'
ON CONFLICT(item_rule_id) DO UPDATE SET general_armor_rating=0,laser_armor_rating=0,
 required_skill_rule_id=NULL,catalogue_display_order=NULL,laser_rating_explicit=false;

INSERT INTO rule_interpretation(rule_id,interpretation_type,decision_register_entry,rationale)
SELECT rule_id,'agreed_interpretation','CE-COMBAT-027',
 'The sources subtract only armor being worn. When none is worn, the executable reduction is zero; this profile is not equipment and cannot be purchased or equipped.'
FROM rule_rule WHERE rule_code='combat.armor.unarmored'
ON CONFLICT DO NOTHING;

INSERT INTO src_issue(issue_code,domain_code,issue_type,review_priority,issue_status,
 subject_code,title,problem_statement,published_value,calculated_value,reviewer_question,
 requested_evidence,engine_disposition,resolved_at,resolution_summary)
VALUES('combat.personal.unarmored-zero-protection','combat.personal','source_omission','low','resolved',
 'combat.armor.unarmored','Unarmored computational profile',
 'The sources define damage reduction from armor being worn but do not name an unarmored armor-catalog entry for executable attack resolution.',
 'Subtract the value of armor being worn','No worn armor subtracts 0 damage',
 'What armor profile should the engine use when the target wears none?',
 'Compare the personal-combat and equipment armor rules in the checked Cepheus sources.',
 'preserve_rule',clock_timestamp(),
 'CE-COMBAT-027 records an AR 0 computational profile, excluded from the purchasable catalog and selected automatically only when no armor is equipped.')
ON CONFLICT(issue_code) DO NOTHING;

INSERT INTO src_issue_locator(source_issue_id,source_locator_id,evidence_role)
SELECT issue.source_issue_id,locator.source_locator_id,
 CASE WHEN work.work_code='cepheus-engine.github-v9.1' THEN 'primary' ELSE 'corroborating' END
FROM src_issue issue
JOIN src_locator locator ON locator.heading_path='Equipment > Armor'
JOIN src_work work USING(source_work_id)
WHERE issue.issue_code='combat.personal.unarmored-zero-protection'
 AND work.work_code IN('cepheus-engine.github-v9.1','cepheus-engine.ogn')
ON CONFLICT DO NOTHING;
