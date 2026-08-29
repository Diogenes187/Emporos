-- Prospecting is printed twice in the Belter training tables but omitted from
-- the SRD's skill definitions. Preserve that source gap while making the
-- printed career result playable as a normal, non-cascade skill.
WITH package AS (
    SELECT content_package_id
    FROM sys_content_package
    WHERE package_code='cepheus-engine'
)
INSERT INTO rule_rule (
    content_package_id,rule_code,name,rule_category,rule_status,description
)
SELECT content_package_id,'skill.prospecting','Prospecting','skill','approved',
       'Locate and assess potentially valuable natural deposits. The career '
       'tables print this skill, but the source supplies no separate skill definition.'
FROM package
ON CONFLICT (content_package_id,rule_code) DO NOTHING;

INSERT INTO rule_skill(rule_id,cascade_skill,permits_untrained,untrained_modifier)
SELECT rule_id,false,true,-3
FROM rule_rule
WHERE rule_code='skill.prospecting'
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO src_record_provenance(
    rule_id,content_package_id,source_locator_id,
    provenance_class,is_primary_citation
)
SELECT skill.rule_id,skill.content_package_id,locator.source_locator_id,
       CASE work.work_code
           WHEN 'cepheus-engine.github-v9.1' THEN 'fills_source_gap'
           ELSE 'corroborating'
       END,
       work.work_code='cepheus-engine.github-v9.1'
FROM rule_rule skill
JOIN src_locator locator
  ON locator.heading_path='Character Creation > Career Tables'
 AND locator.display_citation='Belter'
JOIN src_work work USING(source_work_id)
WHERE skill.rule_code='skill.prospecting'
ON CONFLICT DO NOTHING;

UPDATE rule_career_training_entry
SET outcome_kind='skill',
    skill_rule_id=(SELECT rule_id FROM rule_rule WHERE rule_code='skill.prospecting'),
    characteristic_rule_id=NULL,
    characteristic_increase=NULL,
    fixed_skill_level=NULL
WHERE source_outcome_text='Prospecting'
  AND outcome_kind='text';
