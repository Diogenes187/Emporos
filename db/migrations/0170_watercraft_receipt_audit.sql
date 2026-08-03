INSERT INTO src_issue (
    issue_code,domain_code,issue_type,review_priority,
    subject_code,title,problem_statement,
    published_value,calculated_value,
    reviewer_question,requested_evidence,engine_disposition
)
VALUES (
    'vehicle.class.steamship-cargo-space',
    'vehicle.catalogue','arithmetic_conflict','medium',
    'steamship',
    'Steamship cargo exceeds the remaining chassis space',
    'The Steamship construction lines consume 1,991.4 spaces before cargo. The published 516.6 cargo spaces therefore require 2,508 spaces in a 2,400-space chassis.',
    '2,400 chassis spaces; 516.6 cargo spaces',
    '1,991.4 allocated spaces; 408.6 spaces remaining for cargo',
    'Which Steamship component space or cargo figure should be corrected by 108 spaces?',
    'Publisher errata or a corrected Steamship construction worksheet.',
    'preserve_published'
);

INSERT INTO src_issue_locator (
    source_issue_id,source_locator_id,evidence_role
)
SELECT issue.source_issue_id,locator.source_locator_id,
       CASE work.work_code
           WHEN 'cepheus-engine.github-v9.1' THEN 'primary'
           ELSE 'corroborating'
       END
FROM src_issue issue
JOIN src_locator locator
  ON locator.heading_path='Common Watercraft > TL4 Steamship'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code IN (
     'cepheus-engine.github-v9.1','cepheus-engine.ogn'
 )
WHERE issue.issue_code='vehicle.class.steamship-cargo-space';

INSERT INTO vehicle_class_construction_variance (
    construction_receipt_id,variance_dimension,variance_amount,
    explanation_code,audit_status,source_issue_id
)
SELECT total.construction_receipt_id,'space',source.amount,
       'published-arithmetic-conflict',source.audit_status,
       issue.source_issue_id
FROM (
    VALUES
        (
            'destroyer-watercraft',204.41::numeric,'unresolved',
            'vehicle.class.destroyer-design-table-copy'
        ),
        (
            'steamship',-108::numeric,'source_conflict',
            'vehicle.class.steamship-cargo-space'
        )
) source(class_code,amount,audit_status,issue_code)
JOIN vehicle_class class USING (class_code)
JOIN vehicle_class_construction_total total
  USING (vehicle_class_rule_id)
JOIN src_issue issue USING (issue_code);

INSERT INTO src_issue_comparison_check (
    source_issue_id,comparison_work_id,source_locator_id,
    check_status,evidence_summary
)
SELECT issue.source_issue_id,work.source_work_id,
       locator.source_locator_id,'no_independent_calculation',
       'The predecessor retains the same copied Steamship table but has no construction worksheet or independent arithmetic.'
FROM src_issue issue
JOIN src_work work
  ON work.work_code='cepheus-game.legacy-local'
JOIN src_locator locator
  ON locator.source_work_id=work.source_work_id
 AND locator.heading_path='reference/srd/src/vds/common-watercraft.md'
WHERE issue.issue_code='vehicle.class.steamship-cargo-space';
