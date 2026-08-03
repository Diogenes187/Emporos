INSERT INTO src_artifact (
    source_work_id,artifact_kind,source_uri,source_revision,
    byte_length,checksum_sha256,media_type,local_role
)
SELECT source_work_id,'repository_file',source.source_uri,
       '0839018902355215fb8148f0b4ce1b1f8e011080',
       source.byte_length,source.checksum,'text/markdown','governing'
FROM src_work
CROSS JOIN (
    VALUES
        ('src/vds/common-grav-vehicles.md',12563::bigint,
         '184e34c197c3d1e4379f613ea6f33f439b55752393fd46de2b94afa85239c33d'),
        ('src/vds/common-ground-vehicles.md',9546::bigint,
         '5265e0bf4f16b715722ce516e7be657b61a01cfcc2a81a3b73b633a9d1a1e0f6'),
        ('src/vds/uncommon-vehicles.md',2063::bigint,
         '17d9294fdb344b71952173c3f1fef0065cc80c7c1d890e58ae2d8e5d7d3a62ad')
) source(source_uri,byte_length,checksum)
WHERE work_code='cepheus-engine.github-v9.1';

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
         'Common Grav Vehicles',
         'Cepheus Engine VDS, Common Grav Vehicles'),
        ('src/vds/common-ground-vehicles.md',
         'Common Ground Vehicles',
         'Cepheus Engine VDS, Common Ground Vehicles'),
        ('src/vds/uncommon-vehicles.md',
         'Uncommon Vehicles',
         'Cepheus Engine VDS, Uncommon Vehicles')
) source(source_uri,heading_path,display_citation)
  ON source.source_uri=artifact.source_uri;

ALTER TABLE vehicle_class
    ALTER COLUMN allocated_spaces TYPE numeric,
    ALTER COLUMN cargo_spaces TYPE numeric;

ALTER TABLE vehicle_class_propulsion
    ADD COLUMN speed_multiplier numeric NOT NULL DEFAULT 1 CHECK (
        speed_multiplier>0
    ),
    ADD COLUMN reported_top_speed numeric CHECK (
        reported_top_speed>0
    ),
    ADD COLUMN reported_cruise_speed numeric CHECK (
        reported_cruise_speed>0
    ),
    ADD COLUMN reported_speed_unit text CHECK (
        reported_speed_unit IS NULL OR reported_speed_unit IN (
            'kilometre_per_hour','metre_per_hour','external'
        )
    ),
    ADD COLUMN calculation_status text NOT NULL DEFAULT 'matches' CHECK (
        calculation_status IN (
            'matches','modified','source_conflict','external'
        )
    ),
    ADD CHECK (
        (
            reported_top_speed IS NOT NULL
            AND reported_speed_unit IS NOT NULL
        )
        OR (
            calculation_status='external'
            AND reported_top_speed IS NULL
            AND reported_cruise_speed IS NULL
            AND reported_speed_unit='external'
        )
    );

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
    is_non_powered boolean;
