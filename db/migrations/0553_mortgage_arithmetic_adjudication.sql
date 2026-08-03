INSERT INTO src_issue(
 issue_code,domain_code,issue_type,review_priority,issue_status,subject_code,title,
 problem_statement,published_value,calculated_value,difference_value,value_unit,
 reviewer_question,requested_evidence,engine_disposition,resolved_at,resolution_summary
) VALUES(
 'ship.mortgage.financed-total-arithmetic','ship.finance','arithmetic_conflict','high','resolved',
 'mortgage-standard','Starship mortgage financed-total contradiction',
 'The source prescribes monthly payments of 1/240 of cash price for 480 months, but describes the resulting financed total as 220 percent. The prescribed schedule calculates to 200 percent.',
 '220% of cash price','200% of cash price',20,'percentage points',
 'Should the executable monthly schedule or the explanatory financed-total sentence govern settlement?',
 'Compare the Cepheus GitHub SRD, OGN SRD, published PDF, and originating Traveller SRD wording.',
 'preserve_rule',clock_timestamp(),
 'All checked sources repeat the same internal contradiction. Emporos preserves the explicit executable schedule: cash price divided by 240, paid monthly for 480 months. The 220 percent sentence is retained as cited source evidence but does not alter ledger arithmetic.'
);

INSERT INTO src_issue_locator(source_issue_id,source_locator_id,evidence_role)
SELECT issue.source_issue_id,locator.source_locator_id,
       CASE WHEN work.work_code='cepheus-engine.ogn' THEN 'primary' ELSE 'corroborating' END
FROM src_issue issue
JOIN src_locator locator ON locator.heading_path='Off-World Travel > Starship Expenses'
JOIN src_work work USING(source_work_id)
WHERE issue.issue_code='ship.mortgage.financed-total-arithmetic'
  AND work.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1')
ON CONFLICT DO NOTHING;
