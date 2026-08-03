INSERT INTO rule_interpretation (
    rule_id,interpretation_type,decision_register_entry,rationale
)
SELECT rule.rule_id,'agreed_interpretation',decision.decision_code,
       decision.rationale
FROM (VALUES
    ('ship.class.destroyer','CE-SHIP-005',
     'Prorate the final Crystaliron increment to 11 protection, then reduce cargo to 28.5 tons to accommodate the previously adjudicated H and N drives.'),
    ('ship.class.heavy-cruiser','CE-SHIP-005',
     'Prorate the final Crystaliron increment to preserve the published 11 protection and 152.5-ton cargo allocation within the hull.'),
    ('ship.class.light-cruiser','CE-SHIP-005',
     'Prorate the final Crystaliron increment to preserve the published 11 protection and 53-ton cargo allocation within the hull.'),
    ('ship.class.system-monitor','CE-SHIP-005',
     'Prorate the final Titanium Steel increment to preserve the published 9 protection and 123.5-ton cargo allocation within the hull.'),
    ('ship.class.corvette','CE-SHIP-006',
     'Treat cargo as remaining hull volume and correct the effective cargo allocation from the published 25 tons to 17 tons.'),
    ('ship.class.dreadnought','CE-SHIP-006',
     'Treat cargo as remaining hull volume and correct the effective cargo allocation from the published 412 tons to 385 tons.'),
    ('ship.class.patrol-frigate','CE-SHIP-006',
     'Treat cargo as remaining hull volume and correct the effective cargo allocation from the published 23 tons to 22 tons.'),
    ('ship.class.system-defense-boat','CE-SHIP-006',
     'Treat cargo as remaining hull volume and correct the effective cargo allocation from the published 109 tons to 107 tons.'),
    ('ship.class.cutter','CE-SHIP-007',
     'Treat otherwise unallocated hull volume as cargo and correct the effective cargo allocation from the published 1.3 tons to 4.3 tons.')
) decision(rule_code,decision_code,rationale)
JOIN rule_rule rule ON rule.rule_code=decision.rule_code;

WITH prior AS (
    SELECT DISTINCT ON (receipt.ship_class_rule_id) receipt.*
    FROM ship_class_construction_receipt receipt
    JOIN ship_class class USING (ship_class_rule_id)
    WHERE class.class_code IN (
        'corvette','cutter','destroyer','dreadnought','heavy-cruiser',
        'light-cruiser','patrol-frigate','system-defense-boat',
        'system-monitor'
    )
      AND receipt.finalized
    ORDER BY receipt.ship_class_rule_id,receipt.receipt_version DESC
)
INSERT INTO ship_class_construction_receipt (
    ship_class_rule_id,receipt_version,standard_design_discount_rate,
    receipt_status,source_locator_id,supersedes_receipt_id,
    published_variance_allowed
)
SELECT ship_class_rule_id,receipt_version+1,
       standard_design_discount_rate,receipt_status,source_locator_id,
       construction_receipt_id,published_variance_allowed
FROM prior;

