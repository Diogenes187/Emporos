ALTER TABLE vehicle_class_fuel_tank
    ADD COLUMN published_cost_credits numeric CHECK (
        published_cost_credits>=0
    );

UPDATE vehicle_class_fuel_tank tank
SET published_cost_credits=source.cost_credits
FROM vehicle_class class
JOIN (
    VALUES
        ('air-raft',64.51::numeric),
        ('g-carrier',282.24),
        ('grav-bike',12.9024),
        ('grav-floater',6.96),
        ('grav-tank',564.48),
        ('speeder',32.256),
        ('afv-tracked',60.48),
        ('atv-tracked',60.48),
        ('ground-car',9.5865),
        ('van',59.76),
        ('tunnel-boring-machine',561.744),
        ('biplane',11.2),
        ('helicopter',74.7),
        ('twin-engine-jet',194.22),
        ('hovercraft',354.576),
        ('destroyer-watercraft',19840),
        ('motor-boat',1067.143),
        ('steamship',108000),
        ('submersible',63744)
) source(class_code,cost_credits)
  ON source.class_code=class.class_code
WHERE class.vehicle_class_rule_id=tank.vehicle_class_rule_id;

ALTER TABLE vehicle_class_fuel_tank
    ALTER COLUMN published_cost_credits SET NOT NULL;

CREATE TABLE vehicle_class_construction_receipt (
    construction_receipt_id bigint GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,
    vehicle_class_rule_id bigint NOT NULL REFERENCES
        vehicle_class(vehicle_class_rule_id),
    receipt_version smallint NOT NULL DEFAULT 1 CHECK (
        receipt_version>0
    ),
    supersedes_receipt_id bigint REFERENCES
        vehicle_class_construction_receipt(construction_receipt_id),
    standard_design_discount_rate numeric NOT NULL CHECK (
        standard_design_discount_rate BETWEEN 0 AND 1
    ),
    stated_subtotal_credits numeric NOT NULL CHECK (
        stated_subtotal_credits>=0
    ),
    receipt_status text NOT NULL CHECK (
        receipt_status IN (
            'published','source_conflict','source_gap'
        )
    ),
    finalized boolean NOT NULL DEFAULT false,
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    UNIQUE (vehicle_class_rule_id,receipt_version),
    UNIQUE (construction_receipt_id,vehicle_class_rule_id),
    CHECK (
        supersedes_receipt_id IS NULL OR receipt_version>1
    )
);

CREATE UNIQUE INDEX vehicle_construction_receipt_superseded_once
    ON vehicle_class_construction_receipt(supersedes_receipt_id)
    WHERE supersedes_receipt_id IS NOT NULL;

