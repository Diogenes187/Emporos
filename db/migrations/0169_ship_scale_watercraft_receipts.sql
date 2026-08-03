ALTER TABLE vehicle_class_construction_receipt
    DROP CONSTRAINT
        vehicle_class_construction_receip_stated_subtotal_credits_check,
    ALTER COLUMN stated_subtotal_credits DROP NOT NULL,
    ADD CONSTRAINT vehicle_receipt_stated_subtotal_status_check CHECK (
        (
            receipt_status='source_gap'
            AND stated_subtotal_credits IS NULL
        )
        OR (
            receipt_status<>'source_gap'
            AND stated_subtotal_credits>=0
        )
    );

ALTER TABLE vehicle_class_construction_line
    DROP CONSTRAINT
        vehicle_class_construction_line_line_kind_check,
    ADD CONSTRAINT vehicle_class_construction_line_line_kind_check
        CHECK (
            line_kind IN (
                'chassis','configuration','armor','power_plant',
                'propulsion','fuel','control','autopilot',
                'communication','sensor','computer',
                'computer_option','accommodation','life_support',
                'configuration_option','drive_option',
                'additional_component','weapon_mount','weapon',
                'gun_shield','ammunition','missile','ordnance',
                'cargo','other'
            )
        );

INSERT INTO vehicle_class_construction_receipt (
    vehicle_class_rule_id,standard_design_discount_rate,
    stated_subtotal_credits,receipt_status,source_locator_id
)
SELECT class.vehicle_class_rule_id,0.10,
       source.stated_subtotal,source.receipt_status,
       class.source_locator_id
FROM (
    VALUES
        ('destroyer-watercraft',NULL::numeric,'source_gap'),
        ('motor-boat',2998267.143::numeric,'published'),
        ('steamship',6366700::numeric,'published'),
        ('submersible',34660744::numeric,'published')
) source(class_code,stated_subtotal,receipt_status)
JOIN vehicle_class class USING (class_code);