WITH current_pair AS (
    SELECT class.class_code,old_receipt.construction_receipt_id AS old_id,
           new_receipt.construction_receipt_id AS new_id
    FROM ship_class class
    JOIN ship_class_construction_receipt new_receipt
      ON new_receipt.ship_class_rule_id=class.ship_class_rule_id
    JOIN ship_class_construction_receipt old_receipt
      ON old_receipt.construction_receipt_id=new_receipt.supersedes_receipt_id
    WHERE class.class_code IN (
        'corvette','cutter','destroyer','dreadnought','heavy-cruiser',
        'light-cruiser','patrol-frigate','system-defense-boat',
        'system-monitor'
    )
      AND NOT new_receipt.finalized
), adjusted AS (
    SELECT line.*,pair.class_code,pair.new_id,
           CASE
             WHEN line.line_kind='armor' AND pair.class_code='destroyer'
               THEN 110::numeric
             WHEN line.line_kind='armor' AND pair.class_code='heavy-cruiser'
               THEN 275::numeric
             WHEN line.line_kind='armor' AND pair.class_code='light-cruiser'
               THEN 137.5::numeric
             WHEN line.line_kind='armor' AND pair.class_code='system-monitor'
               THEN 225::numeric
             WHEN line.line_kind='component'
              AND line.reference_code='cargo-hold'
               THEN CASE pair.class_code
                 WHEN 'corvette' THEN 17::numeric
                 WHEN 'cutter' THEN 4.3::numeric
                 WHEN 'destroyer' THEN 28.5::numeric
                 WHEN 'dreadnought' THEN 385::numeric
                 WHEN 'patrol-frigate' THEN 22::numeric
                 WHEN 'system-defense-boat' THEN 107::numeric
                 ELSE line.allocated_tons
               END
             ELSE line.allocated_tons
           END AS effective_tons
    FROM current_pair pair
    JOIN ship_class_construction_line line
      ON line.construction_receipt_id=pair.old_id
)
INSERT INTO ship_class_construction_line (
    ship_class_rule_id,line_order,line_kind,reference_code,quantity,
    allocated_tons,cost_minor,calculation_basis,source_locator_id,
    construction_receipt_id,discount_eligible,line_status
)
SELECT ship_class_rule_id,line_order,line_kind,reference_code,
       CASE WHEN line_kind='armor' AND effective_tons<>allocated_tons
            THEN quantity*effective_tons/allocated_tons ELSE quantity END,
       effective_tons,
       CASE WHEN line_kind='armor' AND effective_tons<>allocated_tons
            THEN round(cost_minor*effective_tons/allocated_tons)::bigint
            ELSE cost_minor END,
       CASE
         WHEN line_kind='armor' AND effective_tons<>allocated_tons
           THEN 'CE-SHIP-005 prorated final capped armor increment'
         WHEN line_kind='component' AND reference_code='cargo-hold'
              AND effective_tons<>allocated_tons AND class_code='cutter'
           THEN 'CE-SHIP-007 remaining hull volume allocated to cargo'
         WHEN line_kind='component' AND reference_code='cargo-hold'
              AND effective_tons<>allocated_tons
           THEN CASE WHEN class_code='destroyer'
                     THEN 'CE-SHIP-005 cargo remaining after corrected drives'
                     ELSE 'CE-SHIP-006 cargo corrected to remaining hull volume'
                END
         ELSE calculation_basis
       END,
       source_locator_id,new_id,discount_eligible,
       CASE WHEN effective_tons<>allocated_tons THEN 'calculated'
            ELSE line_status END
FROM adjusted;

UPDATE ship_class_construction_receipt receipt
SET finalized=true
FROM ship_class class
WHERE class.ship_class_rule_id=receipt.ship_class_rule_id
  AND class.class_code IN (
      'corvette','cutter','destroyer','dreadnought','heavy-cruiser',
      'light-cruiser','patrol-frigate','system-defense-boat',
      'system-monitor'
  )
  AND NOT receipt.finalized;

UPDATE src_issue issue
SET issue_status='resolved',resolved_at=clock_timestamp(),
    resolution_summary=resolution.summary,
    engine_disposition='preserve_rule'
FROM (VALUES
    ('ship.corvette.construction.tonnage',
     'CE-SHIP-006 corrects effective cargo to 17 tons; the published 25-ton value remains preserved in the superseded receipt.'),
    ('ship.cutter.construction.tonnage',
     'CE-SHIP-007 allocates the remaining hull volume to cargo, producing an effective 4.3-ton cargo hold.'),
    ('ship.destroyer.construction.tonnage',
     'CE-SHIP-005 prorates the final armor increment to 110 tons and preserves the originally published worksheet as provenance.'),
    ('ship.dreadnought.construction.tonnage',
     'CE-SHIP-006 corrects effective cargo to 385 tons; the published 412-ton value remains preserved in the superseded receipt.'),
    ('ship.heavy-cruiser.construction.tonnage',
     'CE-SHIP-005 prorates the final armor increment to 275 tons while preserving 11 protection and published cargo.'),
    ('ship.light-cruiser.construction.tonnage',
     'CE-SHIP-005 prorates the final armor increment to 137.5 tons while preserving 11 protection and published cargo.'),
    ('ship.patrol-frigate.construction.tonnage',
     'CE-SHIP-006 corrects effective cargo to 22 tons; the published 23-ton value remains preserved in the superseded receipt.'),
    ('ship.system-defense-boat.construction.tonnage',
     'CE-SHIP-006 corrects effective cargo to 107 tons; the published 109-ton value remains preserved in the superseded receipt.'),
    ('ship.system-monitor.construction.tonnage',
     'CE-SHIP-005 prorates the final armor increment to 225 tons while preserving 9 protection and published cargo.'),
    ('ship.destroyer.construction.tonnage-adjudicated-drives',
     'CE-SHIP-005 reconciles the corrected H/N-drive design to 800 tons with 110 tons of armor and 28.5 tons of cargo.')
) resolution(issue_code,summary)
WHERE issue.issue_code=resolution.issue_code;
