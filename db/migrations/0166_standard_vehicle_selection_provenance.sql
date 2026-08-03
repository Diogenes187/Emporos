INSERT INTO src_artifact (
    source_work_id,artifact_kind,source_uri,media_type,local_role
)
SELECT work.source_work_id,'web_page',source.source_uri,
       'text/html','verification'
FROM src_work work
CROSS JOIN (
    VALUES
        ('https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-equipment/cepheus-engine-common-grav-vehicles/'),
        ('https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-equipment/cepheus-engine-common-ground-vehicles/'),
        ('https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-equipment/cepheus-engine-uncommon-vehicles/')
) source(source_uri)
WHERE work.work_code='cepheus-engine.ogn';

INSERT INTO src_locator (
    source_work_id,source_artifact_id,locator_type,
    heading_path,display_citation
)
SELECT artifact.source_work_id,artifact.source_artifact_id,
       'heading',source.heading_path,source.display_citation
FROM src_artifact artifact
JOIN (
    VALUES
        ('https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-equipment/cepheus-engine-common-grav-vehicles/',
         'Common Grav Vehicles > TL9 Air/Raft',
         'OGN Cepheus Engine VDS, Common Grav Vehicles: TL9 Air/Raft'),
        ('https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-equipment/cepheus-engine-common-grav-vehicles/',
         'Common Grav Vehicles > TL15 G/Carrier',
         'OGN Cepheus Engine VDS, Common Grav Vehicles: TL15 G/Carrier'),
        ('https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-equipment/cepheus-engine-common-grav-vehicles/',
         'Common Grav Vehicles > TL12 Grav Bike',
         'OGN Cepheus Engine VDS, Common Grav Vehicles: TL12 Grav Bike'),
        ('https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-equipment/cepheus-engine-common-grav-vehicles/',
         'Common Grav Vehicles > TL11 Grav Floater',
         'OGN Cepheus Engine VDS, Common Grav Vehicles: TL11 Grav Floater'),
        ('https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-equipment/cepheus-engine-common-grav-vehicles/',
         'Common Grav Vehicles > TL9 Grav Tank',
         'OGN Cepheus Engine VDS, Common Grav Vehicles: TL9 Grav Tank'),
        ('https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-equipment/cepheus-engine-common-grav-vehicles/',
         'Common Grav Vehicles > TL9 Speeder',
         'OGN Cepheus Engine VDS, Common Grav Vehicles: TL9 Speeder'),
        ('https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-equipment/cepheus-engine-common-ground-vehicles/',
         'Common Ground Vehicles > TL12 AFV, Tracked',
         'OGN Cepheus Engine VDS, Common Ground Vehicles: TL12 AFV, Tracked'),
        ('https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-equipment/cepheus-engine-common-ground-vehicles/',
         'Common Ground Vehicles > TL12 ATV, Tracked',
         'OGN Cepheus Engine VDS, Common Ground Vehicles: TL12 ATV, Tracked'),
        ('https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-equipment/cepheus-engine-common-ground-vehicles/',
         'Common Ground Vehicles > TL5 Ground Car',
         'OGN Cepheus Engine VDS, Common Ground Vehicles: TL5 Ground Car'),
        ('https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-equipment/cepheus-engine-common-ground-vehicles/',
         'Common Ground Vehicles > TL3 Stagecoach',
         'OGN Cepheus Engine VDS, Common Ground Vehicles: TL3 Stagecoach'),
        ('https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-equipment/cepheus-engine-common-ground-vehicles/',
         'Common Ground Vehicles > TL5 Van',
         'OGN Cepheus Engine VDS, Common Ground Vehicles: TL5 Van'),
        ('https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-equipment/cepheus-engine-uncommon-vehicles/',
         'Uncommon Vehicles > TL8 Tunnel Boring Machine',
         'OGN Cepheus Engine VDS, Uncommon Vehicles: TL8 Tunnel Boring Machine')
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
WHERE class.class_code IN (
    'air-raft','g-carrier','grav-bike','grav-floater',
    'grav-tank','speeder','afv-tracked','atv-tracked',
    'ground-car','stagecoach','van','tunnel-boring-machine'
);

INSERT INTO src_issue (
    issue_code,domain_code,issue_type,review_priority,
    subject_code,title,problem_statement,
    published_value,calculated_value,
    reviewer_question,requested_evidence,engine_disposition
)
VALUES
    (
        'vehicle.class.basic-life-support-profile-price',
        'vehicle.catalogue','arithmetic_conflict','medium',
        'common-vehicle-basic-life-support',
        'Six vehicle profiles underprice basic life support',
        'The G/Carrier, Grav Tank, Speeder, tracked AFV, tracked ATV, and Tunnel Boring Machine each list a three-space Basic Life Support installation at Cr3,500. The governing catalogue labels Cr3,500 as the price per space, making a normal installation Cr10,500; the Tunnel Boring Machine should instead receive it free with Hostile Environmental Protection.',
        '3 spaces at Cr3,500 in each profile',
        'Cr10,500 normally; Cr0 with Hostile Environmental Protection',
        'Should the six profile worksheets be corrected to the governing life-support prices?',
        'Publisher errata or corrected construction worksheets for the affected vehicles.',
        'preserve_published'
    ),
    (
        'vehicle.class.g-carrier-autopilot',
        'vehicle.catalogue','source_conflict','medium',
        'g-carrier',
        'G/Carrier autopilot level and price conflict with the formula',
        'The TL15 G/Carrier publishes Grav Vehicle-2 at Cr2,000. A ground-vehicle autopilot introduced at TL9 advances to level 3 at TL15 and costs Cr17,000; even the published level 2 would cost Cr12,000.',
        'Grav Vehicle-2 at Cr2,000',
        'Grav Vehicle-3 at Cr17,000',
        'What autopilot level and price were intended for the G/Carrier?',
        'Publisher errata or an authorized G/Carrier construction worksheet.',
        'preserve_published'
    ),
    (
        'vehicle.class.tracked-autopilot-price',
        'vehicle.catalogue','arithmetic_conflict','medium',
        'afv-atv-tracked',
        'Tracked AFV and ATV autopilots omit the skill-level price',
        'Both TL12 tracked profiles correctly identify a Tracked Vehicle-1 autopilot but price it at the level-zero base price of Cr2,000 rather than Cr7,000.',
        'Tracked Vehicle-1 at Cr2,000',
        'Tracked Vehicle-1 at Cr7,000',
        'Should both tracked-vehicle profile prices increase by Cr5,000?',
        'Publisher errata or corrected AFV and ATV construction worksheets.',
        'preserve_published'
    ),
    (
        'vehicle.class.grav-tank-autopilot-label',
        'vehicle.catalogue','source_conflict','low',
        'grav-tank',
        'Grav Tank autopilot level differs between prose and table',
        'The TL9 Grav Tank prose identifies Grav Vehicle-0 and its Cr2,000 table price agrees with level 0, but the table note labels the installation Grav Vehicle-1.',
        'Prose: level 0; table note: level 1; price: Cr2,000',
        'TL9 ground-vehicle formula: level 0 at Cr2,000',
        'Should the Grav Tank table note be corrected to Grav Vehicle-0?',
        'Publisher errata or a corrected Grav Tank profile.',
        'preserve_rule'
    ),
    (
        'vehicle.class.tracked-insidious-protection-price',
        'vehicle.catalogue','arithmetic_conflict','high',
        'afv-atv-tracked',
        'Tracked profiles price Insidious protection as a flat fee',
        'The tracked AFV and ATV each list Insidious Environmental Protection at Cr50,000. The governing rule charges Cr50,000 per chassis space; each Code E chassis has 120 spaces, producing Cr6,000,000.',
        'Cr50,000 on each 120-space chassis',
        'Cr6,000,000 on each 120-space chassis',
        'Is the option price in both tracked profiles missing the per-space multiplication?',
        'Publisher errata or corrected AFV and ATV construction worksheets.',
        'preserve_published'
    ),
    (
        'vehicle.class.tunnel-boring-electronics-omission',
        'vehicle.catalogue','source_omission','medium',
        'tunnel-boring-machine',
        'Tunnel Boring Machine table omits stated electronics',
        'The Tunnel Boring Machine prose specifies Standard sensors and a Model 1 computer, but both rows are absent from its design table. The published cargo remainder and pre-discount total account for exactly their 3.01 spaces and Cr5,500 cost.',
        'No sensor or computer rows in the design table',
        'Standard sensors plus Model 1 computer: 3.01 spaces and Cr5,500',
        'Should the two electronics rows be restored to the design table?',
        'Publisher errata or a corrected Tunnel Boring Machine worksheet.',
        'preserve_rule'
    );

INSERT INTO src_issue_locator (
    source_issue_id,source_locator_id,evidence_role
)
SELECT issue.source_issue_id,locator.source_locator_id,'primary'
FROM src_issue issue
JOIN src_locator locator
  ON locator.heading_path=CASE issue.issue_code
      WHEN 'vehicle.class.basic-life-support-profile-price'
          THEN 'Common Grav Vehicles > TL15 G/Carrier'
      WHEN 'vehicle.class.g-carrier-autopilot'
          THEN 'Common Grav Vehicles > TL15 G/Carrier'
      WHEN 'vehicle.class.tracked-autopilot-price'
          THEN 'Common Ground Vehicles > TL12 AFV, Tracked'
      WHEN 'vehicle.class.grav-tank-autopilot-label'
          THEN 'Common Grav Vehicles > TL9 Grav Tank'
      WHEN 'vehicle.class.tracked-insidious-protection-price'
          THEN 'Common Ground Vehicles > TL12 AFV, Tracked'
      WHEN 'vehicle.class.tunnel-boring-electronics-omission'
          THEN 'Uncommon Vehicles > TL8 Tunnel Boring Machine'
  END
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1'
WHERE issue.issue_code IN (
    'vehicle.class.basic-life-support-profile-price',
    'vehicle.class.g-carrier-autopilot',
    'vehicle.class.tracked-autopilot-price',
    'vehicle.class.grav-tank-autopilot-label',
    'vehicle.class.tracked-insidious-protection-price',
    'vehicle.class.tunnel-boring-electronics-omission'
);

INSERT INTO src_issue_locator (
    source_issue_id,source_locator_id,evidence_role
)
SELECT issue.source_issue_id,locator.source_locator_id,
       source.evidence_role
FROM (
    VALUES
        ('vehicle.class.basic-life-support-profile-price',
         'Common Grav Vehicles > TL9 Grav Tank','corroborating'),
        ('vehicle.class.basic-life-support-profile-price',
         'Common Grav Vehicles > TL9 Speeder','corroborating'),
        ('vehicle.class.basic-life-support-profile-price',
         'Common Ground Vehicles > TL12 AFV, Tracked','corroborating'),
        ('vehicle.class.basic-life-support-profile-price',
         'Common Ground Vehicles > TL12 ATV, Tracked','corroborating'),
        ('vehicle.class.basic-life-support-profile-price',
         'Uncommon Vehicles > TL8 Tunnel Boring Machine','corroborating'),
        ('vehicle.class.basic-life-support-profile-price',
         'Vehicle Design > Vehicle Crew and Passengers > Life Support',
         'conflicting'),
        ('vehicle.class.g-carrier-autopilot',
         'Vehicle Design > Vehicle Controls','conflicting'),
        ('vehicle.class.tracked-autopilot-price',
         'Common Ground Vehicles > TL12 ATV, Tracked','corroborating'),
        ('vehicle.class.tracked-autopilot-price',
         'Vehicle Design > Vehicle Controls','conflicting'),
        ('vehicle.class.grav-tank-autopilot-label',
         'Vehicle Design > Vehicle Controls','corroborating'),
        ('vehicle.class.tracked-insidious-protection-price',
         'Common Ground Vehicles > TL12 ATV, Tracked','corroborating'),
        ('vehicle.class.tracked-insidious-protection-price',
         'Vehicle Design > Vehicle Configuration Options','conflicting'),
        ('vehicle.class.tunnel-boring-electronics-omission',
         'Vehicle Design > Vehicle Sensors','corroborating'),
        ('vehicle.class.tunnel-boring-electronics-omission',
         'Vehicle Design > Vehicle Computer','corroborating')
) source(issue_code,heading_path,evidence_role)
JOIN src_issue issue USING (issue_code)
JOIN src_locator locator USING (heading_path)
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1';

INSERT INTO src_issue_locator (
    source_issue_id,source_locator_id,evidence_role
)
SELECT issue.source_issue_id,locator.source_locator_id,'corroborating'
FROM src_issue issue
JOIN src_locator locator
  ON locator.heading_path=CASE issue.issue_code
      WHEN 'vehicle.class.basic-life-support-profile-price'
          THEN 'Common Grav Vehicles > TL15 G/Carrier'
      WHEN 'vehicle.class.g-carrier-autopilot'
          THEN 'Common Grav Vehicles > TL15 G/Carrier'
      WHEN 'vehicle.class.tracked-autopilot-price'
          THEN 'Common Ground Vehicles > TL12 AFV, Tracked'
      WHEN 'vehicle.class.grav-tank-autopilot-label'
          THEN 'Common Grav Vehicles > TL9 Grav Tank'
      WHEN 'vehicle.class.tracked-insidious-protection-price'
          THEN 'Common Ground Vehicles > TL12 AFV, Tracked'
      WHEN 'vehicle.class.tunnel-boring-electronics-omission'
          THEN 'Uncommon Vehicles > TL8 Tunnel Boring Machine'
  END
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.ogn'
WHERE issue.issue_code IN (
    'vehicle.class.basic-life-support-profile-price',
    'vehicle.class.g-carrier-autopilot',
    'vehicle.class.tracked-autopilot-price',
    'vehicle.class.grav-tank-autopilot-label',
    'vehicle.class.tracked-insidious-protection-price',
    'vehicle.class.tunnel-boring-electronics-omission'
);

INSERT INTO src_artifact (
    source_work_id,artifact_kind,source_uri,source_revision,
    byte_length,checksum_sha256,media_type,local_role
)
SELECT work.source_work_id,'repository_file',source.source_uri,
       work.source_revision,source.byte_length,source.checksum,
       'text/markdown','comparison'
FROM src_work work
CROSS JOIN (
    VALUES
        ('reference/srd/src/vds/common-grav-vehicles.md',
         12563::bigint,
         '184e34c197c3d1e4379f613ea6f33f439b55752393fd46de2b94afa85239c33d'),
        ('reference/srd/src/vds/common-ground-vehicles.md',
         9546::bigint,
         '5265e0bf4f16b715722ce516e7be657b61a01cfcc2a81a3b73b633a9d1a1e0f6'),
        ('reference/srd/src/vds/uncommon-vehicles.md',
         2063::bigint,
         '17d9294fdb344b71952173c3f1fef0065cc80c7c1d890e58ae2d8e5d7d3a62ad')
) source(source_uri,byte_length,checksum)
WHERE work.work_code='cepheus-game.legacy-local';

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
  AND artifact.source_uri IN (
      'reference/srd/src/vds/common-grav-vehicles.md',
      'reference/srd/src/vds/common-ground-vehicles.md',
      'reference/srd/src/vds/uncommon-vehicles.md'
  );

INSERT INTO src_issue_comparison_check (
    source_issue_id,comparison_work_id,source_locator_id,
    check_status,evidence_summary
)
SELECT issue.source_issue_id,work.source_work_id,
       locator.source_locator_id,'no_independent_calculation',
       CASE issue.issue_code
           WHEN 'vehicle.class.basic-life-support-profile-price'
               THEN 'The predecessor retains the same copied profile prices but has no vehicle construction or life-support cost calculator.'
           WHEN 'vehicle.class.g-carrier-autopilot'
               THEN 'The predecessor retains the same G/Carrier profile but has no autopilot level or price calculator.'
           WHEN 'vehicle.class.tracked-autopilot-price'
               THEN 'The predecessor retains the same tracked profiles but has no autopilot price calculator.'
           WHEN 'vehicle.class.grav-tank-autopilot-label'
               THEN 'The predecessor retains the same Grav Tank prose and table conflict but has no independent adjudication.'
           WHEN 'vehicle.class.tracked-insidious-protection-price'
               THEN 'The predecessor retains the same tracked profile prices but has no configuration-option cost calculator.'
           ELSE
               'The predecessor retains the same Tunnel Boring Machine prose and table but has no vehicle construction worksheet.'
       END
FROM src_issue issue
JOIN src_work work
  ON work.work_code='cepheus-game.legacy-local'
JOIN src_locator locator
  ON locator.source_work_id=work.source_work_id
 AND locator.heading_path=CASE
      WHEN issue.issue_code IN (
          'vehicle.class.basic-life-support-profile-price',
          'vehicle.class.g-carrier-autopilot',
          'vehicle.class.grav-tank-autopilot-label'
      ) THEN 'reference/srd/src/vds/common-grav-vehicles.md'
      WHEN issue.issue_code IN (
          'vehicle.class.tracked-autopilot-price',
          'vehicle.class.tracked-insidious-protection-price'
      ) THEN 'reference/srd/src/vds/common-ground-vehicles.md'
      ELSE 'reference/srd/src/vds/uncommon-vehicles.md'
  END
WHERE issue.issue_code IN (
    'vehicle.class.basic-life-support-profile-price',
    'vehicle.class.g-carrier-autopilot',
    'vehicle.class.tracked-autopilot-price',
    'vehicle.class.grav-tank-autopilot-label',
    'vehicle.class.tracked-insidious-protection-price',
    'vehicle.class.tunnel-boring-electronics-omission'
);
