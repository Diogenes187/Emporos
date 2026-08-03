ALTER TABLE vehicle_class_construction_receipt
    DROP CONSTRAINT vehicle_class_construction_receipt_receipt_status_check,
    ADD CONSTRAINT vehicle_class_construction_receipt_receipt_status_check CHECK (
        receipt_status IN ('published','source_conflict','source_gap','adjudicated')
    );

ALTER TABLE vehicle_class_construction_line
    DROP CONSTRAINT vehicle_class_construction_line_line_status_check,
    ADD CONSTRAINT vehicle_class_construction_line_line_status_check CHECK (
        line_status IN (
            'published','published_override','reconstructed','adjudicated'
        )
    );

ALTER TABLE vehicle_class_weapon_point_summary
    DROP CONSTRAINT
        vehicle_class_weapon_point_s_effective_unused_weapon_poin_check,
    DROP COLUMN effective_unused_weapon_points,
    ADD COLUMN effective_unused_weapon_points smallint
        GENERATED ALWAYS AS (
            effective_available_weapon_points-
            calculated_used_weapon_points
        ) STORED,
    ADD CHECK (effective_unused_weapon_points>=0);

INSERT INTO vehicle_class_construction_receipt (
    vehicle_class_rule_id,receipt_version,supersedes_receipt_id,
    standard_design_discount_rate,stated_subtotal_credits,
    receipt_status,source_locator_id
)
SELECT class.vehicle_class_rule_id,prior.receipt_version+1,
       prior.construction_receipt_id,prior.standard_design_discount_rate,
       CASE class.class_code
           WHEN 'g-carrier' THEN 1518682.24
           WHEN 'grav-tank' THEN 1732659.48
           WHEN 'afv-tracked' THEN 6264760.48
           WHEN 'atv-tracked' THEN 6116560.48
           ELSE NULL
       END,
       CASE WHEN class.class_code='destroyer-watercraft'
            THEN 'source_gap' ELSE 'adjudicated' END,
       prior.source_locator_id
FROM vehicle_class class
JOIN vehicle_class_construction_receipt prior USING(vehicle_class_rule_id)
WHERE class.class_code IN (
        'g-carrier','grav-tank','afv-tracked','atv-tracked',
        'destroyer-watercraft'
      )
  AND prior.receipt_version=(
      SELECT max(candidate.receipt_version)
      FROM vehicle_class_construction_receipt candidate
      WHERE candidate.vehicle_class_rule_id=class.vehicle_class_rule_id
  );

WITH receipt_pair AS (
    SELECT class.class_code,new_receipt.construction_receipt_id AS new_id,
           old_receipt.construction_receipt_id AS old_id
    FROM vehicle_class class
    JOIN vehicle_class_construction_receipt new_receipt
      USING(vehicle_class_rule_id)
    JOIN vehicle_class_construction_receipt old_receipt
      ON old_receipt.construction_receipt_id=new_receipt.supersedes_receipt_id
    WHERE class.class_code IN (
        'g-carrier','grav-tank','afv-tracked','atv-tracked',
        'destroyer-watercraft'
    ) AND NOT new_receipt.finalized
)
INSERT INTO vehicle_class_construction_line (
    construction_receipt_id,vehicle_class_rule_id,line_order,line_kind,
    reference_code,quantity,space_role,published_spaces,
    published_cost_credits,discount_eligible,line_status,source_locator_id
)
SELECT pair.new_id,line.vehicle_class_rule_id,line.line_order,line.line_kind,
       line.reference_code,line.quantity,line.space_role,line.published_spaces,
       CASE WHEN pair.class_code IN ('afv-tracked','atv-tracked')
                  AND line.reference_code='insidious-environmental-protection'
            THEN 6000000 ELSE line.published_cost_credits END,
       line.discount_eligible,
       CASE
           WHEN pair.class_code IN ('afv-tracked','atv-tracked')
                AND line.reference_code='insidious-environmental-protection'
               THEN 'adjudicated'
           WHEN pair.class_code IN ('g-carrier','grav-tank')
               THEN 'adjudicated'
           ELSE line.line_status
       END,
       line.source_locator_id
