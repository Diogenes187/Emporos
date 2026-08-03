INSERT INTO src_locator (
    source_work_id,source_artifact_id,locator_type,
    heading_path,display_citation
)
SELECT artifact.source_work_id,artifact.source_artifact_id,
       'heading',source.heading_path,source.display_citation
FROM src_artifact artifact
JOIN (
    VALUES
        ('src/vds/common-grav-vehicles.md',
         'Common Grav Vehicles > TL9 Air/Raft',
         'Cepheus Engine VDS, Common Grav Vehicles: TL9 Air/Raft'),
        ('src/vds/common-grav-vehicles.md',
         'Common Grav Vehicles > TL15 G/Carrier',
         'Cepheus Engine VDS, Common Grav Vehicles: TL15 G/Carrier'),
        ('src/vds/common-grav-vehicles.md',
         'Common Grav Vehicles > TL12 Grav Bike',
         'Cepheus Engine VDS, Common Grav Vehicles: TL12 Grav Bike'),
        ('src/vds/common-grav-vehicles.md',
         'Common Grav Vehicles > TL11 Grav Floater',
         'Cepheus Engine VDS, Common Grav Vehicles: TL11 Grav Floater'),
        ('src/vds/common-grav-vehicles.md',
         'Common Grav Vehicles > TL9 Grav Tank',
         'Cepheus Engine VDS, Common Grav Vehicles: TL9 Grav Tank'),
        ('src/vds/common-grav-vehicles.md',
         'Common Grav Vehicles > TL9 Speeder',
         'Cepheus Engine VDS, Common Grav Vehicles: TL9 Speeder'),
        ('src/vds/common-ground-vehicles.md',
         'Common Ground Vehicles > TL12 AFV, Tracked',
         'Cepheus Engine VDS, Common Ground Vehicles: TL12 AFV, Tracked'),
        ('src/vds/common-ground-vehicles.md',
         'Common Ground Vehicles > TL12 ATV, Tracked',
         'Cepheus Engine VDS, Common Ground Vehicles: TL12 ATV, Tracked'),
        ('src/vds/common-ground-vehicles.md',
         'Common Ground Vehicles > TL5 Ground Car',
         'Cepheus Engine VDS, Common Ground Vehicles: TL5 Ground Car'),
        ('src/vds/common-ground-vehicles.md',
         'Common Ground Vehicles > TL3 Stagecoach',
         'Cepheus Engine VDS, Common Ground Vehicles: TL3 Stagecoach'),
        ('src/vds/common-ground-vehicles.md',
         'Common Ground Vehicles > TL5 Van',
         'Cepheus Engine VDS, Common Ground Vehicles: TL5 Van'),
        ('src/vds/uncommon-vehicles.md',
         'Uncommon Vehicles > TL8 Tunnel Boring Machine',
         'Cepheus Engine VDS, Uncommon Vehicles: TL8 Tunnel Boring Machine')
) source(source_uri,heading_path,display_citation)
  ON source.source_uri=artifact.source_uri
ON CONFLICT DO NOTHING;

UPDATE vehicle_class class
SET source_locator_id=locator.source_locator_id
FROM src_locator locator
WHERE locator.heading_path=CASE class.class_code
    WHEN 'air-raft' THEN 'Common Grav Vehicles > TL9 Air/Raft'
    WHEN 'g-carrier' THEN 'Common Grav Vehicles > TL15 G/Carrier'
    WHEN 'grav-bike' THEN 'Common Grav Vehicles > TL12 Grav Bike'
    WHEN 'grav-floater' THEN 'Common Grav Vehicles > TL11 Grav Floater'
    WHEN 'grav-tank' THEN 'Common Grav Vehicles > TL9 Grav Tank'
    WHEN 'speeder' THEN 'Common Grav Vehicles > TL9 Speeder'
    WHEN 'afv-tracked' THEN
        'Common Ground Vehicles > TL12 AFV, Tracked'
    WHEN 'atv-tracked' THEN
        'Common Ground Vehicles > TL12 ATV, Tracked'
    WHEN 'ground-car' THEN 'Common Ground Vehicles > TL5 Ground Car'
    WHEN 'stagecoach' THEN 'Common Ground Vehicles > TL3 Stagecoach'
    WHEN 'van' THEN 'Common Ground Vehicles > TL5 Van'
    WHEN 'tunnel-boring-machine' THEN
        'Uncommon Vehicles > TL8 Tunnel Boring Machine'
