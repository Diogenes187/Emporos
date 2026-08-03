WITH prior AS (
    SELECT DISTINCT ON (receipt.ship_class_rule_id) receipt.*
    FROM ship_class_construction_receipt receipt
    JOIN ship_class class USING (ship_class_rule_id)
    WHERE class.class_code IN ('asteroid-miner','destroyer','research-vessel')
    ORDER BY receipt.ship_class_rule_id,receipt.receipt_version DESC
)
INSERT INTO ship_class_construction_receipt (
    ship_class_rule_id,receipt_version,standard_design_discount_rate,
    receipt_status,source_locator_id,supersedes_receipt_id,
    published_variance_allowed
)
SELECT prior.ship_class_rule_id,prior.receipt_version+1,
       prior.standard_design_discount_rate,
       CASE class.class_code
           WHEN 'destroyer' THEN 'source_gap' ELSE 'complete' END,
       prior.source_locator_id,prior.construction_receipt_id,
       prior.published_variance_allowed
FROM prior JOIN ship_class class USING (ship_class_rule_id);

WITH current_pair AS (
    SELECT class.class_code,old_receipt.construction_receipt_id AS old_id,
           new_receipt.construction_receipt_id AS new_id,
           class.ship_class_rule_id
    FROM ship_class class
    JOIN ship_class_construction_receipt new_receipt
      ON new_receipt.ship_class_rule_id=class.ship_class_rule_id
    JOIN ship_class_construction_receipt old_receipt
      ON old_receipt.construction_receipt_id=new_receipt.supersedes_receipt_id
    WHERE class.class_code IN ('asteroid-miner','destroyer','research-vessel')
      AND NOT new_receipt.finalized
)
INSERT INTO ship_class_construction_line (
    ship_class_rule_id,line_order,line_kind,reference_code,quantity,
    allocated_tons,cost_minor,calculation_basis,source_locator_id,
    construction_receipt_id,discount_eligible,line_status
)
SELECT line.ship_class_rule_id,line.line_order,line.line_kind,
       line.reference_code,line.quantity,line.allocated_tons,line.cost_minor,
       line.calculation_basis,line.source_locator_id,pair.new_id,
       line.discount_eligible,line.line_status
FROM current_pair pair
JOIN ship_class_construction_line line
  ON line.construction_receipt_id=pair.old_id
WHERE NOT (pair.class_code='asteroid-miner'
           AND line.line_kind='component'
           AND line.reference_code='smelter')
  AND NOT (pair.class_code='destroyer'
           AND line.line_kind IN ('jump_drive','maneuver_drive'));

INSERT INTO ship_class_construction_line (
    ship_class_rule_id,line_order,line_kind,reference_code,quantity,
    allocated_tons,cost_minor,calculation_basis,source_locator_id,
    construction_receipt_id,discount_eligible,line_status
)
SELECT class.ship_class_rule_id,14,'component','smelter',1,
       component.unit_tons,component.unit_cost_minor,
       'CE-SHIP-001 exact published tonnage and final-cost gaps',
       class.source_locator_id,receipt.construction_receipt_id,
       false,'calculated'
FROM ship_class class
JOIN ship_component_definition component ON component.component_code='smelter'
JOIN ship_class_construction_receipt receipt USING (ship_class_rule_id)
WHERE class.class_code='asteroid-miner' AND receipt.receipt_version=2;

INSERT INTO ship_class_construction_line (
    ship_class_rule_id,line_order,line_kind,reference_code,quantity,
    allocated_tons,cost_minor,calculation_basis,source_locator_id,
    construction_receipt_id,discount_eligible,line_status
)
SELECT class.ship_class_rule_id,
       CASE selected.drive_kind WHEN 'jump' THEN 5 ELSE 6 END,
       CASE selected.drive_kind WHEN 'jump' THEN 'jump_drive'
                                ELSE 'maneuver_drive' END,
       selected.drive_code,1,
       CASE selected.drive_kind WHEN 'jump' THEN drive.jump_drive_tons
                                ELSE drive.maneuver_drive_tons END,
       CASE selected.drive_kind WHEN 'jump' THEN drive.jump_drive_cost_minor
                                ELSE drive.maneuver_drive_cost_minor END,
       'CE-SHIP-002 drive selected from 800-ton performance matrix',
       drive.source_locator_id,receipt.construction_receipt_id,
       true,'calculated'
FROM ship_class class
JOIN ship_class_drive selected USING (ship_class_rule_id)
JOIN rule_ship_drive_design drive
  ON drive.craft_scale=selected.craft_scale
 AND drive.drive_code=selected.drive_code
