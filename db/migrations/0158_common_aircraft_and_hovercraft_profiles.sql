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
        ('src/vds/common-aircraft.md',4939::bigint,
         '0c2b925a5863f9c73e9788b409529b7a4333dd34a64675619c3ec8de7f6ee83f'),
        ('src/vds/common-watercraft.md',11609::bigint,
         '6258e916e6195fababc7541628e279a765de8fdf2a64e06b6b9edae401f1339d')
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
        ('src/vds/common-aircraft.md','Common Aircraft > TL5 Biplane',
         'Cepheus Engine VDS, Common Aircraft: TL5 Biplane'),
        ('src/vds/common-aircraft.md','Common Aircraft > TL7 Helicopter',
         'Cepheus Engine VDS, Common Aircraft: TL7 Helicopter'),
        ('src/vds/common-aircraft.md',
         'Common Aircraft > TL7 Twin Engine Jet',
         'Cepheus Engine VDS, Common Aircraft: TL7 Twin Engine Jet'),
        ('src/vds/common-watercraft.md',
         'Common Watercraft > TL7 Hovercraft',
         'Cepheus Engine VDS, Common Watercraft: TL7 Hovercraft')
) source(source_uri,heading_path,display_citation)
  ON source.source_uri=artifact.source_uri;

ALTER TABLE vehicle_class_propulsion
    ADD COLUMN reported_agility_dm smallint;

UPDATE vehicle_class_propulsion propulsion
SET reported_agility_dm=source.agility_dm
FROM (
    VALUES
        ('air-raft',0::smallint),('g-carrier',1::smallint),
        ('grav-bike',1::smallint),('grav-floater',2::smallint),
        ('grav-tank',1::smallint),('speeder',2::smallint),
        ('afv-tracked',-1::smallint),('atv-tracked',-1::smallint),
        ('ground-car',3::smallint),('stagecoach',1::smallint),
        ('van',3::smallint),('tunnel-boring-machine',-4::smallint)
) source(class_code,agility_dm)
JOIN vehicle_class class USING (class_code)
WHERE class.vehicle_class_rule_id=propulsion.vehicle_class_rule_id;

ALTER TABLE vehicle_class_propulsion
    ALTER COLUMN reported_agility_dm SET NOT NULL;

UPDATE vehicle_class
SET construction_cost_minor=94340
WHERE class_code='air-raft';

INSERT INTO rule_rule (
    content_package_id,rule_code,name,rule_category,rule_status
)
SELECT package.content_package_id,
       'vehicle.class.'||source.class_code,
       source.class_name,'vehicle','approved'
FROM sys_content_package package
CROSS JOIN (
    VALUES
        ('biplane','Biplane'),
        ('helicopter','Helicopter'),
        ('twin-engine-jet','Twin Engine Jet'),
        ('hovercraft','Hovercraft')
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
        ('biplane','5',5,'open','iron',2,0,1,
         11.01::numeric,0.99::numeric,20670::bigint,9,
         'Common Aircraft > TL5 Biplane'),
        ('helicopter','8',7,'closed','titanium-steel',3,0,1,
         36.14,11.86,154810,36,
         'Common Aircraft > TL7 Helicopter'),
        ('twin-engine-jet','9',7,'closed','titanium-steel',3,1,1,
         42.78,17.22,736110,45,
         'Common Aircraft > TL7 Twin Engine Jet'),
        ('hovercraft','C',7,'closed','titanium-steel',3,1,2,
         43.73,52.27,144660,36,
         'Common Watercraft > TL7 Hovercraft')
) source(
    class_code,chassis_code,tech_level,configuration,
    armor_code,armor_rating,hull_points,structure_points,
    allocated_spaces,cargo_spaces,construction_cost_minor,
    construction_hours,heading_path
)
JOIN rule_rule rule
  ON rule.rule_code='vehicle.class.'||source.class_code
JOIN src_locator locator
  ON locator.heading_path=source.heading_path
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1';

INSERT INTO vehicle_class_power_plant (
    vehicle_class_rule_id,drive_code,power_plant_code
)
SELECT rule.rule_id,source.drive_code,source.power_plant_code
FROM (
    VALUES
        ('biplane','D','internal-combustion'),
        ('helicopter','M','gas-turbine'),
        ('twin-engine-jet','N','gas-turbine'),
        ('hovercraft','L','gas-turbine')
) source(class_code,drive_code,power_plant_code)
JOIN rule_rule rule
  ON rule.rule_code='vehicle.class.'||source.class_code;

INSERT INTO vehicle_class_propulsion (
    vehicle_class_rule_id,propulsion_code,drive_code,
    speed_variant,performance,speed_multiplier,
    reported_top_speed,reported_cruise_speed,
    reported_speed_unit,calculation_status,reported_agility_dm
)
SELECT rule.rule_id,source.propulsion_code,source.drive_code,
       source.speed_variant,source.performance,1,
       source.top_speed,source.cruise_speed,
       'kilometre_per_hour','matches',source.agility_dm
FROM (
    VALUES
        ('biplane','rotor','D','horizontal',2,
         200::numeric,150::numeric,-1::smallint),
        ('helicopter','rotor','M','vertical',5,
         250,187.5,-2),
        ('twin-engine-jet','jet','N','standard',5,
         750,562.5,-1),
        ('hovercraft','air-cushion','L','standard',2,
         100,75,1)
) source(
    class_code,propulsion_code,drive_code,speed_variant,
    performance,top_speed,cruise_speed,agility_dm
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
WHERE rule.rule_code IN (
    'vehicle.class.biplane',
    'vehicle.class.helicopter',
    'vehicle.class.twin-engine-jet',
    'vehicle.class.hovercraft'
);

INSERT INTO src_issue (
    issue_code,domain_code,issue_type,review_priority,
    subject_code,title,problem_statement,
    published_value,calculated_value,
    reviewer_question,requested_evidence,engine_disposition
)
VALUES (
    'vehicle.class.biplane-chassis-code',
    'vehicle.catalogue','source_conflict','medium',
    'biplane',
    'Biplane chassis code conflicts with its tonnage and spaces',
    'The Biplane is described as a one-ton chassis and its table allocates 12 spaces, but the table labels the chassis Code 4. The governing chassis catalogue defines Code 4 as 0.75 tons and 9 spaces and Code 5 as one ton and 12 spaces.',
    'One ton and 12 spaces, labelled Code 4',
    'One ton and 12 spaces require Code 5',
    'Should the Biplane table chassis label be corrected from Code 4 to Code 5?',
    'A corrected printing, publisher errata, or another authorized Biplane construction profile.',
    'preserve_rule'
);

INSERT INTO src_issue_locator (
    source_issue_id,source_locator_id,evidence_role
)
SELECT issue.source_issue_id,locator.source_locator_id,'primary'
FROM src_issue issue
JOIN src_locator locator
  ON locator.heading_path='Common Aircraft > TL5 Biplane'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1'
WHERE issue.issue_code='vehicle.class.biplane-chassis-code';
