WITH ranked AS(
 SELECT provenance.record_provenance_id,row_number() OVER(PARTITION BY provenance.rule_id,work.work_code,locator.heading_path ORDER BY provenance.record_provenance_id) AS duplicate_rank
 FROM src_record_provenance provenance JOIN rule_rule rule USING(rule_id) JOIN src_locator locator USING(source_locator_id) JOIN src_work work ON work.source_work_id=locator.source_work_id
 WHERE rule.rule_code='ship.security' AND locator.heading_path LIKE 'Off-World Travel > Ship Security > %'
)
DELETE FROM src_record_provenance provenance USING ranked WHERE provenance.record_provenance_id=ranked.record_provenance_id AND ranked.duplicate_rank>1;
