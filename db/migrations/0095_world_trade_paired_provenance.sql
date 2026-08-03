INSERT INTO src_artifact (
    source_work_id,artifact_kind,source_uri,media_type,local_role
)
SELECT source_work_id,'web_page',source_uri,'text/html','verification'
FROM src_work
CROSS JOIN (
    VALUES
        ('https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-worlds/'),
        ('https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-off-world-travel/'),
        ('https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-trade-and-commerce/')
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
        ('https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-worlds/',
         'Worlds > Trade Codes','OGN Cepheus Engine, Worlds: Trade Codes'),
        ('https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-trade-and-commerce/',
         'Trade and Commerce > Determine Goods Available',
         'OGN Cepheus Engine, Trade: Determine Goods Available')
) source(source_uri,heading_path,display_citation)
  ON source.source_uri=artifact.source_uri;

INSERT INTO src_record_provenance (
    rule_id,content_package_id,source_locator_id,
    provenance_class,is_primary_citation
)
SELECT rule.rule_id,rule.content_package_id,locator.source_locator_id,
       'corroborating',false
FROM rule_rule rule
JOIN src_locator locator
  ON locator.heading_path=CASE
      WHEN rule.rule_code LIKE 'world.trade-code.%'
          THEN 'Worlds > Trade Codes'
      ELSE 'Trade and Commerce > Determine Goods Available'
  END
JOIN src_work work ON work.source_work_id=locator.source_work_id
WHERE work.work_code='cepheus-engine.ogn'
  AND (
      rule.rule_code LIKE 'world.trade-code.%'
      OR rule.rule_code LIKE 'trade.good.%'
  );
