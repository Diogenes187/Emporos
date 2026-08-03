CREATE TABLE ship_class_construction_variance (
    construction_variance_id bigint GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,
    construction_receipt_id bigint NOT NULL REFERENCES
        ship_class_construction_receipt(construction_receipt_id),
    variance_dimension text NOT NULL CHECK (
        variance_dimension IN ('tonnage','cost')
    ),
    variance_amount numeric NOT NULL CHECK (variance_amount<>0),
    explanation_code text NOT NULL CHECK (
        explanation_code IN (
            'source-unspecified',
            'capped-armor-proration',
            'published-total-unitemized'
        )
    ),
    audit_status text NOT NULL CHECK (
        audit_status IN ('source_gap','rule_conflict','unresolved')
    ),
    explanation text NOT NULL CHECK (btrim(explanation)<>''),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    UNIQUE (construction_receipt_id,variance_dimension)
);

INSERT INTO ship_class_construction_variance (
    construction_receipt_id,variance_dimension,variance_amount,
    explanation_code,audit_status,explanation,source_locator_id
)
SELECT total.construction_receipt_id,'tonnage',
       total.unallocated_tons,
       CASE
           WHEN class.class_code='asteroid-miner'
               THEN 'source-unspecified'
           WHEN class.class_code IN (
               'destroyer','heavy-cruiser',
               'light-cruiser','system-monitor'
           ) THEN 'capped-armor-proration'
           ELSE 'published-total-unitemized'
       END,
       CASE
           WHEN class.class_code='asteroid-miner' THEN 'source_gap'
           WHEN class.class_code IN (
               'destroyer','heavy-cruiser',
               'light-cruiser','system-monitor'
           ) THEN 'rule_conflict'
           ELSE 'unresolved'
       END,
       CASE
           WHEN class.class_code='asteroid-miner' THEN
               'Four hull tons remain after every specified component; the published smelter has no construction profile.'
           WHEN class.class_code IN (
               'destroyer','heavy-cruiser',
               'light-cruiser','system-monitor'
           ) THEN
               'The variance exactly equals the fractional capped armor increment used by the common design; the construction rule requires whole 5-percent increments.'
           ELSE
               'Published component tonnage does not equal the stated hull and cargo total, and no governing source itemizes the difference.'
       END,
       class.source_locator_id
FROM ship_class_construction_total total
JOIN ship_class class USING (ship_class_rule_id)
WHERE total.unallocated_tons<>0;

INSERT INTO ship_class_construction_variance (
    construction_receipt_id,variance_dimension,variance_amount,
    explanation_code,audit_status,explanation,source_locator_id
)
SELECT total.construction_receipt_id,'cost',
       total.cost_variance_minor,
       CASE
           WHEN class.class_code IN ('asteroid-miner','destroyer')
               THEN 'source-unspecified'
           ELSE 'published-total-unitemized'
       END,
       CASE
           WHEN class.class_code IN ('asteroid-miner','destroyer')
               THEN 'source_gap'
           ELSE 'unresolved'
       END,
       CASE
           WHEN class.class_code='asteroid-miner' THEN
               'The published final price cannot be reconstructed while the smelter cost remains unspecified.'
           WHEN class.class_code='destroyer' THEN
               'The published final price accompanies unresolved jump and maneuver drive conflicts.'
           ELSE
               'The publication states a final price including discounts and fees but does not itemize the remaining variance.'
       END,
       class.source_locator_id
FROM ship_class_construction_total total
JOIN ship_class class USING (ship_class_rule_id)
WHERE total.cost_variance_minor<>0;

CREATE VIEW ship_class_construction_variance_summary AS
SELECT class.ship_class_rule_id,class.class_code,
       receipt.construction_receipt_id,receipt.receipt_version,
       count(variance.construction_variance_id) AS variance_count,
       count(*) FILTER (
           WHERE variance.audit_status='source_gap'
       ) AS source_gap_count,
       count(*) FILTER (
           WHERE variance.audit_status='rule_conflict'
       ) AS rule_conflict_count,
       count(*) FILTER (
           WHERE variance.audit_status='unresolved'
       ) AS unresolved_count
FROM ship_class class
JOIN ship_class_construction_total total USING (ship_class_rule_id)
JOIN ship_class_construction_receipt receipt USING (
    construction_receipt_id,ship_class_rule_id
)
LEFT JOIN ship_class_construction_variance variance USING (
    construction_receipt_id
)
GROUP BY class.ship_class_rule_id,receipt.construction_receipt_id;
