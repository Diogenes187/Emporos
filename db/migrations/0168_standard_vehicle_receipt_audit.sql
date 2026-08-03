CREATE TABLE vehicle_class_construction_variance (
    construction_variance_id bigint GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,
    construction_receipt_id bigint NOT NULL REFERENCES
        vehicle_class_construction_receipt(construction_receipt_id),
    variance_dimension text NOT NULL CHECK (
        variance_dimension IN (
            'space','stated_subtotal','published_cost'
        )
    ),
    variance_amount numeric NOT NULL CHECK (variance_amount<>0),
    explanation_code text NOT NULL CHECK (
        explanation_code IN (
            'published-arithmetic-conflict',
            'published-total-unitemized',
            'published-rounding-conflict'
        )
    ),
    audit_status text NOT NULL CHECK (
        audit_status IN ('source_conflict','unresolved')
    ),
    source_issue_id bigint NOT NULL REFERENCES
        src_issue(source_issue_id),
    UNIQUE (construction_receipt_id,variance_dimension)
);

INSERT INTO src_issue (
    issue_code,domain_code,issue_type,review_priority,
    subject_code,title,problem_statement,
    published_value,calculated_value,
    reviewer_question,requested_evidence,engine_disposition
)
VALUES
    (
        'vehicle.class.air-raft-construction-arithmetic',
        'vehicle.catalogue','arithmetic_conflict','medium',
        'air-raft',
        'Air/Raft spaces and final price do not reconcile',
        'The Air/Raft design lines consume 18.32 spaces and leave 24.57 cargo spaces in a 48-space chassis, leaving 5.11 spaces unaccounted. Its line costs total Cr104,614.51 while the table states Cr104,614.5 and Cr94,160 after discount, but the prose publishes Cr94,340.',
        '48 spaces; subtotal Cr104,614.5; final Cr94,160 or Cr94,340',
        '42.89 itemized spaces; line subtotal Cr104,614.51; discounted Cr94,150',
        'What components consume the missing 5.11 spaces, and which final Air/Raft price is authoritative?',
        'Publisher errata or a corrected Air/Raft construction worksheet.',
        'preserve_published'
    ),
    (
        'vehicle.class.g-carrier-design-subtotal',
        'vehicle.catalogue','arithmetic_conflict','high',
        'g-carrier',
        'G/Carrier stated subtotal exceeds its itemized lines',
        'The G/Carrier itemized lines total Cr1,518,682.24, but the table states Cr3,487,282.24. The Cr1,968,600 difference is not explained by its already inconsistent autopilot row or another listed component.',
        'Cr3,487,282.24',
        'Cr1,518,682.24 itemized',
        'Which G/Carrier component or price accounts for the Cr1,968,600 difference?',
        'Publisher errata or a complete corrected G/Carrier worksheet.',
        'preserve_published'
    ),
    (
        'vehicle.class.grav-tank-subtotal-omits-weapon',
        'vehicle.catalogue','arithmetic_conflict','high',
        'grav-tank',
        'Grav Tank subtotal omits the Beam Laser price',
        'The Grav Tank itemized lines total Cr1,732,659.48, exactly Cr100,000 more than the stated subtotal. The difference equals the published price of its listed Beam Laser-TL 9.',
        'Cr1,632,659.48',
        'Cr1,732,659.48 including the listed Beam Laser',
        'Should the Grav Tank subtotal and discounted final price include its Beam Laser?',
        'Publisher errata or a corrected Grav Tank construction worksheet.',
        'preserve_published'
    ),
    (
        'vehicle.class.speeder-unitemized-subtotal',
        'vehicle.catalogue','published_total_variance','medium',
        'speeder',
        'Speeder subtotal contains an unitemized Cr2,000',
        'The Speeder itemized lines total Cr364,957.256, while the table states Cr366,957.256. No listed component accounts for the additional Cr2,000.',
        'Cr366,957.256',
        'Cr364,957.256 itemized',
        'What Speeder component or fee accounts for the extra Cr2,000?',
        'Publisher errata or a complete corrected Speeder worksheet.',
        'source_gap_pending'
    ),
    (
        'vehicle.class.helicopter-final-price',
        'vehicle.catalogue','arithmetic_conflict','low',
        'helicopter',
        'Helicopter final price conflicts with its stated subtotal',
        'The Helicopter table subtotal of Cr172,055.95 produces Cr154,850 when the standard-design discount is applied and rounded to tens, but the profile publishes Cr154,810.',
        'Cr154,810',
        'Cr154,850 from the stated subtotal',
        'Should the Helicopter final price be corrected to Cr154,850?',
        'Publisher errata or a corrected Helicopter construction worksheet.',
        'preserve_published'
    );

INSERT INTO src_issue_locator (
    source_issue_id,source_locator_id,evidence_role
)
SELECT issue.source_issue_id,locator.source_locator_id,'primary'
FROM src_issue issue
JOIN src_locator locator
  ON locator.heading_path=CASE issue.issue_code
      WHEN 'vehicle.class.air-raft-construction-arithmetic'
          THEN 'Common Grav Vehicles > TL9 Air/Raft'
      WHEN 'vehicle.class.g-carrier-design-subtotal'
          THEN 'Common Grav Vehicles > TL15 G/Carrier'
      WHEN 'vehicle.class.grav-tank-subtotal-omits-weapon'
          THEN 'Common Grav Vehicles > TL9 Grav Tank'
      WHEN 'vehicle.class.speeder-unitemized-subtotal'
          THEN 'Common Grav Vehicles > TL9 Speeder'
      WHEN 'vehicle.class.helicopter-final-price'
          THEN 'Common Aircraft > TL7 Helicopter'
  END
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1'
WHERE issue.issue_code IN (
    'vehicle.class.air-raft-construction-arithmetic',
    'vehicle.class.g-carrier-design-subtotal',
    'vehicle.class.grav-tank-subtotal-omits-weapon',
    'vehicle.class.speeder-unitemized-subtotal',
    'vehicle.class.helicopter-final-price'
);

