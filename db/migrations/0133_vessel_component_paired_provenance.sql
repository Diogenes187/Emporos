INSERT INTO src_artifact (
    source_work_id,artifact_kind,source_uri,media_type,local_role
)
SELECT source_work_id,'web_page',
       'https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-equipment/cepheus-engine-ship-design-and-construction/',
       'text/html','verification'
FROM src_work
WHERE work_code='cepheus-engine.ogn';

INSERT INTO src_locator (
    source_work_id,source_artifact_id,locator_type,
    heading_path,display_citation
)
SELECT artifact.source_work_id,artifact.source_artifact_id,
       'heading',
       'Ship Design and Construction > Small Craft Cockpits and Control Cabins',
       'OGN Cepheus Engine, Ship Design: Small Craft Cockpits and Control Cabins'
FROM src_artifact artifact
JOIN src_work work
  ON work.source_work_id=artifact.source_work_id
WHERE work.work_code='cepheus-engine.ogn'
  AND artifact.source_uri=
      'https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-equipment/cepheus-engine-ship-design-and-construction/';

INSERT INTO src_record_provenance (
    rule_id,content_package_id,source_locator_id,
    provenance_class,is_primary_citation
)
SELECT rule.rule_id,rule.content_package_id,locator.source_locator_id,
       'corroborating',false
FROM rule_rule rule
JOIN (
    VALUES
        ('ship.component.one-person-cockpit',
         'Ship Design and Construction > Small Craft Cockpits and Control Cabins'),
        ('ship.component.two-person-cockpit',
         'Ship Design and Construction > Small Craft Cockpits and Control Cabins'),
        ('ship.component.one-person-control-cabin',
         'Ship Design and Construction > Small Craft Cockpits and Control Cabins'),
        ('ship.component.two-person-control-cabin',
         'Ship Design and Construction > Small Craft Cockpits and Control Cabins'),
        ('ship.component.cutter-module-berth',
         'Common Vessels > TL9 Cutter'),
        ('ship.component.smelter',
         'Common Vessels > TL9 Asteroid Miner')
) source(rule_code,heading_path)
  ON source.rule_code=rule.rule_code
JOIN src_locator locator
  ON locator.heading_path=source.heading_path
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
WHERE work.work_code='cepheus-engine.ogn';