FROM receipt_pair pair
JOIN vehicle_class_construction_line line
  ON line.construction_receipt_id=pair.old_id;

UPDATE vehicle_class_construction_receipt receipt
SET finalized=true
FROM vehicle_class class
WHERE class.vehicle_class_rule_id=receipt.vehicle_class_rule_id
  AND class.class_code IN (
      'g-carrier','grav-tank','afv-tracked','atv-tracked',
      'destroyer-watercraft'
  )
  AND receipt.receipt_version=2;

UPDATE vehicle_class_weapon_point_summary summary
SET effective_available_weapon_points=2,
    adjudication_basis='governing-rule'
FROM vehicle_class class
WHERE class.vehicle_class_rule_id=summary.vehicle_class_rule_id
  AND class.class_code='afv-tracked';

UPDATE vehicle_class_weapon_point_summary summary
SET calculated_used_weapon_points=22,
    used_reconciliation_status='source-conflict'
FROM vehicle_class class
WHERE class.vehicle_class_rule_id=summary.vehicle_class_rule_id
  AND class.class_code='destroyer-watercraft';

INSERT INTO rule_interpretation (
    rule_id,interpretation_type,decision_register_entry,rationale
)
SELECT rule.rule_id,'agreed_interpretation',source.entry,source.rationale
FROM (VALUES
    ('vehicle.class.afv-tracked','CE-VDS-008',
     'A ten-ton chassis has two available weapon points under the governing one-per-five-tons rule; the listed turret occupies one.'),
    ('vehicle.class.g-carrier','CE-VDS-009',
     'The itemized G/Carrier receipt governs at Cr1,518,682.24 before the standard-design discount.'),
    ('vehicle.class.grav-tank','CE-VDS-010',
     'The Grav Tank receipt includes its listed Cr100,000 Beam Laser for a Cr1,732,659.48 subtotal.'),
    ('vehicle.class.destroyer-watercraft','CE-VDS-011',
     'The copied aircraft tail is superseded by an immutable normalized receipt reconstructed from the Destroyer narrative and component selections.'),
    ('vehicle.class.destroyer-watercraft','CE-VDS-012',
     'The listed Destroyer armament consumes 22 weapon points; the published value 23 remains recorded as a source discrepancy.')
) source(rule_code,entry,rationale)
JOIN rule_rule rule ON rule.rule_code=source.rule_code;

UPDATE src_issue issue
SET issue_status='resolved',resolved_at=clock_timestamp(),
    resolution_summary=source.summary,engine_disposition='preserve_rule'
FROM (VALUES
    ('vehicle.class.afv-weapon-points',
     'CE-VDS-008 applies the governing chassis formula: two available points, one used.'),
    ('vehicle.class.g-carrier-design-subtotal',
     'CE-VDS-009 adopts the itemized Cr1,518,682.24 subtotal in adjudicated receipt version 2.'),
    ('vehicle.class.grav-tank-subtotal-omits-weapon',
     'CE-VDS-010 includes the Beam Laser and adopts Cr1,732,659.48 in adjudicated receipt version 2.'),
    ('vehicle.class.tracked-insidious-protection-price',
     'CE-VDS-007 applies Cr50,000 per chassis Space, or Cr6,000,000 on each 120-Space tracked chassis.'),
    ('vehicle.class.destroyer-design-table-copy',
     'CE-VDS-011 supersedes the copied aircraft tail with normalized narrative-based receipt version 2.'),
    ('vehicle.class.destroyer-used-weapon-points',
     'CE-VDS-012 adopts the 22 points reconstructed from the listed armament while preserving published 23.')
) source(issue_code,summary)
WHERE issue.issue_code=source.issue_code;
