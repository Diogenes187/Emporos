CREATE TABLE ship_class_construction_receipt (
    construction_receipt_id bigint GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,
    ship_class_rule_id bigint NOT NULL UNIQUE REFERENCES
        ship_class(ship_class_rule_id),
    receipt_version smallint NOT NULL DEFAULT 1 CHECK (
        receipt_version>0
    ),
    standard_design_discount_rate numeric NOT NULL CHECK (
        standard_design_discount_rate BETWEEN 0 AND 1
    ),
    receipt_status text NOT NULL CHECK (
        receipt_status IN ('complete','source_gap')
    ),
    finalized boolean NOT NULL DEFAULT false,
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    UNIQUE (construction_receipt_id,ship_class_rule_id)
);

DROP VIEW ship_class_construction_total;

ALTER TABLE ship_class_construction_line
    DROP CONSTRAINT ship_class_construction_line_line_kind_check,
    ADD CONSTRAINT ship_class_construction_line_line_kind_check CHECK (
        line_kind IN (
            'hull','configuration','armor','armor_option','bridge',
            'jump_drive','maneuver_drive','power_plant','fuel',
            'computer','computer_option','software','electronics',
            'crew_space','component','hangar','carried_craft',
            'weapon','screen','ammunition','discount','fee','other'
        )
    ),
    ADD COLUMN construction_receipt_id bigint,
    ADD COLUMN discount_eligible boolean NOT NULL DEFAULT true,
    ADD COLUMN line_status text NOT NULL DEFAULT 'calculated' CHECK (
        line_status IN (
            'calculated','published','included','source_unspecified'
        )
    ),
    ADD CONSTRAINT ship_construction_line_receipt_fkey
        FOREIGN KEY (construction_receipt_id,ship_class_rule_id)
        REFERENCES ship_class_construction_receipt(
            construction_receipt_id,ship_class_rule_id
        );

INSERT INTO ship_class_construction_receipt (
    ship_class_rule_id,standard_design_discount_rate,
    receipt_status,source_locator_id
)
SELECT class.ship_class_rule_id,
       CASE WHEN class.standard_design THEN 0.10 ELSE 0 END,
       CASE WHEN EXISTS (
           SELECT 1
           FROM ship_class_source_assertion assertion
           WHERE assertion.ship_class_rule_id=class.ship_class_rule_id
             AND assertion.assertion_status IN (
                 'unresolved_conflict','source_unspecified'
             )
       ) THEN 'source_gap' ELSE 'complete' END,
       class.source_locator_id
FROM ship_class class;

CREATE OR REPLACE FUNCTION ship_validate_construction_receipt_line()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    receipt_finalized boolean;
BEGIN
    SELECT finalized INTO receipt_finalized
    FROM ship_class_construction_receipt
    WHERE construction_receipt_id=NEW.construction_receipt_id
      AND ship_class_rule_id=NEW.ship_class_rule_id;

    IF receipt_finalized IS NULL OR receipt_finalized THEN
        RAISE EXCEPTION
            'Construction line requires an open matching receipt'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER ship_construction_line_receipt_open
BEFORE INSERT ON ship_class_construction_line
FOR EACH ROW EXECUTE FUNCTION ship_validate_construction_receipt_line();

ALTER TABLE ship_class_construction_line
    DISABLE TRIGGER ship_construction_line_capacity_valid;

