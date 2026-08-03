INSERT INTO src_artifact (
    source_work_id,artifact_kind,source_uri,media_type,local_role
)
SELECT source_work_id,'web_page',
       'https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-equipment/cepheus-engine-common-vessels/',
       'text/html','verification'
FROM src_work
WHERE work_code='cepheus-engine.ogn';

INSERT INTO src_locator (
    source_work_id,source_artifact_id,locator_type,
    heading_path,display_citation
)
SELECT artifact.source_work_id,artifact.source_artifact_id,
       'heading','Common Vessels > '||source.heading,
       'OGN Cepheus Engine, Common Vessels: '||source.heading
FROM src_artifact artifact
CROSS JOIN (
    VALUES
        ('TL9 Asteroid Miner'),('TL11 Corvette'),('TL9 Courier'),
        ('TL11 Destroyer'),('TL14 Dreadnought'),('TL9 Frontier Trader'),
        ('TL11 Heavy Cruiser'),('TL11 Light Cruiser'),
        ('TL9 Merchant Freighter'),('TL9 Merchant Liner'),
        ('TL9 Merchant Trader'),('TL11 Patrol Frigate'),('TL9 Raider'),
        ('TL9 Research Vessel'),('TL11 Survey Vessel'),
        ('TL9 System Defense Boat'),('TL9 System Monitor'),('TL9 Yacht'),
        ('TL9 Cutter'),('TL9 Fighter'),('TL9 Launch'),('TL9 Pinnace'),
        ('TL9 Ship''s Boat'),('TL9 Shuttle')
) source(heading)
JOIN src_work work
  ON work.source_work_id=artifact.source_work_id
WHERE work.work_code='cepheus-engine.ogn'
  AND artifact.source_uri=
      'https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-equipment/cepheus-engine-common-vessels/';

INSERT INTO src_record_provenance (
    rule_id,content_package_id,source_locator_id,
    provenance_class,is_primary_citation
)
SELECT rule.rule_id,rule.content_package_id,locator.source_locator_id,
       'corroborating',false
FROM rule_rule rule
JOIN ship_class class
  ON class.ship_class_rule_id=rule.rule_id
JOIN src_locator primary_locator
  ON primary_locator.source_locator_id=class.source_locator_id
JOIN src_locator locator
  ON locator.heading_path=primary_locator.heading_path
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
WHERE work.work_code='cepheus-engine.ogn';
