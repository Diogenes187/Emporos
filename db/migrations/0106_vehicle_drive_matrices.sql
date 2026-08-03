INSERT INTO src_locator (
    source_work_id,source_artifact_id,locator_type,
    heading_path,display_citation
)
SELECT artifact.source_work_id,artifact.source_artifact_id,
       'heading','Vehicle Design > Vehicle Fuel',
       'Cepheus Engine VDS, Vehicle Fuel'
FROM src_artifact artifact
JOIN src_work work ON work.source_work_id=artifact.source_work_id
WHERE work.work_code='cepheus-engine.github-v9.1'
  AND artifact.source_uri='src/vds/vehicle-design.md';

CREATE TABLE rule_vehicle_propulsion_type (
    propulsion_code text PRIMARY KEY CHECK (
        propulsion_code ~
        '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
    ),
    propulsion_name text NOT NULL UNIQUE CHECK (
        btrim(propulsion_name)<>''
    ),
    minimum_tech_level smallint NOT NULL CHECK (
        minimum_tech_level>=0
    ),
    propulsion_basis text NOT NULL CHECK (
        propulsion_basis IN ('contact','thrust')
    ),
    space_multiplier numeric NOT NULL CHECK (space_multiplier>0),
    price_multiplier numeric NOT NULL CHECK (price_multiplier>0),
    example_description text,
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_vehicle_propulsion_type
SELECT source.*,locator.source_locator_id
FROM (
    VALUES
        ('sails-non-powered','Sails, Non-Powered',1,'thrust',1,0.2,'Sailing Ship'),
        ('wheels-non-powered','Wheels, Non-Powered',1,'contact',1,0.5,'Stagecoach'),
        ('rails','Rails',3,'contact',2,1,'Train'),
        ('screw-propeller','Screw Propeller',3,'thrust',1,0.1,'Motor Boat, Steamship'),
        ('airship','Airship',4,'thrust',1,0.5,'Dirigible'),
        ('rotor','Rotor',4,'thrust',2,0.5,'Biplane, Helicopter'),
        ('tracks','Tracks',4,'contact',1,2,'Tank'),
        ('wheels','Wheels',4,'contact',1,1,'Ground Car'),
        ('jet','Jet',5,'thrust',2,2,'Twin-Engine Jet'),
        ('mole','Mole',5,'contact',2,8,'Mole'),
        ('air-cushion','Air Cushion',7,'thrust',1,0.5,'Hovercraft'),
        ('hypersonic','Hypersonic',8,'thrust',1.5,4,'Passenger Air Liner'),
        ('legs','Legs',8,'contact',2,4,'Walker'),
        ('grav','Grav',9,'thrust',1,1,'Air/Raft, Speeder'),
        ('advanced-grav','Advanced Grav',12,'thrust',0.75,2,'Grav Bike'),
        ('extreme-grav','Extreme Grav',15,'thrust',0.5,4,'G/Carrier')
) source(
    propulsion_code,propulsion_name,minimum_tech_level,
    propulsion_basis,space_multiplier,price_multiplier,
    example_description
)
JOIN src_locator locator
  ON locator.heading_path='Vehicle Design > Vehicle Drives';

CREATE TABLE rule_vehicle_drive (
    drive_code text PRIMARY KEY CHECK (
        drive_code ~ '^[A-HJ-NP-Z]$'
    ),
    display_order smallint NOT NULL UNIQUE CHECK (display_order>0),
    power_plant_spaces numeric NOT NULL CHECK (power_plant_spaces>0),
    power_plant_price_minor bigint NOT NULL CHECK (
        power_plant_price_minor>0
    ),
    contact_drive_spaces numeric NOT NULL CHECK (
        contact_drive_spaces>0
    ),
    contact_drive_price_minor bigint NOT NULL CHECK (
        contact_drive_price_minor>0
    ),
    thrust_drive_spaces numeric NOT NULL CHECK (
        thrust_drive_spaces>0
    ),
    thrust_drive_price_minor bigint NOT NULL CHECK (
        thrust_drive_price_minor>0
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_vehicle_drive
SELECT source.*,locator.source_locator_id
FROM (
    VALUES
        ('A',1,0.11,125,0.15,150,0.12,6000),
        ('B',2,0.26,300,0.4,400,0.3,15000),
        ('C',3,0.4,450,0.55,550,0.5,25000),
        ('D',4,0.4,450,0.55,550,0.5,25000),
        ('E',5,1.25,1425,1.6,1575,1.4,70000),
        ('F',6,1.75,1975,2.3,2250,2,100000),
        ('G',7,2.25,2550,3,2925,2.5,125000),
        ('H',8,2.75,3100,3.5,3425,3,150000),
        ('J',9,3.5,3950,4.5,4400,4,200000),
        ('K',10,4,4500,5.25,5125,4.5,225000),
        ('L',11,4.5,5075,6,5850,5.25,262500),
        ('M',12,5.25,5925,7,6825,6.25,312500),
        ('N',13,6.75,7600,9,8775,8,400000),
        ('P',14,7.5,8450,10,9750,8.5,425000),
        ('Q',15,8.5,9575,11,10725,10,500000),
        ('R',16,9.5,10700,13,12675,11.5,575000),
        ('S',17,10.5,11825,14,13650,12,600000),
        ('T',18,12,13500,16,15600,13.5,675000),
        ('U',19,13.5,15200,18,17550,16,800000),
        ('V',20,15.5,17450,21,20475,18,900000),
        ('W',21,18.5,20825,25,24375,22,1100000),
        ('X',22,21.5,24200,29,28275,26,1300000),
        ('Y',23,25.5,28700,34,33150,30,1500000),
        ('Z',24,31,34875,41,39975,36,1800000)
) source(
    drive_code,display_order,power_plant_spaces,
    power_plant_price_minor,contact_drive_spaces,
    contact_drive_price_minor,thrust_drive_spaces,
    thrust_drive_price_minor
)
JOIN src_locator locator
  ON locator.heading_path='Vehicle Design > Vehicle Drives';

CREATE TABLE rule_vehicle_drive_performance (
    drive_code text NOT NULL REFERENCES rule_vehicle_drive(drive_code),
    chassis_code text NOT NULL REFERENCES
        rule_vehicle_chassis(chassis_code),
    performance smallint NOT NULL CHECK (performance BETWEEN 0 AND 6),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    PRIMARY KEY (drive_code,chassis_code)
);

WITH smaller(drive_code,performance_values) AS (
    VALUES
        ('A',ARRAY[4,1,0,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL]::smallint[]),
        ('B',ARRAY[NULL,4,2,1,1,0,NULL,NULL,NULL,NULL,NULL,NULL]::smallint[]),
        ('C',ARRAY[NULL,6,3,2,1,0,NULL,NULL,NULL,NULL,NULL,NULL]::smallint[]),
        ('D',ARRAY[NULL,NULL,5,3,2,1,0,0,NULL,NULL,NULL,NULL]::smallint[]),
        ('E',ARRAY[NULL,NULL,NULL,6,4,2,1,1,0,0,0,0]::smallint[]),
        ('F',ARRAY[NULL,NULL,NULL,NULL,6,3,2,1,1,1,0,0]::smallint[]),
        ('G',ARRAY[NULL,NULL,NULL,NULL,NULL,4,2,2,1,1,1,1]::smallint[]),
        ('H',ARRAY[NULL,NULL,NULL,NULL,NULL,5,3,2,2,1,1,1]::smallint[]),
        ('J',ARRAY[NULL,NULL,NULL,NULL,NULL,6,4,3,2,2,1,1]::smallint[]),
        ('K',ARRAY[NULL,NULL,NULL,NULL,NULL,NULL,5,3,3,2,2,1]::smallint[]),
        ('L',ARRAY[NULL,NULL,NULL,NULL,NULL,NULL,5,4,3,2,2,2]::smallint[]),
        ('M',ARRAY[NULL,NULL,NULL,NULL,NULL,NULL,6,5,4,3,2,2]::smallint[]),
        ('N',ARRAY[NULL,NULL,NULL,NULL,NULL,NULL,NULL,6,5,4,3,3]::smallint[]),
        ('P',ARRAY[NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,5,4,4,3]::smallint[]),
        ('Q',ARRAY[NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,6,5,4,4]::smallint[]),
        ('R',ARRAY[NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,6,5,4]::smallint[]),
        ('S',ARRAY[NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,6,5,5]::smallint[]),
        ('T',ARRAY[NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,6,5]::smallint[]),
        ('U',ARRAY[NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,6]::smallint[])
),
expanded AS (
    SELECT smaller.drive_code,chassis.chassis_code,
           value.performance
    FROM smaller
    CROSS JOIN unnest(
        ARRAY['1','2','3','4','5','6','7','8','9','A','B','C']
    ) WITH ORDINALITY chassis(chassis_code,position)
    JOIN LATERAL (
        SELECT smaller.performance_values[chassis.position]
            AS performance
    ) value ON value.performance IS NOT NULL
)
INSERT INTO rule_vehicle_drive_performance
SELECT expanded.*,locator.source_locator_id
FROM expanded
JOIN src_locator locator
  ON locator.heading_path='Vehicle Design > Vehicle Drives';

WITH larger(drive_code,performance_values) AS (
    VALUES
        ('F',ARRAY[0,0,0,0,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL]::smallint[]),
        ('G',ARRAY[0,0,0,0,0,0,0,0,NULL,NULL,NULL,NULL]::smallint[]),
        ('H',ARRAY[1,1,0,0,0,0,0,0,0,0,0,0]::smallint[]),
        ('J',ARRAY[1,1,1,1,1,0,0,0,0,0,0,0]::smallint[]),
        ('K',ARRAY[1,1,1,1,1,1,1,0,0,0,0,0]::smallint[]),
        ('L',ARRAY[1,1,1,1,1,1,1,1,1,0,0,0]::smallint[]),
        ('M',ARRAY[2,2,1,1,1,1,1,1,1,1,1,1]::smallint[]),
        ('N',ARRAY[2,2,2,2,2,1,1,1,1,1,1,1]::smallint[]),
        ('P',ARRAY[3,2,2,2,2,2,1,1,1,1,1,1]::smallint[]),
        ('Q',ARRAY[3,3,3,2,2,2,2,2,1,1,1,1]::smallint[]),
        ('R',ARRAY[4,3,3,3,2,2,2,2,2,2,2,1]::smallint[]),
        ('S',ARRAY[4,4,3,3,3,2,2,2,2,2,2,2]::smallint[]),
        ('T',ARRAY[5,4,4,3,3,3,3,2,2,2,2,2]::smallint[]),
        ('U',ARRAY[5,5,4,4,4,3,3,3,3,2,2,2]::smallint[]),
        ('V',ARRAY[6,6,5,5,4,4,4,3,3,3,3,3]::smallint[]),
        ('W',ARRAY[NULL,NULL,6,6,5,5,4,4,4,4,3,3]::smallint[]),
        ('X',ARRAY[NULL,NULL,NULL,NULL,6,6,5,5,5,4,4,4]::smallint[]),
        ('Y',ARRAY[NULL,NULL,NULL,NULL,NULL,NULL,6,6,5,5,5,5]::smallint[]),
        ('Z',ARRAY[NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,6,6,6]::smallint[])
),
expanded AS (
    SELECT larger.drive_code,chassis.chassis_code,
           value.performance
    FROM larger
    CROSS JOIN unnest(
        ARRAY['D','E','F','G','H','J','K','L','M','N','P','Q']
    ) WITH ORDINALITY chassis(chassis_code,position)
    JOIN LATERAL (
        SELECT larger.performance_values[chassis.position]
            AS performance
    ) value ON value.performance IS NOT NULL
)
INSERT INTO rule_vehicle_drive_performance
SELECT expanded.*,locator.source_locator_id
FROM expanded
JOIN src_locator locator
  ON locator.heading_path='Vehicle Design > Vehicle Drives';

CREATE TABLE rule_vehicle_propulsion_speed (
    propulsion_code text NOT NULL REFERENCES
        rule_vehicle_propulsion_type(propulsion_code),
    speed_variant text NOT NULL CHECK (btrim(speed_variant)<>''),
    performance smallint NOT NULL CHECK (performance BETWEEN 1 AND 6),
    base_speed integer NOT NULL CHECK (base_speed>0),
    speed_unit text NOT NULL CHECK (
        speed_unit IN ('kilometre_per_hour','metre_per_hour')
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    PRIMARY KEY (propulsion_code,speed_variant,performance)
);

WITH source(
    propulsion_code,speed_variant,speed_values,speed_unit
) AS (
    VALUES
        ('rails','standard',ARRAY[40,80,120,160,200,240],'kilometre_per_hour'),
        ('screw-propeller','standard',ARRAY[20,40,60,80,100,120],'kilometre_per_hour'),
        ('airship','standard',ARRAY[30,60,90,120,150,180],'kilometre_per_hour'),
        ('rotor','horizontal',ARRAY[100,200,300,400,500,600],'kilometre_per_hour'),
        ('rotor','vertical',ARRAY[50,100,150,200,250,300],'kilometre_per_hour'),
        ('tracks','standard',ARRAY[25,50,75,100,125,150],'kilometre_per_hour'),
        ('wheels','standard',ARRAY[50,100,150,200,250,300],'kilometre_per_hour'),
        ('jet','standard',ARRAY[150,300,450,600,750,900],'kilometre_per_hour'),
        ('mole','standard',ARRAY[50,100,150,200,250,300],'metre_per_hour'),
        ('air-cushion','standard',ARRAY[50,100,150,200,250,300],'kilometre_per_hour'),
        ('hypersonic','standard',ARRAY[300,600,900,1200,1500,1800],'kilometre_per_hour'),
        ('legs','standard',ARRAY[50,100,150,200,250,300],'kilometre_per_hour'),
        ('grav','standard',ARRAY[100,200,300,400,500,600],'kilometre_per_hour'),
        ('advanced-grav','standard',ARRAY[200,400,600,800,1000,1200],'kilometre_per_hour'),
        ('extreme-grav','standard',ARRAY[400,800,1200,1600,2000,2400],'kilometre_per_hour')
),
expanded AS (
    SELECT source.propulsion_code,source.speed_variant,
           speed.performance,speed.base_speed,source.speed_unit
    FROM source
    CROSS JOIN unnest(source.speed_values)
        WITH ORDINALITY speed(base_speed,performance)
)
INSERT INTO rule_vehicle_propulsion_speed
SELECT expanded.*,locator.source_locator_id
FROM expanded
JOIN src_locator locator
  ON locator.heading_path='Vehicle Design > Vehicle Drives';

CREATE TABLE rule_vehicle_drive_fuel_requirement (
    drive_code text PRIMARY KEY REFERENCES rule_vehicle_drive(drive_code),
    fuel_basis_spaces numeric NOT NULL CHECK (fuel_basis_spaces>0),
    fuel_spaces_per_week numeric NOT NULL CHECK (
        fuel_spaces_per_week>=0
    ),
    fuel_spaces_per_day numeric NOT NULL CHECK (
        fuel_spaces_per_day>=0
    ),
    fuel_spaces_per_hour numeric NOT NULL CHECK (
        fuel_spaces_per_hour>=0
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_vehicle_drive_fuel_requirement
SELECT source.*,locator.source_locator_id
FROM (
    VALUES
        ('A',0.11,0.03,0.0043,0.00018),('B',0.26,0.09,0.012,0.00052),
        ('C',0.4,0.13,0.019,0.00077),('D',0.75,0.25,0.036,0.0015),
        ('E',1.25,0.41,0.059,0.0024),('F',1.75,0.58,0.083,0.0035),
        ('G',2.25,0.75,0.11,0.0047),('H',2.75,0.91,0.13,0.0054),
        ('J',3.5,1.16,0.17,0.0069),('K',4,1.33,0.19,0.0079),
        ('L',4.5,1.50,0.21,0.0089),('M',5.25,1.75,0.25,0.010),
        ('N',6.75,2.25,0.32,0.013),('P',7.5,2.50,0.36,0.015),
        ('Q',8.5,2.83,0.40,0.017),('R',9.5,3.16,0.45,0.019),
        ('S',10.5,3.50,0.50,0.021),('T',12,4.00,0.57,0.024),
        ('U',13.5,4.50,0.64,0.027),('V',15.5,5.16,0.73,0.031),
        ('W',18.5,6.16,0.88,0.037),('X',21.5,7.16,1.02,0.043),
        ('Y',25.5,8.50,1.21,0.051),('Z',31,10.33,1.48,0.061)
) source(
    drive_code,fuel_basis_spaces,fuel_spaces_per_week,
    fuel_spaces_per_day,fuel_spaces_per_hour
)
JOIN src_locator locator
  ON locator.heading_path='Vehicle Design > Vehicle Fuel';

CREATE TABLE rule_vehicle_power_plant_fuel (
    power_plant_code text NOT NULL REFERENCES
        rule_vehicle_power_plant_type(power_plant_code),
    fuel_kind text NOT NULL CHECK (
        fuel_kind IN (
            'wood','coal','hydrocarbons','radioactives',
            'hydrogen','antimatter_service'
        )
    ),
    consumption_multiplier numeric NOT NULL CHECK (
        consumption_multiplier>=0
    ),
    price_per_fuel_space_minor bigint,
    fixed_refuel_interval_days smallint CHECK (
        fixed_refuel_interval_days>0
    ),
    fixed_service_price_per_plant_space_minor bigint,
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    PRIMARY KEY (power_plant_code,fuel_kind),
    CHECK (
        price_per_fuel_space_minor IS NOT NULL
        OR fixed_service_price_per_plant_space_minor IS NOT NULL
    )
);

INSERT INTO rule_vehicle_power_plant_fuel
SELECT source.*,locator.source_locator_id
FROM (
    VALUES
        ('external-combustion','wood',9,540::bigint,NULL::smallint,NULL::bigint),
        ('external-combustion','coal',5,540,NULL,NULL),
        ('internal-combustion','hydrocarbons',3,830,NULL,NULL),
        ('fission','radioactives',0.04,8300,NULL,NULL),
        ('fuel-cell-closed','hydrogen',20,40,NULL,NULL),
        ('fuel-cell-open','hydrogen',2,40,NULL,NULL),
        ('gas-turbine','hydrocarbons',3,830,NULL,NULL),
        ('early-fusion','hydrogen',1,40,NULL,NULL),
        ('fusion','hydrogen',0.75,40,NULL,NULL),
        ('advanced-fusion','hydrogen',0.5,40,NULL,NULL),
        ('antimatter','antimatter_service',0,NULL,30,40)
) source(
    power_plant_code,fuel_kind,consumption_multiplier,
    price_per_fuel_space_minor,fixed_refuel_interval_days,
    fixed_service_price_per_plant_space_minor
)
JOIN src_locator locator
  ON locator.heading_path='Vehicle Design > Vehicle Fuel';

CREATE TABLE vehicle_class_power_plant (
    vehicle_class_rule_id bigint PRIMARY KEY REFERENCES
        vehicle_class(vehicle_class_rule_id),
    drive_code text NOT NULL REFERENCES rule_vehicle_drive(drive_code),
    power_plant_code text NOT NULL REFERENCES
        rule_vehicle_power_plant_type(power_plant_code),
    quantity smallint NOT NULL DEFAULT 1 CHECK (quantity>0)
);

CREATE TABLE vehicle_class_propulsion (
    vehicle_class_rule_id bigint NOT NULL REFERENCES
        vehicle_class(vehicle_class_rule_id),
    propulsion_code text NOT NULL REFERENCES
        rule_vehicle_propulsion_type(propulsion_code),
    drive_code text NOT NULL REFERENCES rule_vehicle_drive(drive_code),
    speed_variant text NOT NULL DEFAULT 'standard',
    performance smallint NOT NULL CHECK (performance BETWEEN 0 AND 6),
    PRIMARY KEY (vehicle_class_rule_id,propulsion_code)
);

CREATE OR REPLACE FUNCTION vehicle_validate_class_power_plant()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    class_tech smallint;
    plant_tech smallint;
BEGIN
    SELECT minimum_tech_level INTO class_tech
    FROM vehicle_class
    WHERE vehicle_class_rule_id=NEW.vehicle_class_rule_id;
    SELECT minimum_tech_level INTO plant_tech
    FROM rule_vehicle_power_plant_type
    WHERE power_plant_code=NEW.power_plant_code;
    IF class_tech<plant_tech THEN
        RAISE EXCEPTION 'Vehicle power plant exceeds design tech level'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER vehicle_class_power_plant_valid
BEFORE INSERT OR UPDATE ON vehicle_class_power_plant
FOR EACH ROW EXECUTE FUNCTION
    vehicle_validate_class_power_plant();

CREATE OR REPLACE FUNCTION vehicle_validate_class_drive()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    class_chassis text;
    class_tech smallint;
    published_performance smallint;
    propulsion_tech smallint;
    propulsion_drive_order smallint;
    power_drive_order smallint;
BEGIN
    SELECT chassis_code,minimum_tech_level
    INTO class_chassis,class_tech
    FROM vehicle_class
    WHERE vehicle_class_rule_id=NEW.vehicle_class_rule_id;
    SELECT minimum_tech_level INTO propulsion_tech
    FROM rule_vehicle_propulsion_type
    WHERE propulsion_code=NEW.propulsion_code;
    SELECT performance INTO published_performance
    FROM rule_vehicle_drive_performance
    WHERE drive_code=NEW.drive_code
      AND chassis_code=class_chassis;
    SELECT display_order INTO propulsion_drive_order
    FROM rule_vehicle_drive
    WHERE drive_code=NEW.drive_code;
    SELECT drive.display_order INTO power_drive_order
    FROM vehicle_class_power_plant plant
    JOIN rule_vehicle_drive drive
      ON drive.drive_code=plant.drive_code
    WHERE plant.vehicle_class_rule_id=NEW.vehicle_class_rule_id;
    IF published_performance IS NULL
       OR NEW.performance<>published_performance
       OR class_tech<propulsion_tech
       OR power_drive_order IS NULL
       OR power_drive_order<propulsion_drive_order
       OR (
           NEW.performance>0
           AND NOT EXISTS (
               SELECT 1 FROM rule_vehicle_propulsion_speed
               WHERE propulsion_code=NEW.propulsion_code
                 AND speed_variant=NEW.speed_variant
                 AND performance=NEW.performance
           )
       ) THEN
        RAISE EXCEPTION 'Vehicle propulsion disagrees with VDS matrices'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER vehicle_class_propulsion_valid
BEFORE INSERT OR UPDATE ON vehicle_class_propulsion
FOR EACH ROW EXECUTE FUNCTION vehicle_validate_class_drive();
