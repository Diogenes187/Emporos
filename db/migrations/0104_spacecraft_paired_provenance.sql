INSERT INTO src_locator (
    source_work_id,source_artifact_id,locator_type,
    heading_path,display_citation
)
SELECT artifact.source_work_id,artifact.source_artifact_id,
       'heading','Off-World Travel > Crew Salaries',
       'OGN Cepheus Engine, Off-World Travel: Crew Salaries'
FROM src_artifact artifact
JOIN src_work work
  ON work.source_work_id=artifact.source_work_id
WHERE work.work_code='cepheus-engine.ogn'
  AND artifact.source_uri=
      'https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-off-world-travel/';

INSERT INTO src_record_provenance (
    rule_id,content_package_id,source_locator_id,
    provenance_class,is_primary_citation
)
SELECT rule.rule_id,rule.content_package_id,locator.source_locator_id,
       'corroborating',false
FROM rule_rule rule
JOIN src_locator locator
  ON locator.heading_path='Off-World Travel > Crew Salaries'
JOIN src_work work ON work.source_work_id=locator.source_work_id
WHERE work.work_code='cepheus-engine.ogn'
  AND rule.rule_code LIKE 'ship.crew.%';
