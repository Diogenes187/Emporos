ALTER TABLE ship_class_construction_receipt
    DROP CONSTRAINT
        ship_class_construction_receipt_ship_class_rule_id_key,
    ADD COLUMN supersedes_receipt_id bigint REFERENCES
        ship_class_construction_receipt(construction_receipt_id),
    ADD COLUMN published_variance_allowed boolean NOT NULL
        DEFAULT false,
    ADD CONSTRAINT ship_class_construction_receipt_version_key
        UNIQUE (ship_class_rule_id,receipt_version),
    ADD CONSTRAINT ship_class_construction_receipt_supersedes_check CHECK (
        supersedes_receipt_id IS NULL OR receipt_version>1
    );

CREATE UNIQUE INDEX ship_class_construction_receipt_superseded_once
    ON ship_class_construction_receipt(supersedes_receipt_id)
    WHERE supersedes_receipt_id IS NOT NULL;

ALTER TABLE ship_class_construction_receipt
    DISABLE TRIGGER ship_construction_receipt_immutable;

UPDATE ship_class_construction_receipt receipt
SET published_variance_allowed=true
FROM ship_class_construction_total total
WHERE total.construction_receipt_id=receipt.construction_receipt_id
  AND total.unallocated_tons<0;

ALTER TABLE ship_class_construction_receipt
    ENABLE TRIGGER ship_construction_receipt_immutable;

CREATE OR REPLACE FUNCTION ship_construction_receipts_immutable()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP='UPDATE'
       AND NOT OLD.finalized
       AND NEW.finalized
       AND NEW.construction_receipt_id=OLD.construction_receipt_id
       AND NEW.ship_class_rule_id=OLD.ship_class_rule_id
       AND NEW.receipt_version=OLD.receipt_version
       AND NEW.standard_design_discount_rate=
           OLD.standard_design_discount_rate
       AND NEW.receipt_status=OLD.receipt_status
       AND NEW.source_locator_id=OLD.source_locator_id
       AND NEW.supersedes_receipt_id IS NOT DISTINCT FROM
           OLD.supersedes_receipt_id
       AND NEW.published_variance_allowed=
           OLD.published_variance_allowed THEN
        RETURN NEW;
    END IF;
    RAISE EXCEPTION 'Ship construction receipts are immutable'
        USING ERRCODE='23514';
END;
$$;

ALTER TABLE ship_class_construction_line
    DROP CONSTRAINT
        ship_class_construction_line_ship_class_rule_id_line_order_key,
    ADD CONSTRAINT ship_class_construction_line_receipt_order_key
        UNIQUE (construction_receipt_id,line_order);

CREATE OR REPLACE FUNCTION ship_validate_construction_line()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    hull_capacity numeric;
    already_allocated numeric;
    variance_allowed boolean;
BEGIN
    SELECT hull_tons INTO hull_capacity
    FROM ship_class
    WHERE ship_class_rule_id=NEW.ship_class_rule_id;

    SELECT coalesce(sum(allocated_tons),0)
    INTO already_allocated
    FROM ship_class_construction_line
    WHERE construction_receipt_id=NEW.construction_receipt_id;

    SELECT published_variance_allowed INTO variance_allowed
    FROM ship_class_construction_receipt
    WHERE construction_receipt_id=NEW.construction_receipt_id;

    IF already_allocated+NEW.allocated_tons>hull_capacity
       AND NOT variance_allowed THEN
        RAISE EXCEPTION
            'Ship construction lines exceed hull tonnage'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

ALTER VIEW ship_class_construction_total
    RENAME TO ship_class_construction_receipt_total;

CREATE VIEW ship_class_construction_total AS
SELECT total.*
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

INSERT INTO rule_rule (
    content_package_id,rule_code,name,rule_category,rule_status
)
SELECT package.content_package_id,
       'ship.component.more-cabin-space',
       'More Cabin Space','ship','approved'
FROM sys_content_package package
WHERE package.package_code='cepheus-engine';

INSERT INTO ship_component_definition (
    component_rule_id,component_code,component_kind,
    minimum_tech_level,unit_tons,unit_cost_minor,
    source_locator_id,tonnage_basis,tonnage_factor,
    cost_basis,capacity_kind,capacity_per_unit,
    effect_code,calculation_status
)
SELECT rule.rule_id,'more-cabin-space','other',NULL,
       1.5,50000,locator.source_locator_id,
       'fixed',1,'per_component_ton','person',1,
       'small-craft-passenger-cabin','published'
FROM rule_rule rule
JOIN src_locator locator
  ON locator.heading_path=
     'Ship Design and Construction > Small Craft Cockpits and Control Cabins'
 AND locator.display_citation LIKE 'Cepheus Engine v9.1,%'
WHERE rule.rule_code='ship.component.more-cabin-space';

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
     'Ship Design and Construction > Small Craft Cockpits and Control Cabins'
WHERE rule.rule_code='ship.component.more-cabin-space';

INSERT INTO ship_class_component (
    ship_class_rule_id,component_rule_id,quantity,rating,
    allocated_tons,display_order,source_locator_id
)
SELECT class.ship_class_rule_id,component.component_rule_id,
       1,1,1.5,5,class.source_locator_id
FROM ship_class class
JOIN ship_component_definition component
  ON component.component_code='more-cabin-space'
WHERE class.class_code='cutter';

WITH prior AS (
    SELECT receipt.*
    FROM ship_class_construction_receipt receipt
    JOIN ship_class class USING (ship_class_rule_id)
    WHERE class.class_code='cutter'
      AND receipt.receipt_version=1
)
INSERT INTO ship_class_construction_receipt (
    ship_class_rule_id,receipt_version,
    standard_design_discount_rate,receipt_status,
    source_locator_id,supersedes_receipt_id
)
SELECT ship_class_rule_id,2,standard_design_discount_rate,
       receipt_status,source_locator_id,construction_receipt_id
FROM prior;

WITH prior AS (
    SELECT receipt.construction_receipt_id,
           receipt.ship_class_rule_id
    FROM ship_class_construction_receipt receipt
    JOIN ship_class class USING (ship_class_rule_id)
    WHERE class.class_code='cutter'
      AND receipt.receipt_version=1
),
replacement AS (
    SELECT receipt.construction_receipt_id,
           receipt.ship_class_rule_id
    FROM ship_class_construction_receipt receipt
    JOIN ship_class class USING (ship_class_rule_id)
    WHERE class.class_code='cutter'
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
SELECT class.ship_class_rule_id,11,'component',
       component.component_code,1,selected.allocated_tons,
       round(
           component.unit_cost_minor*selected.allocated_tons
       )::bigint,
       component.tonnage_basis||' / '||component.cost_basis,
       selected.source_locator_id,receipt.construction_receipt_id,
       true,'calculated'
FROM ship_class class
JOIN ship_class_component selected USING (ship_class_rule_id)
JOIN ship_component_definition component USING (component_rule_id)
JOIN ship_class_construction_receipt receipt USING (
    ship_class_rule_id
)
WHERE class.class_code='cutter'
  AND component.component_code='more-cabin-space'
  AND receipt.receipt_version=2;

UPDATE ship_class_construction_receipt receipt
SET finalized=true
FROM ship_class class
WHERE class.ship_class_rule_id=receipt.ship_class_rule_id
  AND class.class_code='cutter'
  AND receipt.receipt_version=2;