JOIN ship_class_construction_receipt receipt USING (ship_class_rule_id)
WHERE class.class_code='destroyer'
  AND selected.drive_kind IN ('jump','maneuver')
  AND receipt.receipt_version=2;

UPDATE ship_class_construction_receipt receipt
SET finalized=true
FROM ship_class class
WHERE class.ship_class_rule_id=receipt.ship_class_rule_id
  AND ((class.class_code IN ('asteroid-miner','destroyer')
        AND receipt.receipt_version=2)
       OR (class.class_code='research-vessel'
           AND receipt.receipt_version=3));

INSERT INTO ship_class_construction_variance (
    construction_receipt_id,variance_dimension,variance_amount,
    explanation_code,audit_status,explanation,source_locator_id
)
SELECT total.construction_receipt_id,source.dimension,source.amount,
       source.explanation_code,'unresolved',source.explanation,
       class.source_locator_id
FROM ship_class class
JOIN ship_class_construction_total total USING (ship_class_rule_id)
CROSS JOIN (VALUES
    ('cost',-39987000::numeric,'source-unspecified',
     'Correct drive H and N selections increase the calculated price to MCr462.762; the published MCr422.775 total remains unexplained.'),
    ('tonnage',-32::numeric,'source-unspecified',
     'Correct drive H and N selections raise allocated volume to 832 tons; no published component or cargo correction explains the excess.')
) source(dimension,amount,explanation_code,explanation)
WHERE class.class_code='destroyer';

UPDATE src_issue
SET calculated_value='462762000 credits',difference_value=-39987000
WHERE issue_code='ship.destroyer.construction.cost';

UPDATE src_issue_construction_variance link
SET construction_variance_id=variance.construction_variance_id
FROM src_issue issue,ship_class_construction_variance variance
JOIN ship_class_construction_total total USING (construction_receipt_id)
JOIN ship_class class USING (ship_class_rule_id)
WHERE link.source_issue_id=issue.source_issue_id
  AND issue.issue_code='ship.destroyer.construction.cost'
  AND class.class_code='destroyer'
  AND variance.variance_dimension='cost';

INSERT INTO src_issue (
    issue_code,domain_code,issue_type,review_priority,issue_status,
    subject_code,title,problem_statement,published_value,calculated_value,
    difference_value,value_unit,reviewer_question,requested_evidence,
    engine_disposition
)
VALUES (
    'ship.destroyer.construction.tonnage-adjudicated-drives',
    'ship.construction','source_gap_variance','high','open','destroyer',
    'Destroyer corrected-drive tonnage discrepancy',
    'The agreed H and N drives satisfy published performance but make the itemized design exceed its 800-ton hull.',
    '800 tons','832 tons',-32,'tons',
    'Which published allocation, cargo value, or component should change to recover the 32 excess tons?',
    'Publisher errata or a corrected component-by-component Destroyer worksheet.',
    'source_gap_pending'
);

INSERT INTO src_issue_locator (source_issue_id,source_locator_id,evidence_role)
SELECT issue.source_issue_id,class.source_locator_id,'primary'
FROM src_issue issue JOIN ship_class class ON class.class_code='destroyer'
WHERE issue.issue_code=
    'ship.destroyer.construction.tonnage-adjudicated-drives';

INSERT INTO src_issue_construction_variance (
    source_issue_id,construction_variance_id
)
SELECT issue.source_issue_id,variance.construction_variance_id
FROM src_issue issue
JOIN ship_class class ON class.class_code='destroyer'
JOIN ship_class_construction_total total USING (ship_class_rule_id)
JOIN ship_class_construction_variance variance
  ON variance.construction_receipt_id=total.construction_receipt_id
 AND variance.variance_dimension='tonnage'
WHERE issue.issue_code=
    'ship.destroyer.construction.tonnage-adjudicated-drives';

INSERT INTO src_issue_comparison_check (
    source_issue_id,comparison_work_id,source_locator_id,
    check_status,evidence_summary
)
SELECT issue.source_issue_id,work.source_work_id,locator.source_locator_id,
       'no_independent_calculation',
       'The predecessor parses the published Destroyer summary directly and has no component worksheet capable of resolving the corrected-drive tonnage excess.'
FROM src_issue issue
JOIN src_work work ON work.work_code='cepheus-game.legacy-local'
JOIN src_locator locator ON locator.source_work_id=work.source_work_id
 AND locator.heading_path='scripts/parse_ships.py'
WHERE issue.issue_code=
    'ship.destroyer.construction.tonnage-adjudicated-drives';
