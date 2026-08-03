INSERT INTO src_locator (
    source_work_id,source_artifact_id,locator_type,
    heading_path,display_citation
)
SELECT artifact.source_work_id,artifact.source_artifact_id,
       'heading',source.heading_path,source.display_citation
FROM src_artifact artifact
CROSS JOIN (
    VALUES
        ('Common Watercraft > TL9 Destroyer',
         'OGN Cepheus Engine VDS, Common Watercraft: TL9 Destroyer'),
        ('Common Watercraft > TL5 Motor Boat',
         'OGN Cepheus Engine VDS, Common Watercraft: TL5 Motor Boat'),
        ('Common Watercraft > TL4 Steamship',
         'OGN Cepheus Engine VDS, Common Watercraft: TL4 Steamship'),
        ('Common Watercraft > TL6 Submersible',
         'OGN Cepheus Engine VDS, Common Watercraft: TL6 Submersible')
) source(heading_path,display_citation)
JOIN src_work work
  ON work.source_work_id=artifact.source_work_id
 AND work.work_code='cepheus-engine.ogn'
WHERE artifact.source_uri=
    'https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-equipment/cepheus-engine-common-watercraft/';

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
    'vehicle.class.destroyer-watercraft',
    'vehicle.class.motor-boat',
    'vehicle.class.steamship',
    'vehicle.class.submersible'
);

INSERT INTO src_issue_locator (
    source_issue_id,source_locator_id,evidence_role
)
SELECT issue.source_issue_id,locator.source_locator_id,'corroborating'
FROM src_issue issue
JOIN src_locator locator
  ON locator.heading_path=
     'Common Watercraft > TL9 Destroyer'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.ogn'
WHERE issue.issue_code=
      'vehicle.class.destroyer-design-table-copy';

INSERT INTO src_artifact (
    source_work_id,artifact_kind,source_uri,source_revision,
    byte_length,checksum_sha256,media_type,local_role
)
SELECT source_work_id,'repository_file',
       'reference/srd/src/vds/common-watercraft.md',
       source_revision,11609,
       '6258e916e6195fababc7541628e279a765de8fdf2a64e06b6b9edae401f1339d',
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
      'reference/srd/src/vds/common-watercraft.md';

INSERT INTO src_issue_comparison_check (
    source_issue_id,comparison_work_id,source_locator_id,
    check_status,evidence_summary
)
SELECT issue.source_issue_id,work.source_work_id,
       locator.source_locator_id,'no_independent_calculation',
       'The predecessor contains the same copied Destroyer table but no watercraft construction implementation or independent corrected worksheet.'
FROM src_issue issue
JOIN src_work work
  ON work.work_code='cepheus-game.legacy-local'
JOIN src_locator locator
  ON locator.source_work_id=work.source_work_id
 AND locator.heading_path=
     'reference/srd/src/vds/common-watercraft.md'
WHERE issue.issue_code=
      'vehicle.class.destroyer-design-table-copy';
