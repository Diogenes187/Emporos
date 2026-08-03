INSERT INTO src_locator (
    source_work_id,source_artifact_id,locator_type,
    heading_path,display_citation
)
SELECT artifact.source_work_id,artifact.source_artifact_id,
       'heading',source.heading_path,source.display_citation
FROM src_artifact artifact
CROSS JOIN (
    VALUES
        ('Vehicle Design > Vehicle Controls',
         'Cepheus Engine OGN VDS, Vehicle Controls'),
        ('Vehicle Design > Vehicle Communication Systems',
         'Cepheus Engine OGN VDS, Vehicle Communication Systems'),
        ('Vehicle Design > Vehicle Sensors',
         'Cepheus Engine OGN VDS, Vehicle Sensors'),
        ('Vehicle Design > Vehicle Computer',
         'Cepheus Engine OGN VDS, Vehicle Computer')
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
JOIN vehicle_component_definition component
  ON component.component_rule_id=rule.rule_id
JOIN src_locator locator
  ON locator.heading_path=
     CASE
         WHEN component.component_code LIKE 'communication.%'
             THEN 'Vehicle Design > Vehicle Communication Systems'
         WHEN component.component_code LIKE 'sensor.%'
             THEN 'Vehicle Design > Vehicle Sensors'
         WHEN component.component_code LIKE 'computer.%'
             THEN 'Vehicle Design > Vehicle Computer'
         ELSE 'Vehicle Design > Vehicle Controls'
     END
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.ogn'
WHERE rule.rule_code LIKE 'vehicle.component.%';

INSERT INTO src_issue_locator (
    source_issue_id,source_locator_id,evidence_role
)
SELECT issue.source_issue_id,locator.source_locator_id,'corroborating'
FROM src_issue issue
JOIN (
    VALUES
        ('vehicle.controls.primitive-tech-level',
         'Vehicle Design > Vehicle Controls'),
        ('vehicle.sensors.standard-range-distance',
         'Vehicle Design > Vehicle Sensors')
) source(issue_code,heading_path)
  ON source.issue_code=issue.issue_code
JOIN src_locator locator USING (heading_path)
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.ogn';