CREATE TABLE vehicle_class_construction_line (
    construction_line_id bigint GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,
    construction_receipt_id bigint NOT NULL,
    vehicle_class_rule_id bigint NOT NULL,
    line_order smallint NOT NULL CHECK (line_order>0),
    line_kind text NOT NULL CHECK (
        line_kind IN (
            'chassis','configuration','armor','power_plant',
            'propulsion','fuel','control','autopilot',
            'communication','sensor','computer',
            'computer_option','accommodation','life_support',
            'configuration_option','drive_option',
            'additional_component','weapon_mount','weapon',
            'gun_shield','cargo','other'
        )
    ),
    reference_code text NOT NULL CHECK (btrim(reference_code)<>''),
    quantity numeric NOT NULL DEFAULT 1 CHECK (quantity>0),
    space_role text NOT NULL CHECK (
        space_role IN ('capacity','allocation','remainder','none')
    ),
    published_spaces numeric NOT NULL DEFAULT 0 CHECK (
        published_spaces>=0
    ),
    published_cost_credits numeric NOT NULL,
    discount_eligible boolean NOT NULL DEFAULT true,
    line_status text NOT NULL DEFAULT 'published' CHECK (
        line_status IN (
            'published','published_override','reconstructed'
        )
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    UNIQUE (construction_receipt_id,line_order),
    FOREIGN KEY (construction_receipt_id,vehicle_class_rule_id)
        REFERENCES vehicle_class_construction_receipt(
            construction_receipt_id,vehicle_class_rule_id
        )
);

CREATE OR REPLACE FUNCTION vehicle_validate_construction_line()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    receipt_finalized boolean;
BEGIN
    SELECT finalized INTO receipt_finalized
    FROM vehicle_class_construction_receipt
    WHERE construction_receipt_id=NEW.construction_receipt_id
      AND vehicle_class_rule_id=NEW.vehicle_class_rule_id;
    IF receipt_finalized IS NULL OR receipt_finalized THEN
        RAISE EXCEPTION
            'Vehicle construction line requires an open matching receipt'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER vehicle_construction_line_open_receipt
BEFORE INSERT OR UPDATE OR DELETE ON vehicle_class_construction_line
FOR EACH ROW EXECUTE FUNCTION vehicle_validate_construction_line();

INSERT INTO vehicle_class_construction_receipt (
    vehicle_class_rule_id,standard_design_discount_rate,
    stated_subtotal_credits,receipt_status,source_locator_id
)
SELECT class.vehicle_class_rule_id,
       CASE WHEN class.standard_design THEN 0.10 ELSE 0 END,
       source.stated_subtotal,
       CASE
           WHEN source.class_code IN ('air-raft','g-carrier')
               THEN 'source_conflict'
           ELSE 'published'
       END,
       class.source_locator_id
FROM (
    VALUES
        ('air-raft',104614.5::numeric),
        ('g-carrier',3487282.24),
        ('grav-bike',45977.9024),
        ('grav-floater',33966.96),
        ('grav-tank',1632659.48),
        ('speeder',366957.256),
        ('afv-tracked',319760.48),
        ('atv-tracked',171560.48),
        ('ground-car',6982.0865),
        ('stagecoach',8972.5),
        ('van',7256.01),
        ('tunnel-boring-machine',314049.244),
        ('biplane',22963.71),
        ('helicopter',172055.95),
        ('twin-engine-jet',817894.22),
        ('hovercraft',160723.326)
) source(class_code,stated_subtotal)
JOIN vehicle_class class USING (class_code);

WITH core_source(
    class_code,configuration_cost,
    power_spaces,power_cost,propulsion_spaces,propulsion_cost,
    armor_spaces,armor_cost
) AS (
    VALUES
        ('air-raft',-625::numeric,1.25::numeric,1425::numeric,
         1.4::numeric,70000::numeric,NULL::numeric,NULL::numeric),
        ('g-carrier',0,5.25,23650,6,240000,9.6,13350),
        ('grav-bike',-185,0.15,300,0.23,30000,NULL,NULL),
        ('grav-floater',-240,0.26,300,0.12,6000,NULL,NULL),
        ('grav-tank',0,10.5,11825,12,600000,9.6,2670),
        ('speeder',0,1.25,1425,1.4,70000,NULL,NULL),
        ('afv-tracked',0,6.38,9575,11,21450,24,14200),
        ('atv-tracked',0,6.38,9575,11,21450,NULL,NULL),
        ('ground-car',0,2.4,22.5,0.55,550,NULL,NULL),
        ('stagecoach',-355,0,0,1,487.5,NULL,NULL),
        ('van',0,7.5,71.25,1.6,1575,NULL,NULL),
        ('tunnel-boring-machine',0,4.5,637.5,14,54600,NULL,NULL),
        ('biplane',-240,4.5,42.5,1.5,18750,NULL,NULL),
        ('helicopter',0,10.5,1481.25,12.5,156250,NULL,NULL),
        ('twin-engine-jet',0,13.5,1900,16,800000,NULL,NULL),
        ('hovercraft',0,9,1268.75,5.25,131250,NULL,NULL)
),
generated_line AS (
    SELECT class.vehicle_class_rule_id,10::smallint AS line_order,
           'chassis'::text AS line_kind,
           chassis.chassis_code AS reference_code,1::numeric AS quantity,
           'capacity'::text AS space_role,
           chassis.spaces::numeric AS published_spaces,
           chassis.base_price_minor::numeric AS published_cost,
           true AS discount_eligible,'published'::text AS line_status,
           class.source_locator_id
    FROM vehicle_class class
    JOIN core_source source USING (class_code)
    JOIN rule_vehicle_chassis chassis USING (chassis_code)

    UNION ALL

    SELECT class.vehicle_class_rule_id,20,'configuration',
           class.configuration,1,'none',0,
           source.configuration_cost,true,'published',
           class.source_locator_id
    FROM vehicle_class class
    JOIN core_source source USING (class_code)
    WHERE source.configuration_cost<>0

    UNION ALL

    SELECT class.vehicle_class_rule_id,30,'armor',
           class.armor_code,1,'allocation',
           source.armor_spaces,source.armor_cost,true,'published',
           class.source_locator_id
    FROM vehicle_class class
    JOIN core_source source USING (class_code)
    WHERE source.armor_spaces IS NOT NULL

    UNION ALL

    SELECT class.vehicle_class_rule_id,40,'power_plant',
           coalesce(plant.power_plant_code,'animal-powered'),1,
           CASE WHEN source.power_spaces=0 THEN 'none'
                ELSE 'allocation' END,
           source.power_spaces,source.power_cost,true,'published',
           class.source_locator_id
    FROM vehicle_class class
    JOIN core_source source USING (class_code)
    LEFT JOIN vehicle_class_power_plant plant
      USING (vehicle_class_rule_id)

    UNION ALL

    SELECT class.vehicle_class_rule_id,50,'propulsion',
           propulsion.propulsion_code,1,'allocation',
           source.propulsion_spaces,source.propulsion_cost,
           true,'published',class.source_locator_id
    FROM vehicle_class class
    JOIN core_source source USING (class_code)
    JOIN vehicle_class_propulsion propulsion
      USING (vehicle_class_rule_id)

    UNION ALL

    SELECT class.vehicle_class_rule_id,60,'fuel',
           tank.fuel_kind,1,'allocation',
           tank.capacity_kilolitres,tank.published_cost_credits,
           true,'published',tank.source_locator_id
    FROM vehicle_class class
    JOIN core_source source USING (class_code)
    JOIN vehicle_class_fuel_tank tank
      USING (vehicle_class_rule_id)

    UNION ALL

    SELECT class.vehicle_class_rule_id,
           (100+selection.display_order)::smallint,
           CASE component.component_kind
               WHEN 'controls' THEN 'control'
               WHEN 'communications' THEN 'communication'
               WHEN 'sensors' THEN 'sensor'
               WHEN 'computer' THEN 'computer'
               WHEN 'crew_space' THEN 'accommodation'
               WHEN 'passenger_space' THEN
                   CASE
                       WHEN component.component_code LIKE
                            'accommodation.%'
                           THEN 'accommodation'
                       ELSE 'additional_component'
                   END
               WHEN 'environmental_protection' THEN
                   CASE
                       WHEN component.component_code LIKE
                            'life-support.%'
                           THEN 'life_support'
                       ELSE 'additional_component'
                   END
               ELSE 'additional_component'
           END,
           component.component_code,selection.quantity,
           CASE WHEN selection.allocated_spaces=0
                THEN 'none' ELSE 'allocation' END,
           selection.allocated_spaces,
           selection.published_cost_minor::numeric,true,
           CASE selection.calculation_status
               WHEN 'published_override' THEN 'published_override'
               ELSE 'published'
           END,
           selection.source_locator_id
    FROM vehicle_class class
    JOIN core_source source USING (class_code)
    JOIN vehicle_class_component selection
      USING (vehicle_class_rule_id)
    JOIN vehicle_component_definition component
      USING (component_rule_id)

    UNION ALL

    SELECT class.vehicle_class_rule_id,
           (200+row_number() OVER (
               PARTITION BY class.vehicle_class_rule_id
               ORDER BY option.option_code
           ))::smallint,
           'configuration_option',option.option_code,1,
           CASE WHEN selection.allocated_spaces=0
                THEN 'none' ELSE 'allocation' END,
           selection.allocated_spaces,
           selection.published_cost_minor::numeric,true,
           'published',selection.source_locator_id
    FROM vehicle_class class
    JOIN core_source source USING (class_code)
    JOIN vehicle_class_configuration_option selection
      USING (vehicle_class_rule_id)
    JOIN rule_vehicle_configuration_option option
      USING (option_rule_id)

    UNION ALL

    SELECT class.vehicle_class_rule_id,
           (220+row_number() OVER (
               PARTITION BY class.vehicle_class_rule_id
               ORDER BY option.option_code
           ))::smallint,
           'drive_option',option.option_code,selection.option_steps,
           'none',0,selection.published_cost_minor::numeric,
           true,'published',selection.source_locator_id
    FROM vehicle_class class
    JOIN core_source source USING (class_code)
    JOIN vehicle_class_drive_option selection
      USING (vehicle_class_rule_id)
    JOIN rule_vehicle_drive_option option USING (option_rule_id)

    UNION ALL

    SELECT class.vehicle_class_rule_id,240,'autopilot',
           rule.rule_code,1,'none',0,
           autopilot.published_cost_minor::numeric,true,
           CASE autopilot.calculation_status
               WHEN 'published_override' THEN 'published_override'
               ELSE 'published'
           END,
           autopilot.source_locator_id
    FROM vehicle_class class
    JOIN core_source source USING (class_code)
    JOIN vehicle_class_autopilot autopilot
      USING (vehicle_class_rule_id)
    JOIN rule_rule rule ON rule.rule_id=autopilot.skill_rule_id

    UNION ALL

    SELECT class.vehicle_class_rule_id,250,'computer_option',
           option.option_code,1,'none',0,
           option.published_incremental_cost_minor::numeric,
           true,'published',option.source_locator_id
    FROM vehicle_class class
    JOIN core_source source USING (class_code)
    JOIN vehicle_class_computer_option option
      USING (vehicle_class_rule_id)

    UNION ALL

    SELECT class.vehicle_class_rule_id,
           (260+row_number() OVER (
               PARTITION BY class.vehicle_class_rule_id
               ORDER BY alternative.communicator_type_code
           ))::smallint,
           'communication',
           alternative.communicator_type_code||':'||
               component.component_code,
           1,'allocation',alternative.allocated_spaces,
           alternative.published_cost_minor::numeric,
           true,'published',alternative.source_locator_id
    FROM vehicle_class class
    JOIN core_source source USING (class_code)
    JOIN vehicle_class_alternative_communication alternative
      USING (vehicle_class_rule_id)
    JOIN vehicle_component_definition component
      ON component.component_rule_id=
         alternative.communication_component_rule_id

    UNION ALL

    SELECT class.vehicle_class_rule_id,
           (300+mount.mount_sequence)::smallint,
           'weapon_mount','mount-'||mount.mount_sequence::text,
           mount.quantity,'allocation',
           mount.published_mount_spaces_each*mount.quantity,
           mount.published_mount_cost_each_minor*mount.quantity,
           true,'published',mount.source_locator_id
    FROM vehicle_class class
    JOIN core_source source USING (class_code)
    JOIN vehicle_class_armament_mount mount
      USING (vehicle_class_rule_id)

    UNION ALL

    SELECT class.vehicle_class_rule_id,
           (320+mount.mount_sequence*5+weapon.slot_order)::smallint,
           'weapon',definition.weapon_code,
           mount.quantity*weapon.quantity_per_mount,'allocation',
           mount.quantity*weapon.quantity_per_mount*
               weapon.published_weapon_spaces_each,
           mount.quantity*weapon.quantity_per_mount*
               weapon.published_weapon_cost_each_minor,
           true,'published',weapon.source_locator_id
    FROM vehicle_class class
    JOIN core_source source USING (class_code)
    JOIN vehicle_class_armament_mount mount
      USING (vehicle_class_rule_id)
    JOIN vehicle_class_armament_weapon weapon
      USING (class_armament_mount_id)
    JOIN rule_vehicle_weapon_definition definition
      ON definition.weapon_rule_id=weapon.weapon_rule_id

    UNION ALL

    SELECT class.vehicle_class_rule_id,
           (350+mount.mount_sequence)::smallint,
           'gun_shield','gun-shield',mount.quantity,'none',0,
           shield.published_cost_minor*mount.quantity,
           true,'published',shield.source_locator_id
    FROM vehicle_class class
    JOIN core_source source USING (class_code)
    JOIN vehicle_class_armament_mount mount
      USING (vehicle_class_rule_id)
    JOIN vehicle_class_armament_gun_shield shield
      USING (class_armament_mount_id)

    UNION ALL

    SELECT class.vehicle_class_rule_id,900,'cargo','cargo',1,
           'remainder',class.cargo_spaces,0,true,'published',
           class.source_locator_id
    FROM vehicle_class class
    JOIN core_source source USING (class_code)
)
INSERT INTO vehicle_class_construction_line (
    construction_receipt_id,vehicle_class_rule_id,
    line_order,line_kind,reference_code,quantity,
    space_role,published_spaces,published_cost_credits,
    discount_eligible,line_status,source_locator_id
)
SELECT receipt.construction_receipt_id,
       line.vehicle_class_rule_id,line.line_order,
       line.line_kind,line.reference_code,line.quantity,
       line.space_role,line.published_spaces,line.published_cost,
       line.discount_eligible,line.line_status,line.source_locator_id
FROM generated_line line
JOIN vehicle_class_construction_receipt receipt
  USING (vehicle_class_rule_id);

UPDATE vehicle_class_construction_receipt
SET finalized=true;

CREATE VIEW vehicle_class_construction_receipt_total AS
WITH line_total AS (
    SELECT receipt.construction_receipt_id,
           receipt.vehicle_class_rule_id,
           receipt.receipt_version,receipt.receipt_status,
           receipt.standard_design_discount_rate,
           receipt.stated_subtotal_credits,
           max(line.published_spaces) FILTER (
               WHERE line.space_role='capacity'
           ) AS capacity_spaces,
           coalesce(sum(line.published_spaces) FILTER (
               WHERE line.space_role='allocation'
           ),0) AS allocated_spaces,
           coalesce(sum(line.published_spaces) FILTER (
               WHERE line.space_role='remainder'
           ),0) AS remainder_spaces,
           coalesce(sum(line.published_cost_credits) FILTER (
               WHERE line.discount_eligible
           ),0) AS discountable_cost_credits,
           coalesce(sum(line.published_cost_credits) FILTER (
               WHERE NOT line.discount_eligible
           ),0) AS excluded_cost_credits
    FROM vehicle_class_construction_receipt receipt
    LEFT JOIN vehicle_class_construction_line line USING (
        construction_receipt_id,vehicle_class_rule_id
    )
    GROUP BY receipt.construction_receipt_id
)
SELECT total.*,
       total.capacity_spaces-total.allocated_spaces-
           total.remainder_spaces AS space_variance,
       total.stated_subtotal_credits-
           total.discountable_cost_credits-
           total.excluded_cost_credits AS stated_subtotal_variance,
       round(
           total.stated_subtotal_credits*
           (1-total.standard_design_discount_rate),
           -1
       ) AS stated_discounted_cost_credits,
       class.construction_cost_minor AS published_cost_credits,
       class.construction_cost_minor-round(
           total.stated_subtotal_credits*
           (1-total.standard_design_discount_rate),
           -1
       ) AS published_cost_variance,
       CASE
           WHEN total.receipt_status='source_gap' THEN 'source_gap'
           WHEN total.capacity_spaces<>total.allocated_spaces+
                total.remainder_spaces THEN 'space_conflict'
           WHEN abs(
               total.stated_subtotal_credits-
               total.discountable_cost_credits-
               total.excluded_cost_credits
           )>0.01 THEN 'subtotal_conflict'
           WHEN class.construction_cost_minor<>round(
               total.stated_subtotal_credits*
               (1-total.standard_design_discount_rate),
               -1
           ) THEN 'published_cost_conflict'
           ELSE 'published_reconciled'
       END AS reconciliation_status
FROM line_total total
JOIN vehicle_class class USING (vehicle_class_rule_id);

CREATE VIEW vehicle_class_construction_total AS
SELECT total.*
FROM vehicle_class_construction_receipt_total total
JOIN vehicle_class_construction_receipt receipt USING (
    construction_receipt_id,vehicle_class_rule_id,receipt_version
)
WHERE NOT EXISTS (
    SELECT 1
    FROM vehicle_class_construction_receipt newer
    WHERE newer.vehicle_class_rule_id=receipt.vehicle_class_rule_id
      AND newer.receipt_version>receipt.receipt_version
);

CREATE OR REPLACE FUNCTION vehicle_construction_receipts_immutable()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP='UPDATE'
       AND NOT OLD.finalized
       AND NEW.finalized
       AND NEW.construction_receipt_id=OLD.construction_receipt_id
       AND NEW.vehicle_class_rule_id=OLD.vehicle_class_rule_id
       AND NEW.receipt_version=OLD.receipt_version
       AND NEW.supersedes_receipt_id IS NOT DISTINCT FROM
           OLD.supersedes_receipt_id
       AND NEW.standard_design_discount_rate=
           OLD.standard_design_discount_rate
       AND NEW.stated_subtotal_credits=
           OLD.stated_subtotal_credits
       AND NEW.receipt_status=OLD.receipt_status
       AND NEW.source_locator_id=OLD.source_locator_id THEN
        RETURN NEW;
    END IF;
    RAISE EXCEPTION 'Vehicle construction receipts are immutable'
        USING ERRCODE='23514';
END;
$$;

CREATE TRIGGER vehicle_construction_receipt_immutable
BEFORE UPDATE OR DELETE ON vehicle_class_construction_receipt
FOR EACH ROW EXECUTE FUNCTION
    vehicle_construction_receipts_immutable();
