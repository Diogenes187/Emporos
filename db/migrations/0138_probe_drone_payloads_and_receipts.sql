INSERT INTO src_locator (
    source_work_id,source_artifact_id,locator_type,
    heading_path,display_citation
)
SELECT artifact.source_work_id,artifact.source_artifact_id,
       'heading',
       'Equipment > Robots and Drones > Probe Drone',
       CASE
           WHEN artifact.source_uri='src/book1/equipment.md'
               THEN 'Cepheus Engine v9.1, Equipment: Probe Drone'
           ELSE 'Cepheus Engine OGN, Equipment: Probe Drone'
       END
FROM src_artifact artifact
WHERE artifact.source_uri IN (
    'src/book1/equipment.md',
    'https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-equipment/'
);

INSERT INTO rule_rule (
    content_package_id,rule_code,name,rule_category,rule_status
)
SELECT package.content_package_id,
       'equipment.probe-drone','Probe Drone','equipment','approved'
FROM sys_content_package package
WHERE package.package_code='cepheus-engine';

INSERT INTO inv_item_definition (
    rule_id,item_kind,minimum_tech_level,cost_credits,
    mass_grams,inherent
)
SELECT rule.rule_id,'equipment',11,15000,NULL,false
FROM rule_rule rule
WHERE rule.rule_code='equipment.probe-drone';

INSERT INTO src_record_provenance (
    rule_id,content_package_id,source_locator_id,
    provenance_class,is_primary_citation
)
SELECT rule.rule_id,rule.content_package_id,
       locator.source_locator_id,'direct',
       locator.display_citation LIKE 'Cepheus Engine v9.1,%'
FROM rule_rule rule
JOIN src_locator locator
  ON locator.heading_path=
     'Equipment > Robots and Drones > Probe Drone'
WHERE rule.rule_code='equipment.probe-drone';

