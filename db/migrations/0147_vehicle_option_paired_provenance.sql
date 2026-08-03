INSERT INTO src_locator (
    source_work_id,source_artifact_id,locator_type,
    heading_path,display_citation
)
SELECT artifact.source_work_id,artifact.source_artifact_id,
       'heading',source.heading_path,source.display_citation
FROM src_artifact artifact
CROSS JOIN (
    VALUES
        ('Vehicle Design > Vehicle Configuration',
         'Cepheus Engine OGN VDS, Vehicle Configuration'),
        ('Vehicle Design > Vehicle Configuration Options',
         'Cepheus Engine OGN VDS, Vehicle Configuration Options'),
        ('Vehicle Design > Vehicle Drive Options',
         'Cepheus Engine OGN VDS, Vehicle Drive Options')
) source(heading_path,display_citation)
WHERE artifact.source_uri=
    'https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-equipment/cepheus-engine-introduction-2/';

INSERT INTO src_record_provenance (
    rule_id,content_package_id,source_locator_id,
    provenance_class,is_primary_citation
)
SELECT rule.rule_id,rule.content_package_id,
       locator.source_locator_id,'corroborating',false
FROM rule_rule rule
JOIN src_locator locator
  ON locator.heading_path=
     CASE
         WHEN rule.rule_code LIKE 'vehicle.configuration-option.%'
             THEN 'Vehicle Design > Vehicle Configuration Options'
         WHEN rule.rule_code LIKE 'vehicle.drive-option.%'
             THEN 'Vehicle Design > Vehicle Drive Options'
         ELSE 'Vehicle Design > Vehicle Configuration'
     END
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.ogn'
WHERE rule.rule_code LIKE 'vehicle.configuration.%'
   OR rule.rule_code LIKE 'vehicle.configuration-option.%'
   OR rule.rule_code LIKE 'vehicle.drive-option.%';

INSERT INTO src_issue_locator (
    source_issue_id,source_locator_id,evidence_role
)
SELECT issue.source_issue_id,locator.source_locator_id,'corroborating'
FROM src_issue issue
JOIN src_locator locator
  ON locator.heading_path=
     'Vehicle Design > Vehicle Configuration Options'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.ogn'
WHERE issue.issue_code LIKE 'vehicle.configuration.%';

INSERT INTO src_issue_comparison_check (
    source_issue_id,comparison_work_id,source_locator_id,
    check_status,evidence_summary
)
SELECT issue.source_issue_id,work.source_work_id,
       locator.source_locator_id,'no_independent_calculation',
       'The predecessor defines vehicle-related skills but has no vehicle configuration, drive-option, submersible-depth, or construction calculator capable of resolving this VDS question.'
FROM src_issue issue
JOIN src_work work
  ON work.work_code='cepheus-game.legacy-local'
JOIN src_locator locator
  ON locator.source_work_id=work.source_work_id
 AND locator.heading_path='engine/skills.py'
WHERE issue.issue_code LIKE 'vehicle.configuration.%';
