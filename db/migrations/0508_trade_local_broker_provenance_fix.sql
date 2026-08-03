INSERT INTO src_locator(source_work_id,source_artifact_id,locator_type,heading_path,display_citation)
SELECT DISTINCT ON(work.work_code) artifact.source_work_id,artifact.source_artifact_id,'heading',
       'Trade and Commerce > Local Brokers',
       CASE work.work_code WHEN 'cepheus-engine.ogn'
         THEN 'Cepheus Engine SRD, Trade and Commerce: Local Brokers'
         ELSE 'Cepheus Engine v9.1, Trade and Commerce: Local Brokers' END
FROM src_artifact artifact JOIN src_work work USING(source_work_id)
WHERE artifact.source_uri IN(
 'src/book2/trade-and-commerce.md',
 'https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-equipment/cepheus-engine-trade-and-commerce/'
)
ORDER BY work.work_code,artifact.source_artifact_id
ON CONFLICT DO NOTHING;

INSERT INTO src_record_provenance(rule_id,content_package_id,source_locator_id,provenance_class,is_primary_citation)
SELECT rule.rule_id,rule.content_package_id,locator.source_locator_id,
       CASE work.work_code WHEN 'cepheus-engine.ogn' THEN 'direct' ELSE 'corroborating' END,
       work.work_code='cepheus-engine.ogn'
FROM rule_rule rule CROSS JOIN src_locator locator JOIN src_work work USING(source_work_id)
WHERE rule.rule_code='trade.local-broker-settlement'
  AND locator.heading_path='Trade and Commerce > Local Brokers'
  AND work.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1')
ON CONFLICT DO NOTHING;

INSERT INTO src_issue_locator(source_issue_id,source_locator_id,evidence_role)
SELECT issue.source_issue_id,locator.source_locator_id,
       CASE work.work_code WHEN 'cepheus-engine.ogn' THEN 'primary' ELSE 'corroborating' END
FROM src_issue issue CROSS JOIN src_locator locator JOIN src_work work USING(source_work_id)
WHERE issue.issue_code='trade.local-broker.commission-rounding'
  AND locator.heading_path='Trade and Commerce > Local Brokers'
  AND work.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1')
ON CONFLICT DO NOTHING;