WITH watercraft AS (
    SELECT *
    FROM vehicle_class
    WHERE class_code IN (
        'destroyer-watercraft','motor-boat',
        'steamship','submersible'
    )
),
generated_line AS (
    SELECT class.vehicle_class_rule_id,10::smallint AS line_order,
           'chassis'::text AS line_kind,
           hull.ship_hull_code AS reference_code,
           1::numeric AS quantity,'capacity'::text AS space_role,
           hull.published_base_spaces AS published_spaces,
           hull.published_base_cost_minor::numeric AS published_cost,
           true AS discount_eligible,
           CASE hull.calculation_status
               WHEN 'matches' THEN 'published'
               ELSE 'published_override'
           END AS line_status,
           hull.source_locator_id
    FROM watercraft class
    JOIN vehicle_class_ship_scale_hull hull
      USING (vehicle_class_rule_id)

    UNION ALL

    SELECT class.vehicle_class_rule_id,30,'armor',
           class.armor_code,1,'allocation',960,4000000,
           true,'published',class.source_locator_id
    FROM watercraft class
    WHERE class.class_code='destroyer-watercraft'

    UNION ALL

    SELECT class.vehicle_class_rule_id,40,'power_plant',
           plant.power_plant_code,1,'allocation',
           plant.published_spaces,plant.published_cost_minor,
           true,
           CASE plant.calculation_status
               WHEN 'matches' THEN 'published'
               ELSE 'published_override'
           END,
           plant.source_locator_id
    FROM watercraft class
    JOIN vehicle_class_ship_scale_power_plant plant
      USING (vehicle_class_rule_id)

    UNION ALL

    SELECT class.vehicle_class_rule_id,50,'propulsion',
           propulsion.propulsion_code,1,'allocation',
           propulsion.published_spaces,
           propulsion.published_cost_minor,true,
           CASE propulsion.calculation_status
               WHEN 'matches' THEN 'published'
               ELSE 'published_override'
           END,
           propulsion.source_locator_id
    FROM watercraft class
    JOIN vehicle_class_ship_scale_propulsion propulsion
      USING (vehicle_class_rule_id)

    UNION ALL

    SELECT class.vehicle_class_rule_id,60,'fuel',
           tank.fuel_kind,1,'allocation',
           tank.capacity_kilolitres,tank.published_cost_credits,
           true,'published',tank.source_locator_id
    FROM watercraft class
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
    FROM watercraft class
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
           CASE
               WHEN class.class_code='submersible'
                    AND option.option_code=
                        'hostile-environmental-protection'
                   THEN 'published_override'
               ELSE 'published'
           END,
           selection.source_locator_id
    FROM watercraft class
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
    FROM watercraft class
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
    FROM watercraft class
    JOIN vehicle_class_autopilot autopilot
      USING (vehicle_class_rule_id)
    JOIN rule_rule rule ON rule.rule_id=autopilot.skill_rule_id

    UNION ALL

    SELECT class.vehicle_class_rule_id,250,'computer_option',
           option.option_code,1,'none',0,
           option.published_incremental_cost_minor::numeric,
           true,'published',option.source_locator_id
    FROM watercraft class
    JOIN vehicle_class_computer_option option
      USING (vehicle_class_rule_id)

    UNION ALL

    SELECT class.vehicle_class_rule_id,
           (300+mount.mount_sequence)::smallint,
           'weapon_mount','mount-'||mount.mount_sequence::text,
           mount.quantity,'allocation',
           mount.published_mount_spaces_each*mount.quantity,
           mount.published_mount_cost_each_minor*mount.quantity,
           true,'reconstructed',mount.source_locator_id
    FROM watercraft class
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
           true,'reconstructed',weapon.source_locator_id
    FROM watercraft class
    JOIN vehicle_class_armament_mount mount
      USING (vehicle_class_rule_id)
    JOIN vehicle_class_armament_weapon weapon
      USING (class_armament_mount_id)
    JOIN rule_vehicle_weapon_definition definition
      ON definition.weapon_rule_id=weapon.weapon_rule_id

    UNION ALL

    SELECT class.vehicle_class_rule_id,
           (400+row_number() OVER (
               PARTITION BY class.vehicle_class_rule_id
               ORDER BY load.weapon_family_code
           ))::smallint,
           'ammunition',load.weapon_family_code,
           load.round_count,'allocation',load.allocated_spaces,
           load.published_cost_minor,true,'reconstructed',
           load.source_locator_id
    FROM watercraft class
    JOIN vehicle_class_weapon_ammunition_load load
      USING (vehicle_class_rule_id)

    UNION ALL

    SELECT class.vehicle_class_rule_id,450,'missile',
           definition.missile_code,load.missile_count,
           'allocation',load.allocated_spaces,
           load.published_cost_minor,true,'reconstructed',
           load.source_locator_id
    FROM watercraft class
    JOIN vehicle_class_missile_load load
      USING (vehicle_class_rule_id)
    JOIN rule_vehicle_missile definition
      USING (missile_rule_id)

    UNION ALL

    SELECT class.vehicle_class_rule_id,460,'ordnance',
           definition.ordnance_code,load.ordnance_count,
           'allocation',load.allocated_spaces,
           load.published_cost_minor,true,'reconstructed',
           load.source_locator_id
    FROM watercraft class
    JOIN vehicle_class_ordnance_load load
      USING (vehicle_class_rule_id)
    JOIN rule_vehicle_ordnance_definition definition
      USING (ordnance_rule_id)

    UNION ALL

    SELECT class.vehicle_class_rule_id,900,'cargo','cargo',1,
           'remainder',class.cargo_spaces,0,true,
           CASE
               WHEN class.class_code='destroyer-watercraft'
                   THEN 'reconstructed'
               ELSE 'published'
           END,
           class.source_locator_id
    FROM watercraft class
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
       AND NEW.stated_subtotal_credits IS NOT DISTINCT FROM
           OLD.stated_subtotal_credits
       AND NEW.receipt_status=OLD.receipt_status
       AND NEW.source_locator_id=OLD.source_locator_id THEN
        RETURN NEW;
    END IF;
    RAISE EXCEPTION 'Vehicle construction receipts are immutable'
        USING ERRCODE='23514';
END;
$$;

UPDATE vehicle_class_construction_receipt
SET finalized=true
WHERE vehicle_class_rule_id IN (
    SELECT vehicle_class_rule_id
    FROM vehicle_class
    WHERE class_code IN (
        'destroyer-watercraft','motor-boat',
        'steamship','submersible'
    )
);