END
AND class.class_code IN (
    'air-raft','g-carrier','grav-bike','grav-floater',
    'grav-tank','speeder','afv-tracked','atv-tracked',
    'ground-car','stagecoach','van','tunnel-boring-machine'
);

UPDATE src_record_provenance provenance
SET source_locator_id=class.source_locator_id
FROM vehicle_class class
WHERE class.vehicle_class_rule_id=provenance.rule_id
  AND class.class_code IN (
      'air-raft','g-carrier','grav-bike','grav-floater',
      'grav-tank','speeder','afv-tracked','atv-tracked',
      'ground-car','stagecoach','van','tunnel-boring-machine'
  );

ALTER TABLE vehicle_class_component
    DROP CONSTRAINT vehicle_class_component_published_cost_minor_check;

CREATE OR REPLACE FUNCTION vehicle_validate_component_allocation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    class_tech smallint;
    class_chassis text;
    chassis_price bigint;
    design_capacity numeric;
    already_allocated numeric;
    component_tech smallint;
    unit_spaces numeric;
    unit_cost bigint;
    formula rule_vehicle_component_formula%ROWTYPE;
    control_formula rule_vehicle_control_system%ROWTYPE;
    increments numeric;
    expected_spaces numeric;
    expected_cost numeric;
BEGIN
    SELECT class.minimum_tech_level,class.chassis_code,
           chassis.base_price_minor,class.allocated_spaces
    INTO class_tech,class_chassis,chassis_price,design_capacity
    FROM vehicle_class class
    JOIN rule_vehicle_chassis chassis USING (chassis_code)
    WHERE class.vehicle_class_rule_id=NEW.vehicle_class_rule_id
    FOR UPDATE OF class;
    SELECT definition.minimum_tech_level,
           definition.unit_spaces,definition.unit_cost_minor
    INTO component_tech,unit_spaces,unit_cost
    FROM vehicle_component_definition definition
    WHERE definition.component_rule_id=NEW.component_rule_id;
    SELECT coalesce(sum(allocated_spaces),0)
    INTO already_allocated
    FROM vehicle_class_component
    WHERE vehicle_class_rule_id=NEW.vehicle_class_rule_id
      AND vehicle_class_component_id<>
          coalesce(NEW.vehicle_class_component_id,0);
    IF already_allocated+NEW.allocated_spaces>design_capacity
       OR (
           component_tech IS NOT NULL
           AND class_tech<component_tech
           AND NEW.tech_level_status='matches'
       )
       OR (
           component_tech IS NOT NULL
           AND class_tech>=component_tech
           AND NEW.tech_level_status='published_override'
       ) THEN
        RAISE EXCEPTION
            'Vehicle component exceeds class capacity or tech level'
            USING ERRCODE='23514';
    END IF;
    IF NEW.calculation_status='matches'
       AND (
           NEW.allocated_spaces<>unit_spaces*NEW.quantity
           OR NEW.published_cost_minor<>unit_cost*NEW.quantity
       ) THEN
        RAISE EXCEPTION
            'Vehicle component does not match fixed catalogue values'
            USING ERRCODE='23514';
    ELSIF NEW.calculation_status='formula' THEN
        SELECT * INTO formula
        FROM rule_vehicle_component_formula
        WHERE component_rule_id=NEW.component_rule_id;
        IF FOUND THEN
            IF NEW.rating IS NULL THEN
                RAISE EXCEPTION
                    'Vehicle formula component requires a rating'
                    USING ERRCODE='23514';
            END IF;
            increments=CASE formula.increment_rounding
                WHEN 'ceiling' THEN ceil(
                    NEW.rating/formula.basis_units_per_increment
                )
                WHEN 'floor' THEN floor(
                    NEW.rating/formula.basis_units_per_increment
                )
                ELSE NEW.rating/formula.basis_units_per_increment
            END;
            expected_spaces=(
                formula.base_spaces+
                formula.spaces_per_increment*increments
            )*NEW.quantity;
            expected_cost=(
                formula.base_cost_minor+
                formula.cost_per_basis_unit_minor*NEW.rating+
                formula.cost_per_allocated_space_minor*expected_spaces+
                formula.cost_per_increment_minor*increments
            )*NEW.quantity;
        ELSE
            SELECT * INTO control_formula
            FROM rule_vehicle_control_system
            WHERE component_rule_id=NEW.component_rule_id
              AND price_basis='chassis_percent_adjustment';
            IF NOT FOUND THEN
                RAISE EXCEPTION
                    'Vehicle component lacks a supported formula'
                    USING ERRCODE='23514';
            END IF;
            expected_spaces=unit_spaces*NEW.quantity;
            expected_cost=(
                chassis_price*
                control_formula.chassis_price_adjustment_percent/100
            )*NEW.quantity;
        END IF;
        IF NEW.allocated_spaces<>expected_spaces
           OR NEW.published_cost_minor<>expected_cost THEN
            RAISE EXCEPTION
                'Vehicle formula component calculation is inconsistent'
                USING ERRCODE='23514';
        END IF;
    ELSIF NEW.calculation_status='published_override'
          AND NEW.allocated_spaces=unit_spaces*NEW.quantity
          AND NEW.published_cost_minor=unit_cost*NEW.quantity THEN
        RAISE EXCEPTION
            'Published override must differ from fixed catalogue values'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

