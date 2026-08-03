INSERT INTO src_artifact (
    source_work_id,artifact_kind,source_uri,media_type,local_role
)
SELECT source_work_id,'web_page',source.source_uri,
       'text/html','verification'
FROM src_work
CROSS JOIN (
    VALUES
        ('https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-equipment/cepheus-engine-common-aircraft/'),
        ('https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-equipment/cepheus-engine-common-watercraft/')
) source(source_uri)
WHERE work_code='cepheus-engine.ogn';

INSERT INTO src_locator (
    source_work_id,source_artifact_id,locator_type,
    heading_path,display_citation
)
SELECT artifact.source_work_id,artifact.source_artifact_id,
       'heading',source.heading_path,source.display_citation
FROM src_artifact artifact
JOIN (
    VALUES
        ('https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-equipment/cepheus-engine-common-aircraft/',
         'Common Aircraft > TL5 Biplane',
         'OGN Cepheus Engine VDS, Common Aircraft: TL5 Biplane'),
        ('https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-equipment/cepheus-engine-common-aircraft/',
         'Common Aircraft > TL7 Helicopter',
         'OGN Cepheus Engine VDS, Common Aircraft: TL7 Helicopter'),
        ('https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-equipment/cepheus-engine-common-aircraft/',
         'Common Aircraft > TL7 Twin Engine Jet',
         'OGN Cepheus Engine VDS, Common Aircraft: TL7 Twin Engine Jet'),
        ('https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-equipment/cepheus-engine-common-watercraft/',
         'Common Watercraft > TL7 Hovercraft',
         'OGN Cepheus Engine VDS, Common Watercraft: TL7 Hovercraft')
) source(source_uri,heading_path,display_citation)
  ON source.source_uri=artifact.source_uri;

INSERT INTO src_record_provenance (
    rule_id,content_package_id,source_locator_id,
    provenance_class,is_primary_citation
)
SELECT rule.rule_id,rule.content_package_id,
       locator.source_locator_id,'corroborating',false
FROM rule_rule rule
JOIN vehicle_class class
  ON class.vehicle_class_rule_id=rule.rule_id
JOIN src_locator primary_locator
  ON primary_locator.source_locator_id=class.source_locator_id
JOIN src_locator locator
  ON locator.heading_path=primary_locator.heading_path
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.ogn'
WHERE rule.rule_code IN (
    'vehicle.class.biplane',
    'vehicle.class.helicopter',
    'vehicle.class.twin-engine-jet',
    'vehicle.class.hovercraft'
);

INSERT INTO src_issue_locator (
    source_issue_id,source_locator_id,evidence_role
)
SELECT issue.source_issue_id,locator.source_locator_id,'corroborating'
FROM src_issue issue
JOIN src_locator locator
  ON locator.heading_path='Common Aircraft > TL5 Biplane'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.ogn'
WHERE issue.issue_code='vehicle.class.biplane-chassis-code';

INSERT INTO src_artifact (
    source_work_id,artifact_kind,source_uri,source_revision,
    byte_length,checksum_sha256,media_type,local_role
)
SELECT source_work_id,'repository_file',
       'reference/srd/src/vds/common-aircraft.md',
       source_revision,4939,
       '0c2b925a5863f9c73e9788b409529b7a4333dd34a64675619c3ec8de7f6ee83f',
       'text/markdown','comparison'
FROM src_work
WHERE work_code='cepheus-game.legacy-local';

INSERT INTO src_locator (
    source_work_id,source_artifact_id,locator_type,
    heading_path,display_citation
)
SELECT artifact.source_work_id,artifact.source_artifact_id,
       'repository_path',artifact.source_uri,
       'Legacy Cepheus reference copy: '||artifact.source_uri
FROM src_artifact artifact
JOIN src_work work USING (source_work_id)
WHERE work.work_code='cepheus-game.legacy-local'
  AND artifact.source_uri=
      'reference/srd/src/vds/common-aircraft.md';

INSERT INTO src_issue_comparison_check (
    source_issue_id,comparison_work_id,source_locator_id,
    check_status,evidence_summary
)
SELECT issue.source_issue_id,work.source_work_id,
       locator.source_locator_id,'no_independent_calculation',
       'The predecessor contains the same copied Biplane profile but no vehicle-construction implementation or independent chassis-code adjudication.'
FROM src_issue issue
JOIN src_work work
  ON work.work_code='cepheus-game.legacy-local'
JOIN src_locator locator
  ON locator.source_work_id=work.source_work_id
 AND locator.heading_path=
     'reference/srd/src/vds/common-aircraft.md'
WHERE issue.issue_code='vehicle.class.biplane-chassis-code';
