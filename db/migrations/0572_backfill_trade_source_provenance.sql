WITH wanted(heading_path,label) AS (
    VALUES
        ('Trade and Commerce > Determine Goods Available',
         'Determine Goods Available'),
        ('Trade and Commerce > Determine Purchase Price',
         'Determine Purchase Price'),
        ('Trade and Commerce > Selling Goods','Selling Goods'),
        ('Trade and Commerce > Local Brokers','Local Brokers')
)
INSERT INTO src_locator (
    source_work_id,source_artifact_id,locator_type,heading_path,display_citation
)
SELECT DISTINCT ON (work.work_code,wanted.heading_path)
       artifact.source_work_id,artifact.source_artifact_id,'heading',
       wanted.heading_path,
       CASE work.work_code WHEN 'cepheus-engine.ogn'
         THEN 'Cepheus Engine SRD, Trade and Commerce: '||wanted.label
         ELSE 'Cepheus Engine v9.1, Trade and Commerce: '||wanted.label END
FROM src_artifact artifact
JOIN src_work work USING (source_work_id)
CROSS JOIN wanted
WHERE artifact.source_uri IN (
    'src/book2/trade-and-commerce.md',
    'https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-equipment/cepheus-engine-trade-and-commerce/'
)
ORDER BY work.work_code,wanted.heading_path,artifact.source_artifact_id
ON CONFLICT DO NOTHING;

WITH wanted(rule_code,heading_path) AS (
    VALUES
        ('trade.supplier-stock-generation',
         'Trade and Commerce > Determine Goods Available'),
        ('trade.rejected-quote-cooldown',
         'Trade and Commerce > Determine Purchase Price'),
        ('trade.rejected-quote-cooldown',
         'Trade and Commerce > Selling Goods'),
        ('trade.local-broker-settlement',
         'Trade and Commerce > Local Brokers')
)
INSERT INTO src_record_provenance (
    rule_id,content_package_id,source_locator_id,
    provenance_class,is_primary_citation
)
SELECT rule.rule_id,rule.content_package_id,locator.source_locator_id,
       CASE work.work_code WHEN 'cepheus-engine.ogn'
         THEN 'direct' ELSE 'corroborating' END,
       work.work_code='cepheus-engine.ogn'
FROM wanted
JOIN rule_rule rule ON rule.rule_code=wanted.rule_code
JOIN src_locator locator ON locator.heading_path=wanted.heading_path
JOIN src_work work ON work.source_work_id=locator.source_work_id
WHERE work.work_code IN (
    'cepheus-engine.ogn','cepheus-engine.github-v9.1'
)
ON CONFLICT DO NOTHING;