CREATE TABLE ship_class_carried_item (
    carrier_class_rule_id bigint NOT NULL REFERENCES
        ship_class(ship_class_rule_id),
    hangar_identifier text NOT NULL,
    item_rule_id bigint NOT NULL REFERENCES
        inv_item_definition(rule_id),
    item_count integer NOT NULL CHECK (item_count>0),
    relationship_status text NOT NULL CHECK (
        relationship_status IN ('published','published_tl_conflict')
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    PRIMARY KEY (
        carrier_class_rule_id,hangar_identifier,item_rule_id
    ),
    FOREIGN KEY (carrier_class_rule_id,hangar_identifier)
        REFERENCES ship_class_hangar_option(
            ship_class_rule_id,hangar_identifier
        )
);

CREATE OR REPLACE FUNCTION ship_validate_class_carried_item()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    capacity integer;
    class_tl smallint;
    item_tl smallint;
BEGIN
    SELECT hangar.installation_count*
           option.units_per_installation,
           class.minimum_tech_level,
           item.minimum_tech_level
    INTO capacity,class_tl,item_tl
    FROM ship_class_hangar_option hangar
    JOIN rule_ship_hangar_option option USING (hangar_option_code)
    JOIN ship_class class
      ON class.ship_class_rule_id=hangar.ship_class_rule_id
    JOIN inv_item_definition item
      ON item.rule_id=NEW.item_rule_id
    WHERE hangar.ship_class_rule_id=NEW.carrier_class_rule_id
      AND hangar.hangar_identifier=NEW.hangar_identifier;

    IF NEW.item_count>capacity
       OR (
           class_tl<item_tl
           AND NEW.relationship_status<>'published_tl_conflict'
       )
       OR (
           class_tl>=item_tl
           AND NEW.relationship_status<>'published'
       ) THEN
        RAISE EXCEPTION
            'Carried item exceeds hangar capacity or conflicts with tech level'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER ship_class_carried_item_valid
BEFORE INSERT OR UPDATE ON ship_class_carried_item
FOR EACH ROW EXECUTE FUNCTION ship_validate_class_carried_item();

INSERT INTO ship_class_carried_item (
    carrier_class_rule_id,hangar_identifier,item_rule_id,
    item_count,relationship_status,source_locator_id
)
SELECT class.ship_class_rule_id,'probe-drone-sets',
       item.rule_id,source.item_count,source.relationship_status,
       class.source_locator_id
FROM (
    VALUES
        ('research-vessel',15,'published_tl_conflict'),
        ('survey-vessel',20,'published')
) source(class_code,item_count,relationship_status)
JOIN ship_class class
  ON class.class_code=source.class_code
JOIN rule_rule item
  ON item.rule_code='equipment.probe-drone';

INSERT INTO ship_class_source_assertion (
    ship_class_rule_id,field_code,published_value,canonical_value,
    assertion_status,rationale,source_locator_id
)
SELECT class.ship_class_rule_id,'probe-drone-tech-level',
       'TL9 vessel includes Probe Drones',NULL,
       'unresolved_conflict',
       'The common Research Vessel is TL9, while the equipment catalogue defines Probe Drones at TL11.',
       class.source_locator_id
FROM ship_class class
WHERE class.class_code='research-vessel';

ALTER TABLE ship_class_construction_line
    DROP CONSTRAINT ship_class_construction_line_line_kind_check,
    ADD CONSTRAINT ship_class_construction_line_line_kind_check CHECK (
        line_kind IN (
            'hull','configuration','armor','armor_option','bridge',
            'jump_drive','maneuver_drive','power_plant','fuel',
            'computer','computer_option','software','electronics',
            'crew_space','component','hangar','carried_craft',
            'carried_item','weapon','screen','ammunition',
            'discount','fee','other'
        )
    );

WITH current_receipt AS (
    SELECT receipt.*
    FROM ship_class_construction_receipt receipt
    JOIN ship_class_construction_total total USING (
        construction_receipt_id,ship_class_rule_id
    )
    JOIN ship_class class USING (ship_class_rule_id)
    WHERE class.class_code IN ('research-vessel','survey-vessel')
)
INSERT INTO ship_class_construction_receipt (
    ship_class_rule_id,receipt_version,
    standard_design_discount_rate,receipt_status,
    source_locator_id,supersedes_receipt_id,
    published_variance_allowed
)
SELECT prior.ship_class_rule_id,prior.receipt_version+1,
       prior.standard_design_discount_rate,
       CASE class.class_code
           WHEN 'research-vessel' THEN 'source_gap'
           ELSE prior.receipt_status
       END,
       prior.source_locator_id,prior.construction_receipt_id,
       prior.published_variance_allowed
FROM current_receipt prior
JOIN ship_class class USING (ship_class_rule_id);

WITH prior AS (
    SELECT receipt.construction_receipt_id,
           receipt.ship_class_rule_id
    FROM ship_class_construction_receipt receipt
    JOIN ship_class class USING (ship_class_rule_id)
    WHERE class.class_code IN ('research-vessel','survey-vessel')
      AND receipt.receipt_version=1
),
replacement AS (
    SELECT receipt.construction_receipt_id,
           receipt.ship_class_rule_id
    FROM ship_class_construction_receipt receipt
    JOIN ship_class class USING (ship_class_rule_id)
    WHERE class.class_code IN ('research-vessel','survey-vessel')
      AND receipt.receipt_version=2
)
INSERT INTO ship_class_construction_line (
    ship_class_rule_id,line_order,line_kind,reference_code,
    quantity,allocated_tons,cost_minor,calculation_basis,
    source_locator_id,construction_receipt_id,
    discount_eligible,line_status
)
SELECT line.ship_class_rule_id,line.line_order,line.line_kind,
       line.reference_code,line.quantity,line.allocated_tons,
       line.cost_minor,line.calculation_basis,line.source_locator_id,
       replacement.construction_receipt_id,
       line.discount_eligible,line.line_status
FROM prior
JOIN replacement USING (ship_class_rule_id)
JOIN ship_class_construction_line line
  ON line.construction_receipt_id=prior.construction_receipt_id;

INSERT INTO ship_class_construction_line (
    ship_class_rule_id,line_order,line_kind,reference_code,
    quantity,allocated_tons,cost_minor,calculation_basis,
    source_locator_id,construction_receipt_id,
    discount_eligible,line_status
)
SELECT carried.carrier_class_rule_id,20,'carried_item',
       rule.rule_code,carried.item_count,0,
       carried.item_count*item.cost_credits,
       'published carried-item count * equipment unit cost',
       locator.source_locator_id,receipt.construction_receipt_id,
       true,'calculated'
FROM ship_class_carried_item carried
JOIN inv_item_definition item
  ON item.rule_id=carried.item_rule_id
JOIN rule_rule rule
  ON rule.rule_id=item.rule_id
JOIN ship_class_construction_receipt receipt
  ON receipt.ship_class_rule_id=carried.carrier_class_rule_id
 AND receipt.receipt_version=2
JOIN src_locator locator
  ON locator.heading_path=
     'Equipment > Robots and Drones > Probe Drone'
 AND locator.display_citation LIKE 'Cepheus Engine v9.1,%';

UPDATE ship_class_construction_receipt receipt
SET finalized=true
FROM ship_class class
WHERE class.ship_class_rule_id=receipt.ship_class_rule_id
  AND class.class_code IN ('research-vessel','survey-vessel')
  AND receipt.receipt_version=2;

CREATE OR REPLACE VIEW ship_class_construction_total AS
SELECT total.construction_receipt_id,total.ship_class_rule_id,
       total.hull_tons,total.allocated_tons,total.unallocated_tons,
       total.discountable_cost_minor,
       total.standard_design_discount_minor,
       total.excluded_cost_minor,total.calculated_cost_minor,
       total.published_cost_minor,total.cost_variance_minor,
       total.unresolved_line_count,
       CASE
           WHEN receipt.receipt_status='source_gap' THEN 'source_gap'
           ELSE total.reconciliation_status
       END AS reconciliation_status
FROM ship_class_construction_receipt_total total
JOIN ship_class_construction_receipt receipt USING (
    construction_receipt_id,ship_class_rule_id
)
WHERE NOT EXISTS (
    SELECT 1
    FROM ship_class_construction_receipt newer
    WHERE newer.ship_class_rule_id=receipt.ship_class_rule_id
      AND newer.receipt_version>receipt.receipt_version
);

INSERT INTO ship_class_construction_variance (
    construction_receipt_id,variance_dimension,variance_amount,
    explanation_code,audit_status,explanation,source_locator_id
)
SELECT total.construction_receipt_id,'cost',
       total.cost_variance_minor,
       'published-total-unitemized','unresolved',
       'The equipment cost of every carried probe drone is now included; the publication does not itemize the remaining final-price variance.',
       class.source_locator_id
FROM ship_class_construction_total total
JOIN ship_class class USING (ship_class_rule_id)
WHERE class.class_code IN ('research-vessel','survey-vessel')
  AND total.cost_variance_minor<>0;