ALTER TABLE vehicle_class_autopilot
    ADD COLUMN calculation_status text NOT NULL DEFAULT 'matches'
        CHECK (
            calculation_status IN ('matches','published_override')
        );

CREATE OR REPLACE FUNCTION vehicle_validate_class_autopilot()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    class_tech smallint;
    introduction_tech smallint;
    formula rule_vehicle_autopilot_formula%ROWTYPE;
    expected_level smallint;
    expected_cost bigint;
    is_match boolean;
BEGIN
    SELECT minimum_tech_level INTO class_tech
    FROM vehicle_class
    WHERE vehicle_class_rule_id=NEW.vehicle_class_rule_id;
    SELECT minimum_tech_level INTO introduction_tech
    FROM rule_vehicle_autopilot_introduction introduction
    WHERE introduction.vehicle_category=NEW.vehicle_category;
    SELECT definition.* INTO formula
    FROM rule_vehicle_autopilot_introduction introduction
    JOIN rule_vehicle_autopilot_formula definition
      USING (formula_code)
    WHERE introduction.vehicle_category=NEW.vehicle_category;
    expected_level=least(
        formula.maximum_skill_level,
        formula.base_skill_level+
        floor(
            (class_tech-introduction_tech)/
            formula.tech_levels_per_skill_level
        )
    );
    expected_cost=formula.base_price_minor+
        formula.price_per_skill_level_minor*expected_level;
    is_match=class_tech>=introduction_tech
             AND NEW.skill_level=expected_level
             AND NEW.published_cost_minor=expected_cost;
    IF (
        NEW.calculation_status='matches' AND NOT is_match
    ) OR (
        NEW.calculation_status='published_override' AND is_match
    ) THEN
        RAISE EXCEPTION
            'Vehicle autopilot conflicts with calculation status'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TABLE vehicle_class_alternative_communication (
    vehicle_class_rule_id bigint NOT NULL REFERENCES
        vehicle_class(vehicle_class_rule_id),
    communication_component_rule_id bigint NOT NULL REFERENCES
        rule_vehicle_communication_system(component_rule_id),
    communicator_type_code text NOT NULL REFERENCES
        rule_vehicle_communicator_type(communicator_type_code),
    allocated_spaces numeric NOT NULL CHECK (allocated_spaces>0),
    published_cost_minor bigint NOT NULL CHECK (
        published_cost_minor>0
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    PRIMARY KEY (
        vehicle_class_rule_id,communication_component_rule_id,
        communicator_type_code
    )
);

CREATE OR REPLACE FUNCTION
vehicle_validate_class_alternative_communication()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    class_tech smallint;
    type_tech smallint;
    base_spaces numeric;
    base_cost bigint;
    space_multiplier numeric;
    price_multiplier numeric;
BEGIN
    SELECT minimum_tech_level INTO class_tech
    FROM vehicle_class
    WHERE vehicle_class_rule_id=NEW.vehicle_class_rule_id;
    SELECT definition.unit_spaces,definition.unit_cost_minor,
           type.minimum_tech_level,type.space_multiplier,
           type.price_multiplier
    INTO base_spaces,base_cost,type_tech,
         space_multiplier,price_multiplier
    FROM vehicle_component_definition definition
    CROSS JOIN rule_vehicle_communicator_type type
    WHERE definition.component_rule_id=
          NEW.communication_component_rule_id
      AND type.communicator_type_code=
          NEW.communicator_type_code;
    IF class_tech<type_tech
       OR NEW.allocated_spaces<>base_spaces*space_multiplier
       OR NEW.published_cost_minor<>base_cost*price_multiplier THEN
        RAISE EXCEPTION
            'Alternative communication selection is inconsistent'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER vehicle_class_alternative_communication_valid
BEFORE INSERT OR UPDATE ON vehicle_class_alternative_communication
FOR EACH ROW EXECUTE FUNCTION
    vehicle_validate_class_alternative_communication();

WITH source(
    class_code,component_code,quantity,rating,allocated_spaces,
    published_cost,calculation_status,display_order
) AS (
    VALUES
        ('air-raft','control.advanced',1::smallint,NULL::numeric,
         2::numeric,10000::bigint,'matches',1::smallint),
        ('air-raft','communication.class-3',1,NULL,0.05,2000,
         'matches',2),
        ('air-raft','sensor.basic-civilian',1,NULL,6,10000,
         'matches',3),
        ('air-raft','computer.model-1',1,NULL,0.01,500,
         'matches',4),
        ('air-raft','accommodation.cockpit-basic',1,NULL,2,1000,
         'matches',5),
        ('air-raft','accommodation.seat-cramped',1,NULL,4,2000,
         'matches',6),
        ('g-carrier','control.advanced',1,NULL,2,10000,'matches',1),
        ('g-carrier','communication.class-4',1,NULL,0.10,4000,
         'matches',2),
        ('g-carrier','sensor.basic-military',1,NULL,12,20000,
         'matches',3),
        ('g-carrier','computer.model-5',1,NULL,0,10000,
         'matches',4),
        ('g-carrier','accommodation.cockpit-extended',1,NULL,
         4,2000,'matches',5),
        ('g-carrier','accommodation.seat-cramped',4,NULL,
         16,8000,'matches',6),
        ('g-carrier','life-support.basic',1,NULL,3,3500,
         'published_override',7),
        ('grav-bike','control.basic',1,NULL,1,0,'matches',1),
        ('grav-bike','communication.class-4',1,NULL,0.10,4000,
         'matches',2),
        ('grav-bike','computer.model-3',1,NULL,0,2000,
         'matches',3),
        ('grav-bike','accommodation.cockpit-basic',1,NULL,
         2,1000,'matches',4),
        ('grav-floater','control.advanced',1,NULL,2,10000,
         'matches',1),
        ('grav-floater','communication.class-3',1,NULL,0.05,2000,
         'matches',2),
        ('grav-floater','sensor.standard',1,NULL,3,5000,
         'matches',3),
        ('grav-floater','computer.model-1',1,NULL,0.01,500,
         'matches',4),
        ('grav-floater','accommodation.cockpit-basic',1,NULL,
         2,1000,'matches',5),
        ('grav-tank','control.advanced',1,NULL,2,10000,'matches',1),
        ('grav-tank','communication.class-4',1,NULL,0.10,4000,
         'matches',2),
        ('grav-tank','sensor.basic-civilian',1,NULL,6,10000,
         'matches',3),
        ('grav-tank','computer.model-1',1,NULL,0.01,500,
         'matches',4),
        ('grav-tank','accommodation.cockpit-extended',1,NULL,
         4,2000,'matches',5),
        ('grav-tank','accommodation.seat-cramped',4,NULL,
         16,8000,'matches',6),
        ('grav-tank','life-support.basic',1,NULL,3,3500,
         'published_override',7),
        ('speeder','control.advanced',1,NULL,2,10000,'matches',1),
        ('speeder','communication.class-4',1,NULL,0.10,4000,
         'matches',2),
        ('speeder','sensor.basic-civilian',1,NULL,6,10000,
         'matches',3),
        ('speeder','computer.model-1',1,NULL,0.01,500,
         'matches',4),
        ('speeder','accommodation.cockpit-extended',1,NULL,
         4,2000,'matches',5),
        ('speeder','life-support.basic',1,NULL,3,3500,
         'published_override',6),
        ('speeder','additional.entertainment-system',1,NULL,
         0,200,'matches',7),
        ('afv-tracked','control.advanced',1,NULL,2,10000,'matches',1),
        ('afv-tracked','communication.class-4',1,NULL,0.10,4000,
         'matches',2),
        ('afv-tracked','sensor.basic-military',1,NULL,12,20000,
         'matches',3),
        ('afv-tracked','computer.model-3',1,NULL,0,2000,
         'matches',4),
        ('afv-tracked','accommodation.cockpit-extended',1,NULL,
         4,2000,'matches',5),
        ('afv-tracked','accommodation.seat-cramped',2,NULL,
         8,4000,'matches',6),
        ('afv-tracked','life-support.basic',1,NULL,3,3500,
         'published_override',7),
        ('afv-tracked','additional.fresher',1,NULL,6,1500,
         'matches',8),
        ('afv-tracked','additional.galley-full',1,8,21,6000,
         'formula',9),
        ('atv-tracked','control.advanced',1,NULL,2,10000,'matches',1),
        ('atv-tracked','communication.class-4',1,NULL,0.10,4000,
         'matches',2),
        ('atv-tracked','sensor.basic-civilian',1,NULL,6,10000,
         'matches',3),
        ('atv-tracked','computer.model-3',1,NULL,0,2000,
         'matches',4),
        ('atv-tracked','accommodation.cockpit-extended',1,NULL,
         4,2000,'matches',5),
        ('atv-tracked','accommodation.seat-cramped',2,NULL,
         8,4000,'matches',6),
        ('atv-tracked','life-support.basic',1,NULL,3,3500,
         'published_override',7),
        ('atv-tracked','additional.fresher',1,NULL,6,1500,
         'matches',8),
        ('atv-tracked','additional.galley-full',1,8,21,6000,
         'formula',9),
        ('ground-car','control.basic',1,NULL,1,0,'matches',1),
        ('ground-car','accommodation.cockpit-extended',1,NULL,
         4,2000,'matches',2),
        ('ground-car','accommodation.seat-cramped',1,NULL,
         4,2000,'matches',3),
        ('stagecoach','control.primitive',1,NULL,0.5,-710,
         'formula',1),
        ('stagecoach','accommodation.cockpit-extended',1,NULL,
         4,2000,'matches',2),
        ('stagecoach','accommodation.seat-cramped',2,NULL,
         8,4000,'matches',3),
        ('van','control.basic',1,NULL,1,0,'matches',1),
        ('van','accommodation.cockpit-extended',1,NULL,
         4,2000,'matches',2),
        ('tunnel-boring-machine','control.basic',1,NULL,
         1,0,'matches',1),
        ('tunnel-boring-machine','communication.class-2',1,NULL,
         0.02,1000,'matches',2),
        ('tunnel-boring-machine','sensor.standard',1,NULL,
         3,5000,'matches',3),
        ('tunnel-boring-machine','computer.model-1',1,NULL,
         0.01,500,'matches',4),
        ('tunnel-boring-machine',
         'accommodation.cockpit-extended',1,NULL,
         4,2000,'matches',5),
        ('tunnel-boring-machine','life-support.basic',1,NULL,
         3,3500,'published_override',6),
        ('biplane','control.basic',1,NULL,1,0,'matches',1),
        ('biplane','accommodation.cockpit-basic',1,NULL,
         2,1000,'matches',2),
        ('biplane','accommodation.seat-standard',1,NULL,
         2,1000,'matches',3),
        ('helicopter','control.basic',1,NULL,1,0,'matches',1),
        ('helicopter','communication.class-3',1,NULL,
         0.05,2000,'matches',2),
        ('helicopter','accommodation.cockpit-extended',1,NULL,
         4,2000,'matches',3),
        ('helicopter','accommodation.seat-cramped',2,NULL,
         8,4000,'matches',4),
        ('twin-engine-jet','control.basic',1,NULL,1,0,'matches',1),
        ('twin-engine-jet','communication.class-3',1,NULL,
         0.05,2000,'matches',2),
        ('twin-engine-jet','accommodation.cockpit-extended',1,NULL,
         4,2000,'matches',3),
        ('twin-engine-jet','accommodation.seat-cramped',2,NULL,
         8,4000,'matches',4),
        ('hovercraft','control.basic',1,NULL,1,0,'matches',1),
        ('hovercraft','communication.class-3',1,NULL,
         0.05,2000,'matches',2),
        ('hovercraft','accommodation.cockpit-basic',1,NULL,
         2,1000,'matches',3),
        ('hovercraft','accommodation.seat-cramped',5,NULL,
         20,10000,'matches',4),
        ('hovercraft','additional.fresher',1,NULL,
         6,1500,'matches',5)
)
INSERT INTO vehicle_class_component (
    vehicle_class_rule_id,component_rule_id,quantity,rating,
    allocated_spaces,display_order,published_cost_minor,
    calculation_status,tech_level_status,source_locator_id
)
SELECT class.vehicle_class_rule_id,component.component_rule_id,
       source.quantity,source.rating,source.allocated_spaces,
       source.display_order,source.published_cost,
       source.calculation_status,'matches',class.source_locator_id
FROM source
JOIN vehicle_class class USING (class_code)
JOIN vehicle_component_definition component USING (component_code);

INSERT INTO vehicle_class_configuration_option (
    vehicle_class_rule_id,option_rule_id,allocated_spaces,
    published_cost_minor,source_locator_id
)
SELECT class.vehicle_class_rule_id,option.option_rule_id,
       source.spaces,source.cost_minor,class.source_locator_id
FROM (
    VALUES
        ('g-carrier','vacuum-environmental-protection',
         3::numeric,960000::bigint),
        ('grav-tank','vacuum-environmental-protection',3,960000),
        ('speeder','streamlined',0,17750),
        ('speeder','vacuum-environmental-protection',3,240000),
        ('afv-tracked','insidious-environmental-protection',6,50000),
        ('atv-tracked','insidious-environmental-protection',6,50000),
        ('tunnel-boring-machine',
         'hostile-environmental-protection',3,240000)
) source(class_code,option_code,spaces,cost_minor)
JOIN vehicle_class class USING (class_code)
JOIN rule_vehicle_configuration_option option USING (option_code);

INSERT INTO vehicle_class_drive_option (
    vehicle_class_rule_id,option_rule_id,option_steps,
    published_cost_minor,source_locator_id
)
SELECT class.vehicle_class_rule_id,option.option_rule_id,
       1,10725,class.source_locator_id
FROM vehicle_class class
CROSS JOIN rule_vehicle_drive_option option
WHERE class.class_code IN ('afv-tracked','atv-tracked')
  AND option.option_code='off-road-capability';

INSERT INTO vehicle_class_autopilot (
    vehicle_class_rule_id,vehicle_category,skill_rule_id,
    skill_level,published_cost_minor,source_locator_id,
    calculation_status
)
SELECT class.vehicle_class_rule_id,'ground_vehicle',
       skill.rule_id,source.skill_level,source.cost_minor,
       class.source_locator_id,source.calculation_status
FROM (
    VALUES
        ('air-raft','skill.grav-vehicle',0::smallint,
         2000::bigint,'matches'),
        ('g-carrier','skill.grav-vehicle',2,2000,
         'published_override'),
        ('grav-bike','skill.grav-vehicle',1,7000,'matches'),
        ('grav-floater','skill.grav-vehicle',1,7000,'matches'),
        ('grav-tank','skill.grav-vehicle',0,2000,'matches'),
        ('speeder','skill.grav-vehicle',0,2000,'matches'),
        ('afv-tracked','skill.tracked-vehicle',1,2000,
         'published_override'),
        ('atv-tracked','skill.tracked-vehicle',1,2000,
         'published_override')
) source(
    class_code,skill_code,skill_level,cost_minor,calculation_status
)
JOIN vehicle_class class USING (class_code)
JOIN rule_rule skill
  ON skill.rule_code=source.skill_code;

INSERT INTO vehicle_class_computer_option (
    vehicle_class_rule_id,option_code,
    published_incremental_cost_minor,source_locator_id
)
SELECT class.vehicle_class_rule_id,'hardened',source.cost_minor,
       class.source_locator_id
FROM (
    VALUES
        ('g-carrier',5000::bigint),
        ('grav-tank',250)
) source(class_code,cost_minor)
JOIN vehicle_class class USING (class_code);

INSERT INTO vehicle_class_fuel_tank (
    vehicle_class_rule_id,power_plant_code,fuel_kind,
    capacity_kilolitres,endurance_hours,source_locator_id
)
SELECT class.vehicle_class_rule_id,source.power_plant_code,
       source.fuel_kind,source.capacity,source.endurance,
       class.source_locator_id
FROM (
    VALUES
        ('air-raft','early-fusion','hydrogen',
         1.61::numeric,672::numeric),
        ('g-carrier','advanced-fusion','hydrogen',7.06,672),
        ('grav-bike','fusion','hydrogen',0.32,672),
        ('grav-floater','early-fusion','hydrogen',0.17,336),
        ('grav-tank','early-fusion','hydrogen',14.11,672),
        ('speeder','early-fusion','hydrogen',0.81,672),
        ('afv-tracked','fusion','hydrogen',1.51,72),
        ('atv-tracked','fusion','hydrogen',1.51,72),
        ('ground-car','internal-combustion','hydrocarbons',0.012,5),
        ('van','internal-combustion','hydrocarbons',0.072,10),
        ('tunnel-boring-machine','gas-turbine','hydrocarbons',
         0.68,48),
        ('biplane','internal-combustion','hydrocarbons',0.014,3),
        ('helicopter','gas-turbine','hydrocarbons',0.09,3),
        ('twin-engine-jet','gas-turbine','hydrocarbons',0.23,6),
        ('hovercraft','gas-turbine','hydrocarbons',0.43,16)
) source(
    class_code,power_plant_code,fuel_kind,capacity,endurance
)
JOIN vehicle_class class USING (class_code);

INSERT INTO vehicle_class_alternative_communication (
    vehicle_class_rule_id,communication_component_rule_id,
    communicator_type_code,allocated_spaces,
    published_cost_minor,source_locator_id
)
SELECT class.vehicle_class_rule_id,component.component_rule_id,
       'laser',0.2,12000,class.source_locator_id
FROM vehicle_class class
CROSS JOIN vehicle_component_definition component
WHERE class.class_code IN ('afv-tracked','atv-tracked')
  AND component.component_code='communication.class-4';
