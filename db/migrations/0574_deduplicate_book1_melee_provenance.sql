WITH ranked AS (
    SELECT provenance.record_provenance_id,
           row_number() OVER (
               PARTITION BY provenance.rule_id,locator.source_work_id
               ORDER BY provenance.recorded_at,
                        provenance.record_provenance_id
           ) AS duplicate_order
    FROM src_record_provenance provenance
    JOIN src_locator locator
      ON locator.source_locator_id=provenance.source_locator_id
    JOIN rule_book1_melee_attack melee
      ON melee.rule_id=provenance.rule_id
    WHERE locator.heading_path=
          'Equipment > Weapons > Common Personal Melee Weapons'
)
DELETE FROM src_record_provenance provenance
USING ranked
WHERE provenance.record_provenance_id=ranked.record_provenance_id
  AND ranked.duplicate_order > 1;