INSERT INTO src_issue_locator (
    source_issue_id,source_locator_id,evidence_role
)
SELECT issue.source_issue_id,locator.source_locator_id,'corroborating'
FROM src_issue issue
JOIN src_locator locator
  ON locator.heading_path=CASE issue.issue_code
      WHEN 'vehicle.class.air-raft-construction-arithmetic'
          THEN 'Common Grav Vehicles > TL9 Air/Raft'
      WHEN 'vehicle.class.g-carrier-design-subtotal'
          THEN 'Common Grav Vehicles > TL15 G/Carrier'
      WHEN 'vehicle.class.grav-tank-subtotal-omits-weapon'
          THEN 'Common Grav Vehicles > TL9 Grav Tank'
      WHEN 'vehicle.class.speeder-unitemized-subtotal'
          THEN 'Common Grav Vehicles > TL9 Speeder'
      WHEN 'vehicle.class.helicopter-final-price'
          THEN 'Common Aircraft > TL7 Helicopter'
  END
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.ogn'
WHERE issue.issue_code IN (
    'vehicle.class.air-raft-construction-arithmetic',
    'vehicle.class.g-carrier-design-subtotal',
    'vehicle.class.grav-tank-subtotal-omits-weapon',
    'vehicle.class.speeder-unitemized-subtotal',
    'vehicle.class.helicopter-final-price'
);

INSERT INTO vehicle_class_construction_variance (
    construction_receipt_id,variance_dimension,variance_amount,
    explanation_code,audit_status,source_issue_id
)
SELECT total.construction_receipt_id,source.dimension,
       source.amount,source.explanation_code,
       source.audit_status,issue.source_issue_id
FROM (
    VALUES
        ('air-raft','space',5.11::numeric,
         'published-arithmetic-conflict','source_conflict',
         'vehicle.class.air-raft-construction-arithmetic'),
        ('air-raft','published_cost',190,
         'published-arithmetic-conflict','source_conflict',
         'vehicle.class.air-raft-construction-arithmetic'),
        ('g-carrier','stated_subtotal',1968600,
         'published-total-unitemized','unresolved',
         'vehicle.class.g-carrier-design-subtotal'),
        ('grav-tank','stated_subtotal',-100000,
         'published-arithmetic-conflict','source_conflict',
         'vehicle.class.grav-tank-subtotal-omits-weapon'),
        ('speeder','stated_subtotal',2000,
         'published-total-unitemized','unresolved',
         'vehicle.class.speeder-unitemized-subtotal'),
        ('helicopter','published_cost',-40,
         'published-rounding-conflict','source_conflict',
         'vehicle.class.helicopter-final-price'),
        ('afv-tracked','stated_subtotal',5000,
         'published-arithmetic-conflict','source_conflict',
         'vehicle.class.tracked-autopilot-price'),
        ('atv-tracked','stated_subtotal',5000,
         'published-arithmetic-conflict','source_conflict',
         'vehicle.class.tracked-autopilot-price')
) source(
    class_code,dimension,amount,explanation_code,
    audit_status,issue_code
)
JOIN vehicle_class class USING (class_code)
JOIN vehicle_class_construction_total total
  USING (vehicle_class_rule_id)
JOIN src_issue issue USING (issue_code);

CREATE VIEW vehicle_class_construction_material_variance AS
SELECT variance.construction_variance_id,
       variance.construction_receipt_id,
       receipt.vehicle_class_rule_id,
       class.class_code,variance.variance_dimension,
       variance.variance_amount,variance.explanation_code,
       variance.audit_status,issue.issue_code
FROM vehicle_class_construction_variance variance
JOIN vehicle_class_construction_receipt receipt
  USING (construction_receipt_id)
JOIN vehicle_class class USING (vehicle_class_rule_id)
JOIN src_issue issue USING (source_issue_id);

INSERT INTO src_issue_comparison_check (
    source_issue_id,comparison_work_id,source_locator_id,
    check_status,evidence_summary
)
SELECT issue.source_issue_id,work.source_work_id,
       locator.source_locator_id,'no_independent_calculation',
       CASE issue.issue_code
           WHEN 'vehicle.class.helicopter-final-price'
               THEN 'The predecessor retains the same copied Helicopter table but has no construction total calculator.'
           ELSE
               'The predecessor retains the same copied vehicle profile but has no construction worksheet or independent arithmetic.'
       END
FROM src_issue issue
JOIN src_work work
  ON work.work_code='cepheus-game.legacy-local'
JOIN src_locator locator
  ON locator.source_work_id=work.source_work_id
 AND locator.heading_path=CASE
      WHEN issue.issue_code='vehicle.class.helicopter-final-price'
          THEN 'reference/srd/src/vds/common-aircraft.md'
      ELSE 'reference/srd/src/vds/common-grav-vehicles.md'
  END
WHERE issue.issue_code IN (
    'vehicle.class.air-raft-construction-arithmetic',
    'vehicle.class.g-carrier-design-subtotal',
    'vehicle.class.grav-tank-subtotal-omits-weapon',
    'vehicle.class.speeder-unitemized-subtotal',
    'vehicle.class.helicopter-final-price'
);
