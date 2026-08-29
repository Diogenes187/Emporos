-- Resolve the last two printed career outcomes that could stop a lifepath.
-- Perception is printed but never defined; Liaision-1 is the source's typo for
-- the already-defined Liaison skill.
WITH package AS (
    SELECT content_package_id FROM sys_content_package
    WHERE package_code='cepheus-engine'
)
INSERT INTO rule_rule(
    content_package_id,rule_code,name,rule_category,rule_status,description
)
SELECT content_package_id,'skill.perception','Perception','skill','approved',
       'Notice significant details and immediate sensory cues. The career '
       'tables print this skill, but the source supplies no separate definition.'
FROM package
ON CONFLICT(content_package_id,rule_code) DO NOTHING;

INSERT INTO rule_skill(rule_id,cascade_skill,permits_untrained,untrained_modifier)
SELECT rule_id,false,true,-3 FROM rule_rule
WHERE rule_code='skill.perception'
ON CONFLICT(rule_id) DO NOTHING;

INSERT INTO src_record_provenance(
    rule_id,content_package_id,source_locator_id,
    provenance_class,is_primary_citation
)
SELECT skill.rule_id,skill.content_package_id,
       provenance.source_locator_id,
       CASE work.work_code
           WHEN 'cepheus-engine.github-v9.1' THEN 'fills_source_gap'
           ELSE 'corroborating'
       END,
       work.work_code='cepheus-engine.github-v9.1'
FROM rule_rule skill
JOIN rule_career_training_entry entry
  ON entry.source_outcome_text='Perception'
JOIN src_career_training_entry_provenance provenance
  USING(career_training_entry_id)
JOIN src_locator locator USING(source_locator_id)
JOIN src_work work USING(source_work_id)
WHERE skill.rule_code='skill.perception'
ON CONFLICT DO NOTHING;

UPDATE rule_career_training_entry
SET outcome_kind='skill',
    skill_rule_id=(SELECT rule_id FROM rule_rule WHERE rule_code='skill.perception'),
    characteristic_rule_id=NULL,
    characteristic_increase=NULL,
    fixed_skill_level=NULL
WHERE source_outcome_text='Perception'
  AND outcome_kind='text';

UPDATE rule_career_rank
SET granted_skill_rule_id=(
        SELECT rule_id FROM rule_rule WHERE rule_code='skill.liaison'
    ),
    granted_skill_level=1
WHERE source_grant_text='Liaision-1'
  AND granted_skill_rule_id IS NULL;