BEGIN
    SELECT chassis_code,minimum_tech_level
    INTO class_chassis,class_tech
    FROM vehicle_class
    WHERE vehicle_class_rule_id=NEW.vehicle_class_rule_id;
    SELECT minimum_tech_level,
           propulsion_code LIKE '%non-powered'
    INTO propulsion_tech,is_non_powered
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
       OR (
           NOT is_non_powered
           AND (
               power_drive_order IS NULL
               OR power_drive_order<propulsion_drive_order
           )
       )
       OR (
           NEW.performance>0
           AND NOT is_non_powered
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

INSERT INTO rule_rule (
    content_package_id,rule_code,name,rule_category,rule_status
)
SELECT package.content_package_id,
       'vehicle.class.'||source.class_code,
       source.class_name,'vehicle','approved'
FROM sys_content_package package
CROSS JOIN (
    VALUES
        ('air-raft','Air/Raft'),('g-carrier','G/Carrier'),
        ('grav-bike','Grav Bike'),('grav-floater','Grav Floater'),
        ('grav-tank','Grav Tank'),('speeder','Speeder'),
        ('afv-tracked','AFV, Tracked'),('atv-tracked','ATV, Tracked'),
        ('ground-car','Ground Car'),('stagecoach','Stagecoach'),
        ('van','Van'),('tunnel-boring-machine','Tunnel Boring Machine')
) source(class_code,class_name)
WHERE package.package_code='cepheus-engine';

INSERT INTO vehicle_class (
    vehicle_class_rule_id,class_code,chassis_code,
    minimum_tech_level,configuration,standard_design,
    armor_code,armor_rating,hull_points,structure_points,
    allocated_spaces,cargo_spaces,construction_cost_minor,
    construction_hours,source_locator_id
)
SELECT rule.rule_id,source.class_code,source.chassis_code,
       source.tech_level,source.configuration,true,
       source.armor_code,source.armor_rating,
       source.hull_points,source.structure_points,
       source.allocated_spaces,source.cargo_spaces,
       source.construction_cost_minor,source.construction_hours,
       locator.source_locator_id
FROM (
    VALUES
        ('air-raft','8',9,'open','titanium-steel',3,0,1,23.43,24.57,94160::bigint,36,'Common Grav Vehicles'),
        ('g-carrier','C',15,'closed','bonded-superdense',18,1,2,71.01,24.99,3138560,864,'Common Grav Vehicles'),
        ('grav-bike','3',12,'open','superdense',5,0,1,3.79,2.21,41390,5,'Common Grav Vehicles'),
        ('grav-floater','5',11,'open','crystaliron',4,0,1,7.61,4.39,30580,9,'Common Grav Vehicles'),
        ('grav-tank','C',9,'closed','titanium-steel',9,1,2,83.82,12.18,1469400,432,'Common Grav Vehicles'),
        ('speeder','6',9,'closed','titanium-steel',3,0,1,21.57,2.43,330250,18,'Common Grav Vehicles'),
        ('afv-tracked','E',12,'closed','superdense',25,2,2,108.69,11.31,287790,240,'Common Ground Vehicles'),
        ('atv-tracked','E',12,'closed','superdense',5,2,2,75.19,44.81,154410,60,'Common Ground Vehicles'),
        ('ground-car','5',5,'closed','iron',2,0,1,11.962,0.038,6290,9,'Common Ground Vehicles'),
        ('stagecoach','6',3,'open','wood',1,0,1,13.5,10.5,8080,18,'Common Ground Vehicles'),
        ('van','6',5,'closed','iron',2,0,1,14.172,9.828,6540,18,'Common Ground Vehicles'),
        ('tunnel-boring-machine','8',8,'closed','titanium-steel',3,0,1,33.21,14.79,282650,36,'Uncommon Vehicles')
) source(
    class_code,chassis_code,tech_level,configuration,
    armor_code,armor_rating,hull_points,structure_points,
    allocated_spaces,cargo_spaces,construction_cost_minor,
    construction_hours,heading_path
)
JOIN rule_rule rule
  ON rule.rule_code='vehicle.class.'||source.class_code
JOIN src_locator locator
  ON locator.heading_path=source.heading_path;

INSERT INTO vehicle_class_power_plant (
    vehicle_class_rule_id,drive_code,power_plant_code
)
SELECT rule.rule_id,source.drive_code,source.power_plant_code
FROM (
    VALUES
        ('air-raft','E','early-fusion'),('g-carrier','S','advanced-fusion'),
        ('grav-bike','B','fusion'),('grav-floater','B','early-fusion'),
        ('grav-tank','S','early-fusion'),('speeder','E','early-fusion'),
        ('afv-tracked','Q','fusion'),('atv-tracked','Q','fusion'),
        ('ground-car','C','internal-combustion'),
        ('van','E','internal-combustion'),
        ('tunnel-boring-machine','G','gas-turbine')
) source(class_code,drive_code,power_plant_code)
JOIN rule_rule rule
  ON rule.rule_code='vehicle.class.'||source.class_code;

INSERT INTO vehicle_class_propulsion (
    vehicle_class_rule_id,propulsion_code,drive_code,
    speed_variant,performance,speed_multiplier,
    reported_top_speed,reported_cruise_speed,
    reported_speed_unit,calculation_status
)
SELECT rule.rule_id,source.propulsion_code,source.drive_code,
       'standard',source.performance,source.speed_multiplier,
       source.top_speed,source.cruise_speed,source.speed_unit,
       source.calculation_status
FROM (
    VALUES
        ('air-raft','grav','E',1,1,100::numeric,75::numeric,'kilometre_per_hour','matches'),
        ('g-carrier','extreme-grav','S',5,1,2000,1500,'kilometre_per_hour','matches'),
        ('grav-bike','advanced-grav','B',2,1,400,300,'kilometre_per_hour','matches'),
        ('grav-floater','grav','B',1,1,100,75,'kilometre_per_hour','matches'),
        ('grav-tank','grav','S',5,1,500,375,'kilometre_per_hour','matches'),
        ('speeder','grav','E',2,5,1000,750,'kilometre_per_hour','modified'),
        ('afv-tracked','tracks','Q',3,0.9,67.5,50,'kilometre_per_hour','modified'),
        ('atv-tracked','tracks','Q',3,0.9,67.5,50,'kilometre_per_hour','modified'),
        ('ground-car','wheels','C',1,1,100,75,'kilometre_per_hour','source_conflict'),
        ('stagecoach','wheels-non-powered','D',1,1,NULL,NULL,'external','external'),
        ('van','wheels','E',2,1,100,75,'kilometre_per_hour','matches'),
        ('tunnel-boring-machine','mole','G',2,1,100,75,'metre_per_hour','matches')
) source(
    class_code,propulsion_code,drive_code,performance,
    speed_multiplier,top_speed,cruise_speed,speed_unit,
    calculation_status
)
JOIN rule_rule rule
  ON rule.rule_code='vehicle.class.'||source.class_code;

INSERT INTO src_record_provenance (
    rule_id,content_package_id,source_locator_id,
    provenance_class,is_primary_citation
)
SELECT rule.rule_id,rule.content_package_id,
       class.source_locator_id,'fills_source_gap',true
FROM rule_rule rule
JOIN vehicle_class class
  ON class.vehicle_class_rule_id=rule.rule_id
WHERE rule.rule_code LIKE 'vehicle.class.%';