WITH generated_line AS (
    SELECT class.ship_class_rule_id,'hull'::text AS line_kind,
           hull.hull_code AS reference_code,1::numeric AS quantity,
           0::numeric AS allocated_tons,
           hull.base_cost_minor AS cost_minor,
           'published hull table'::text AS calculation_basis,
           hull.source_locator_id,true AS discount_eligible,
           'published'::text AS line_status
    FROM ship_class class
    JOIN ship_class_design_hull design USING (ship_class_rule_id)
    JOIN rule_ship_hull_design hull USING (hull_code)

    UNION ALL

    SELECT class.ship_class_rule_id,'configuration',
           configuration.configuration_code,1,0,
           round(
               hull.base_cost_minor*
               (configuration.hull_cost_multiplier-1)
           )::bigint,
           'base hull cost * configuration delta',
           configuration.source_locator_id,true,'calculated'
    FROM ship_class class
    JOIN ship_class_design_hull design USING (ship_class_rule_id)
    JOIN rule_ship_hull_design hull USING (hull_code)
    JOIN rule_ship_configuration configuration USING (
        configuration_code
    )
    WHERE configuration.hull_cost_multiplier<>1

    UNION ALL

    SELECT class.ship_class_rule_id,'armor',armor.armor_code,
           design.armor_increments,
           greatest(
               class.hull_tons*armor.hull_percent_per_increment,
               armor.minimum_increment_tons
           )*design.armor_increments,
           round(
               hull.base_cost_minor*
               armor.base_hull_cost_multiplier*
               design.armor_increments
           )::bigint,
           'armor increments * hull percentage and base hull cost',
           armor.source_locator_id,true,'calculated'
    FROM ship_class class
    JOIN ship_class_design_hull design USING (ship_class_rule_id)
    JOIN rule_ship_hull_design hull USING (hull_code)
    JOIN rule_ship_armor_design armor USING (armor_code)

    UNION ALL

    SELECT class.ship_class_rule_id,'armor_option',
           option.armor_option_code,selected.installation_count,0,
           option.cost_minor_per_hull_ton*class.hull_tons::bigint*
               selected.installation_count,
           'cost per hull ton * installations',
           option.source_locator_id,true,'calculated'
    FROM ship_class class
    JOIN ship_class_armor_option selected USING (ship_class_rule_id)
    JOIN rule_ship_armor_option option USING (armor_option_code)

    UNION ALL

    SELECT class.ship_class_rule_id,'bridge',bridge.bridge_band_code,
           1,bridge.bridge_tons,
           ceil(class.hull_tons/100) *
               bridge.bridge_cost_minor_per_100_tons,
           'bridge band tons; cost per 100 hull tons',
           bridge.source_locator_id,true,'calculated'
    FROM ship_class class
    JOIN rule_ship_bridge_band bridge
      ON class.craft_scale='starship'
     AND class.hull_tons>=bridge.minimum_hull_tons
     AND (
         bridge.maximum_hull_tons IS NULL
         OR class.hull_tons<=bridge.maximum_hull_tons
     )

    UNION ALL

    SELECT selected.ship_class_rule_id,
           CASE selected.drive_kind
               WHEN 'jump' THEN 'jump_drive'
               WHEN 'maneuver' THEN 'maneuver_drive'
               ELSE 'power_plant'
           END,
           selected.drive_code,1,
           CASE selected.drive_kind
               WHEN 'jump' THEN drive.jump_drive_tons
               WHEN 'maneuver' THEN drive.maneuver_drive_tons
               ELSE drive.power_plant_tons
           END,
           CASE selected.drive_kind
               WHEN 'jump' THEN drive.jump_drive_cost_minor
               WHEN 'maneuver' THEN drive.maneuver_drive_cost_minor
               ELSE drive.power_plant_cost_minor
           END,
           'selected drive catalogue entry',
           drive.source_locator_id,true,
           CASE selected.validation_status
               WHEN 'published_conflict' THEN 'source_unspecified'
               ELSE 'published'
           END
    FROM ship_class_drive selected
    JOIN rule_ship_drive_design drive USING (craft_scale,drive_code)

    UNION ALL

    SELECT class.ship_class_rule_id,'fuel','fuel-tankage',1,
           fact.characteristic_value,0,
           'published fuel tankage',
           class.source_locator_id,true,'published'
    FROM ship_class class
    JOIN ship_class_characteristic fact USING (ship_class_rule_id)
    WHERE fact.characteristic_code='fuel_tons'

    UNION ALL

    SELECT selected.ship_class_rule_id,'computer',
           computer.computer_code,1,0,computer.cost_minor,
           'selected computer catalogue entry',
           computer.source_locator_id,true,'published'
    FROM ship_class_computer selected
    JOIN rule_ship_computer computer USING (computer_code)

    UNION ALL

    SELECT selected.ship_class_rule_id,'computer_option',
           option.computer_option_code,1,0,
           round(computer.cost_minor*
                 option.cost_multiplier_increment)::bigint,
           'computer cost * option increment',
           option.source_locator_id,true,'calculated'
    FROM ship_class_computer_option selected
    JOIN rule_ship_computer_option option USING (computer_option_code)
    JOIN ship_class_computer class_computer USING (ship_class_rule_id)
    JOIN rule_ship_computer computer USING (computer_code)

    UNION ALL

    SELECT selected.ship_class_rule_id,'software',
           software.software_code,selected.software_level,0,
           software.cost_minor_per_level*selected.software_level,
           'software level * cost per level',
           software.source_locator_id,true,'calculated'
    FROM ship_class_software selected
    JOIN rule_ship_software software USING (software_code)

    UNION ALL

    SELECT selected.ship_class_rule_id,'electronics',
           electronics.electronics_code,1,electronics.unit_tons,
           electronics.cost_minor,
           'selected electronics catalogue entry',
           electronics.source_locator_id,true,
           CASE WHEN electronics.included_in_bridge
                THEN 'included' ELSE 'published' END
    FROM ship_class_electronics selected
    JOIN rule_ship_electronics_suite electronics USING (
        electronics_code
    )

    UNION ALL

    SELECT selected.ship_class_rule_id,'component',
           component.component_code,selected.quantity,
           selected.allocated_tons,
           CASE component.cost_basis
               WHEN 'fixed' THEN
                   CASE
                       WHEN component.component_code='fuel-scoop'
                            AND class.hull_configuration='streamlined'
                       THEN 0
                       ELSE component.unit_cost_minor*selected.quantity
                   END
               WHEN 'per_person' THEN
                   component.unit_cost_minor*selected.rating::bigint
               WHEN 'per_component_ton' THEN
                   round(
                       component.unit_cost_minor*
                       selected.allocated_tons
                   )::bigint
               WHEN 'per_20_hull_tons' THEN
                   component.unit_cost_minor*
                   ceil(class.hull_tons/20)::bigint
               ELSE 0
           END,
           component.tonnage_basis||' / '||component.cost_basis,
           coalesce(
               selected.source_locator_id,
               component.source_locator_id,
               class.source_locator_id
           ),
           true,
           CASE
               WHEN component.component_code='fuel-scoop'
                    AND class.hull_configuration='streamlined'
               THEN 'included'
               ELSE CASE component.calculation_status
                   WHEN 'source_unspecified' THEN 'source_unspecified'
                   WHEN 'included' THEN 'included'
                   ELSE 'calculated'
               END
           END
    FROM ship_class_component selected
    JOIN ship_class class USING (ship_class_rule_id)
    JOIN ship_component_definition component USING (
        component_rule_id
    )

    UNION ALL

    SELECT selected.ship_class_rule_id,'hangar',
           selected.hangar_identifier,selected.installation_count,
           selected.allocated_tons,selected.installation_cost_minor,
           'published or formula hangar installation',
           coalesce(selected.source_locator_id,option.source_locator_id),
           true,
           CASE option.derivation_status
               WHEN 'source_unspecified' THEN 'source_unspecified'
               WHEN 'published' THEN 'published'
               ELSE 'calculated'
           END
    FROM ship_class_hangar_option selected
    JOIN rule_ship_hangar_option option USING (hangar_option_code)

    UNION ALL

    SELECT carried.carrier_class_rule_id,'carried_craft',
           craft.class_code,carried.craft_count,0,
           craft.construction_cost_minor*carried.craft_count,
           'published carried-craft unit cost; already discounted',
           carried.source_locator_id,false,'published'
    FROM ship_class_carried_craft carried
    JOIN ship_class craft
      ON craft.ship_class_rule_id=carried.carried_class_rule_id

    UNION ALL

    SELECT mount.ship_class_rule_id,'weapon',
           mount.mount_identifier,mount.mount_count,
           (mount_rule.allocated_tons+
            mount_rule.fire_control_tons)*mount.mount_count,
           (
               CASE
                   WHEN mount_rule.fixed_cost_minor IS NOT NULL THEN
                       mount_rule.fixed_cost_minor*mount.mount_count
                   WHEN mount_rule.cost_additive_minor IS NOT NULL THEN
                       mount_rule.cost_additive_minor*mount.mount_count
                   ELSE
                       pricing.fixed_cost_minor*
                       mount_rule.cost_multiplier*
                       mount.mount_count
               END
               +weapon.weapon_cost_minor*mount.mount_count
           )::bigint,
           'mount installation plus installed weapons',
           mount_rule.source_locator_id,true,'calculated'
    FROM ship_class_weapon_mount mount
    JOIN rule_ship_weapon_mount mount_rule USING (mount_code)
    LEFT JOIN rule_ship_weapon_mount pricing
      ON pricing.mount_code=mount.pricing_mount_code
    JOIN LATERAL (
        SELECT sum(definition.unit_cost_minor)::bigint
                   AS weapon_cost_minor
        FROM ship_class_mount_weapon selected_weapon
        JOIN ship_weapon_definition definition
          ON definition.weapon_rule_id=selected_weapon.weapon_rule_id
        WHERE selected_weapon.class_weapon_mount_id=
              mount.class_weapon_mount_id
    ) weapon ON true

    UNION ALL

    SELECT class.ship_class_rule_id,'weapon','reserved-fire-control',
           fact.characteristic_value, fact.characteristic_value,0,
           'published fire-control tonnage without installed mount',
           class.source_locator_id,true,'published'
    FROM ship_class class
    JOIN ship_class_characteristic fact USING (ship_class_rule_id)
    WHERE fact.characteristic_code='hardpoints'
      AND NOT EXISTS (
          SELECT 1
          FROM ship_class_weapon_mount mount
          WHERE mount.ship_class_rule_id=class.ship_class_rule_id
      )

    UNION ALL

    SELECT selected.ship_class_rule_id,'screen',screen.screen_code,
           selected.screen_count,
           screen.allocated_tons*selected.screen_count,
           screen.unit_cost_minor*selected.screen_count,
           'screen catalogue entry * count',
           screen.source_locator_id,true,'calculated'
    FROM ship_class_screen selected
    JOIN rule_ship_screen screen USING (screen_code)

    UNION ALL

    SELECT selected.ship_class_rule_id,'ammunition',
           selected.missile_code,selected.missile_count,
           selected.allocated_tons,
           missile.unit_cost_minor*selected.missile_count,
           'missile count * unit cost; discount excluded',
           missile.source_locator_id,false,'calculated'
    FROM ship_class_missile_store selected
    JOIN rule_ship_missile missile USING (missile_code)

    UNION ALL

    SELECT selected.ship_class_rule_id,'ammunition',
           selected.ammunition_code,selected.barrel_count,
           selected.allocated_tons,
           round(
               ammunition.cost_minor_per_ton*
               selected.allocated_tons
           )::bigint,
           'sand ammunition tons * cost per ton; discount excluded',
           ammunition.source_locator_id,false,'calculated'
    FROM ship_class_sand_store selected
    JOIN rule_ship_sand_ammunition ammunition USING (
        ammunition_code
    )
),
ordered_line AS (
    SELECT generated_line.*,
           row_number() OVER (
               PARTITION BY ship_class_rule_id
               ORDER BY
                   CASE line_kind
                       WHEN 'hull' THEN 10
                       WHEN 'configuration' THEN 20
                       WHEN 'armor' THEN 30
                       WHEN 'armor_option' THEN 40
                       WHEN 'bridge' THEN 50
                       WHEN 'jump_drive' THEN 60
                       WHEN 'maneuver_drive' THEN 70
                       WHEN 'power_plant' THEN 80
                       WHEN 'fuel' THEN 90
                       WHEN 'computer' THEN 100
                       WHEN 'computer_option' THEN 110
                       WHEN 'software' THEN 120
                       WHEN 'electronics' THEN 130
                       WHEN 'component' THEN 140
                       WHEN 'hangar' THEN 150
                       WHEN 'carried_craft' THEN 160
                       WHEN 'weapon' THEN 170
                       WHEN 'screen' THEN 180
                       WHEN 'ammunition' THEN 190
                       ELSE 900
                   END,
                   reference_code
           ) AS line_order
    FROM generated_line
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
       receipt.construction_receipt_id,line.discount_eligible,
       line.line_status
FROM ordered_line line
JOIN ship_class_construction_receipt receipt USING (
    ship_class_rule_id
);

ALTER TABLE ship_class_construction_line
    ENABLE TRIGGER ship_construction_line_capacity_valid;

ALTER TABLE ship_class_construction_line
    ALTER COLUMN construction_receipt_id SET NOT NULL;

UPDATE ship_class_construction_receipt
SET finalized=true;

CREATE VIEW ship_class_construction_total AS
WITH subtotal AS (
    SELECT receipt.construction_receipt_id,
           receipt.ship_class_rule_id,
           receipt.receipt_status,
           receipt.standard_design_discount_rate,
           coalesce(sum(line.allocated_tons),0) AS allocated_tons,
           coalesce(sum(line.cost_minor) FILTER (
               WHERE line.discount_eligible
           ),0)::bigint AS discountable_cost_minor,
           coalesce(sum(line.cost_minor) FILTER (
               WHERE NOT line.discount_eligible
           ),0)::bigint AS excluded_cost_minor,
           count(*) FILTER (
               WHERE line.line_status='source_unspecified'
           ) AS unresolved_line_count
    FROM ship_class_construction_receipt receipt
    LEFT JOIN ship_class_construction_line line USING (
        construction_receipt_id,ship_class_rule_id
    )
    GROUP BY receipt.construction_receipt_id
)
SELECT subtotal.construction_receipt_id,
       class.ship_class_rule_id,
       class.hull_tons,
       subtotal.allocated_tons,
       class.hull_tons-subtotal.allocated_tons AS unallocated_tons,
       subtotal.discountable_cost_minor,
       round(
           subtotal.discountable_cost_minor*
           subtotal.standard_design_discount_rate
       )::bigint AS standard_design_discount_minor,
       subtotal.excluded_cost_minor,
       (
           subtotal.discountable_cost_minor-
           round(
               subtotal.discountable_cost_minor*
               subtotal.standard_design_discount_rate
           )::bigint+
           subtotal.excluded_cost_minor
       )::bigint AS calculated_cost_minor,
       class.construction_cost_minor AS published_cost_minor,
       (
           class.construction_cost_minor-
           (
               subtotal.discountable_cost_minor-
               round(
                   subtotal.discountable_cost_minor*
                   subtotal.standard_design_discount_rate
               )::bigint+
               subtotal.excluded_cost_minor
           )
       )::bigint AS cost_variance_minor,
       subtotal.unresolved_line_count,
       CASE
           WHEN subtotal.unresolved_line_count>0 THEN 'source_gap'
           WHEN class.hull_tons<>subtotal.allocated_tons THEN
               'tonnage_variance'
           WHEN class.construction_cost_minor=(
               subtotal.discountable_cost_minor-
               round(
                   subtotal.discountable_cost_minor*
                   subtotal.standard_design_discount_rate
               )::bigint+
               subtotal.excluded_cost_minor
           ) THEN 'reconciled'
           ELSE 'cost_variance'
       END AS reconciliation_status
FROM subtotal
JOIN ship_class class USING (ship_class_rule_id);

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
       AND NEW.source_locator_id=OLD.source_locator_id THEN
        RETURN NEW;
    END IF;
    RAISE EXCEPTION 'Ship construction receipts are immutable'
        USING ERRCODE='23514';
END;
$$;

CREATE TRIGGER ship_construction_receipt_immutable
BEFORE UPDATE OR DELETE ON ship_class_construction_receipt
FOR EACH ROW EXECUTE FUNCTION ship_construction_receipts_immutable();
