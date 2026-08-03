INSERT INTO src_locator (
    source_work_id,source_artifact_id,locator_type,
    heading_path,display_citation
)
SELECT artifact.source_work_id,artifact.source_artifact_id,
       'heading',source.heading_path,source.display_citation
FROM src_artifact artifact
CROSS JOIN (
    VALUES
        ('Vehicle Design > Vehicle Crew and Passengers',
         'Cepheus Engine OGN VDS, Vehicle Crew and Passengers'),
        ('Vehicle Design > Vehicle Crew and Passengers > Life Support',
         'Cepheus Engine OGN VDS, Vehicle Life Support'),
        ('Vehicle Design > Additional Vehicle Components',
         'Cepheus Engine OGN VDS, Additional Vehicle Components')
) source(heading_path,display_citation)
WHERE artifact.source_uri=
    'https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-equipment/cepheus-engine-introduction-2/';

INSERT INTO src_locator (
    source_work_id,source_artifact_id,locator_type,
    heading_path,display_citation
)
SELECT artifact.source_work_id,artifact.source_artifact_id,
       'heading',
       'Ship Design and Construction > Ship Crew > Accommodation',
       'OGN Cepheus Engine, Ship Design: Crew Accommodation'
FROM src_artifact artifact
JOIN src_work work USING (source_work_id)
WHERE work.work_code='cepheus-engine.ogn'
  AND artifact.source_uri=
      'https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-equipment/cepheus-engine-ship-design-and-construction/';

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
         WHEN component.component_code LIKE 'accommodation.%'
             THEN 'Vehicle Design > Vehicle Crew and Passengers'
         WHEN component.component_code LIKE 'life-support.%'
             THEN 'Vehicle Design > Vehicle Crew and Passengers > Life Support'
         ELSE 'Vehicle Design > Additional Vehicle Components'
     END
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.ogn'
WHERE rule.rule_code LIKE 'vehicle.component.accommodation.%'
   OR rule.rule_code LIKE 'vehicle.component.life-support.%'
   OR rule.rule_code LIKE 'vehicle.component.additional.%';

INSERT INTO src_record_provenance (
    rule_id,content_package_id,source_locator_id,
    provenance_class,is_primary_citation
)
SELECT rule.rule_id,rule.content_package_id,
       locator.source_locator_id,'corroborating',false
FROM rule_rule rule
JOIN rule_vehicle_emergency_low_berth berth
  ON berth.component_rule_id=rule.rule_id
JOIN src_locator locator
  ON locator.heading_path=
     'Ship Design and Construction > Ship Crew > Accommodation'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.ogn';

INSERT INTO src_issue_locator (
    source_issue_id,source_locator_id,evidence_role
)
SELECT issue.source_issue_id,locator.source_locator_id,'corroborating'
FROM src_issue issue
JOIN src_locator locator
  ON locator.heading_path=
     'Vehicle Design > Additional Vehicle Components'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.ogn'
WHERE issue.issue_code IN (
    'vehicle.components.wet-bar-table',
    'vehicle.components.folding-wings-summary-omission',
    'vehicle.components.emergency-low-berth-capacity'
);

INSERT INTO src_issue_locator (
    source_issue_id,source_locator_id,evidence_role
)
SELECT issue.source_issue_id,locator.source_locator_id,'corroborating'
FROM src_issue issue
JOIN src_locator locator
  ON locator.heading_path=
     'Ship Design and Construction > Ship Crew > Accommodation'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.ogn'
WHERE issue.issue_code=
      'vehicle.components.emergency-low-berth-capacity';

INSERT INTO src_artifact (
    source_work_id,artifact_kind,source_uri,source_revision,
    media_type,local_role
)
SELECT work.source_work_id,'repository_file','engine/skills.py',
       work.source_revision,'text/x-python','comparison'
FROM src_work work
WHERE work.work_code='cepheus-game.legacy-local';

INSERT INTO src_locator (
    source_work_id,source_artifact_id,locator_type,
    heading_path,display_citation
)
SELECT artifact.source_work_id,artifact.source_artifact_id,
       'repository_path',artifact.source_uri,
       'Legacy Cepheus @ fa849d9: '||artifact.source_uri
FROM src_artifact artifact
JOIN src_work work USING (source_work_id)
WHERE work.work_code='cepheus-game.legacy-local'
  AND artifact.source_uri='engine/skills.py';

INSERT INTO src_issue_comparison_check (
    source_issue_id,comparison_work_id,source_locator_id,
    check_status,evidence_summary
)
SELECT issue.source_issue_id,work.source_work_id,
       locator.source_locator_id,'no_independent_calculation',
       'The predecessor defines vehicle-related skills but has no vehicle construction catalogue, component calculator, or independent adjudication of controls, sensors, accommodations, life support, or additional vehicle components.'
FROM src_issue issue
JOIN src_work work
  ON work.work_code='cepheus-game.legacy-local'
JOIN src_locator locator
  ON locator.source_work_id=work.source_work_id
 AND locator.heading_path='engine/skills.py'
WHERE issue.issue_code LIKE 'vehicle.%';
