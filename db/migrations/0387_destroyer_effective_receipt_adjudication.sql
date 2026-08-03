INSERT INTO rule_interpretation (
    rule_id,interpretation_type,decision_register_entry,rationale
)
SELECT rule.rule_id,'agreed_interpretation','CE-SHIP-004',
       'The corrected H/N-drive receipt is the effective Destroyer design at 832 allocated tons and MCr462.762; published 800 tons and MCr422.775 remain immutable source facts.'
FROM rule_rule rule
WHERE rule.rule_code='ship.class.destroyer';

UPDATE src_issue issue
SET issue_status='resolved',resolved_at=clock_timestamp(),
    resolution_summary=source.summary,engine_disposition='preserve_rule'
FROM (VALUES
    ('ship.destroyer.construction.cost',
     'CE-SHIP-004 adopts the corrected-drive receipt cost MCr462.762 while preserving published MCr422.775 as provenance.'),
    ('ship.destroyer.construction.tonnage-adjudicated-drives',
     'CE-SHIP-004 adopts 832 allocated tons as the effective corrected-drive receipt while preserving the published 800-ton hull statement as provenance.')
) source(issue_code,summary)
WHERE issue.issue_code=source.issue_code;
