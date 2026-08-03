INSERT INTO src_locator (
    source_work_id,source_artifact_id,locator_type,
    heading_path,display_citation
)
SELECT artifact.source_work_id,artifact.source_artifact_id,
       'heading',source.heading_path,source.display_citation
FROM src_artifact artifact
CROSS JOIN (
    VALUES
        ('Vehicle Design > Vehicle Controls',
         'Cepheus Engine VDS, Vehicle Controls'),
        ('Vehicle Design > Vehicle Communication Systems',
         'Cepheus Engine VDS, Vehicle Communication Systems'),
        ('Vehicle Design > Vehicle Sensors',
         'Cepheus Engine VDS, Vehicle Sensors'),
        ('Vehicle Design > Vehicle Computer',
         'Cepheus Engine VDS, Vehicle Computer')
) source(heading_path,display_citation)
WHERE artifact.source_uri='src/vds/vehicle-design.md';

CREATE TABLE rule_vehicle_electronics_range (
    range_code text PRIMARY KEY CHECK (
        range_code ~ '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
    ),
    range_name text NOT NULL UNIQUE CHECK (btrim(range_name)<>''),
    display_order smallint NOT NULL UNIQUE CHECK (display_order>0),
    maximum_range_km numeric CHECK (maximum_range_km>0),
    derivation_status text NOT NULL CHECK (
        derivation_status IN ('published','source_unspecified')
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    CHECK (
        (derivation_status='published' AND maximum_range_km IS NOT NULL)
        OR
        (derivation_status='source_unspecified'
         AND maximum_range_km IS NULL)
    )
);

INSERT INTO rule_vehicle_electronics_range
SELECT source.*,locator.source_locator_id
FROM (
    VALUES
        ('long','Long',1,NULL::numeric,'source_unspecified'),
        ('very-long','Very Long',2,0.5,'published'),
        ('distant','Distant',3,5,'published'),
        ('very-distant','Very Distant',4,50,'published'),
        ('regional','Regional',5,500,'published'),
        ('continental','Continental',6,5000,'published')
) source(
    range_code,range_name,display_order,maximum_range_km,
    derivation_status
)
JOIN src_locator locator
  ON locator.heading_path=
     'Vehicle Design > Vehicle Communication Systems';

WITH source(
    component_code,component_name,component_kind,
    minimum_tech_level,unit_spaces,unit_cost_minor,heading_path
) AS (
    VALUES
        ('control.primitive','Primitive Controls','controls',1,0.5,0::bigint,
         'Vehicle Design > Vehicle Controls'),
        ('control.basic','Basic Controls','controls',4,1,0,
         'Vehicle Design > Vehicle Controls'),
        ('control.advanced','Advanced Controls','controls',8,2,10000,
         'Vehicle Design > Vehicle Controls'),
        ('control.exo-skeleton','Exo-Skeleton Linkage','controls',10,3,100000,
         'Vehicle Design > Vehicle Controls'),
        ('control.neural-linked','Neural-linked Controls','controls',12,4,200000,
         'Vehicle Design > Vehicle Controls'),
        ('drone-controller.primitive','Primitive Drone Controller','controls',5,0.5,10000,
         'Vehicle Design > Vehicle Controls'),
        ('drone-controller.basic','Basic Drone Controller','controls',7,1,50000,
         'Vehicle Design > Vehicle Controls'),
        ('drone-controller.advanced','Advanced Drone Controller','controls',9,2,100000,
         'Vehicle Design > Vehicle Controls'),
        ('drone-controller.exo-skeleton','Exo-Skeleton Drone Controller','controls',11,3,200000,
         'Vehicle Design > Vehicle Controls'),
        ('drone-controller.neural-linked','Neural-linked Drone Controller','controls',13,4,500000,
         'Vehicle Design > Vehicle Controls'),
        ('robot-brain.linear','Linear Robot Brain','computer',8,3,22500,
         'Vehicle Design > Vehicle Controls'),
        ('robot-brain.parallel','Parallel Robot Brain','computer',10,2,40000,
         'Vehicle Design > Vehicle Controls'),
        ('robot-brain.synaptic','Synaptic Robot Brain','computer',12,1,90000,
         'Vehicle Design > Vehicle Controls'),
        ('communication.class-1','Class I Communication System','communications',5,0.01,500,
         'Vehicle Design > Vehicle Communication Systems'),
        ('communication.class-2','Class II Communication System','communications',5,0.02,1000,
         'Vehicle Design > Vehicle Communication Systems'),
        ('communication.class-3','Class III Communication System','communications',6,0.05,2000,
         'Vehicle Design > Vehicle Communication Systems'),
        ('communication.class-4','Class IV Communication System','communications',8,0.10,4000,
         'Vehicle Design > Vehicle Communication Systems'),
        ('sensor.standard','Standard Sensors','sensors',8,3,5000,
         'Vehicle Design > Vehicle Sensors'),
        ('sensor.basic-civilian','Basic Civilian Sensors','sensors',9,6,10000,
         'Vehicle Design > Vehicle Sensors'),
        ('sensor.basic-military','Basic Military Sensors','sensors',10,12,20000,
         'Vehicle Design > Vehicle Sensors'),
        ('sensor.advanced','Advanced Sensors','sensors',11,18,50000,
         'Vehicle Design > Vehicle Sensors'),
        ('sensor.very-advanced','Very Advanced Sensors','sensors',12,30,100000,
         'Vehicle Design > Vehicle Sensors'),
        ('computer.model-0','Vehicle Computer Model 0','computer',7,0.02,100,
         'Vehicle Design > Vehicle Computer'),
        ('computer.model-1','Vehicle Computer Model 1','computer',8,0.01,500,
         'Vehicle Design > Vehicle Computer'),
        ('computer.model-2','Vehicle Computer Model 2','computer',10,0,1000,
         'Vehicle Design > Vehicle Computer'),
        ('computer.model-3','Vehicle Computer Model 3','computer',12,0,2000,
         'Vehicle Design > Vehicle Computer'),
        ('computer.model-4','Vehicle Computer Model 4','computer',13,0,3000,
         'Vehicle Design > Vehicle Computer'),
        ('computer.model-5','Vehicle Computer Model 5','computer',14,0,10000,
         'Vehicle Design > Vehicle Computer')
)
INSERT INTO rule_rule (
    content_package_id,rule_code,name,rule_category,rule_status
)
SELECT package.content_package_id,
       'vehicle.component.'||source.component_code,
       source.component_name,'vehicle','approved'
FROM source
CROSS JOIN sys_content_package package
WHERE package.package_code='cepheus-engine';

WITH source(
    component_code,component_kind,minimum_tech_level,
    unit_spaces,unit_cost_minor,heading_path
) AS (
    VALUES
        ('control.primitive','controls',1,0.5,0::bigint,'Vehicle Design > Vehicle Controls'),
        ('control.basic','controls',4,1,0,'Vehicle Design > Vehicle Controls'),
        ('control.advanced','controls',8,2,10000,'Vehicle Design > Vehicle Controls'),
        ('control.exo-skeleton','controls',10,3,100000,'Vehicle Design > Vehicle Controls'),
        ('control.neural-linked','controls',12,4,200000,'Vehicle Design > Vehicle Controls'),
        ('drone-controller.primitive','controls',5,0.5,10000,'Vehicle Design > Vehicle Controls'),
        ('drone-controller.basic','controls',7,1,50000,'Vehicle Design > Vehicle Controls'),
        ('drone-controller.advanced','controls',9,2,100000,'Vehicle Design > Vehicle Controls'),
        ('drone-controller.exo-skeleton','controls',11,3,200000,'Vehicle Design > Vehicle Controls'),
        ('drone-controller.neural-linked','controls',13,4,500000,'Vehicle Design > Vehicle Controls'),
        ('robot-brain.linear','computer',8,3,22500,'Vehicle Design > Vehicle Controls'),
        ('robot-brain.parallel','computer',10,2,40000,'Vehicle Design > Vehicle Controls'),
        ('robot-brain.synaptic','computer',12,1,90000,'Vehicle Design > Vehicle Controls'),
        ('communication.class-1','communications',5,0.01,500,'Vehicle Design > Vehicle Communication Systems'),
        ('communication.class-2','communications',5,0.02,1000,'Vehicle Design > Vehicle Communication Systems'),
        ('communication.class-3','communications',6,0.05,2000,'Vehicle Design > Vehicle Communication Systems'),
        ('communication.class-4','communications',8,0.10,4000,'Vehicle Design > Vehicle Communication Systems'),
        ('sensor.standard','sensors',8,3,5000,'Vehicle Design > Vehicle Sensors'),
        ('sensor.basic-civilian','sensors',9,6,10000,'Vehicle Design > Vehicle Sensors'),
        ('sensor.basic-military','sensors',10,12,20000,'Vehicle Design > Vehicle Sensors'),
        ('sensor.advanced','sensors',11,18,50000,'Vehicle Design > Vehicle Sensors'),
        ('sensor.very-advanced','sensors',12,30,100000,'Vehicle Design > Vehicle Sensors'),
        ('computer.model-0','computer',7,0.02,100,'Vehicle Design > Vehicle Computer'),
        ('computer.model-1','computer',8,0.01,500,'Vehicle Design > Vehicle Computer'),
        ('computer.model-2','computer',10,0,1000,'Vehicle Design > Vehicle Computer'),
        ('computer.model-3','computer',12,0,2000,'Vehicle Design > Vehicle Computer'),
        ('computer.model-4','computer',13,0,3000,'Vehicle Design > Vehicle Computer'),
        ('computer.model-5','computer',14,0,10000,'Vehicle Design > Vehicle Computer')
)
INSERT INTO vehicle_component_definition (
    component_rule_id,component_code,component_kind,
    minimum_tech_level,unit_spaces,unit_cost_minor,
    source_locator_id
)
SELECT rule.rule_id,source.component_code,source.component_kind,
       source.minimum_tech_level,source.unit_spaces,
       source.unit_cost_minor,locator.source_locator_id
FROM source
JOIN rule_rule rule
  ON rule.rule_code='vehicle.component.'||source.component_code
JOIN src_locator locator USING (heading_path);

CREATE TABLE rule_vehicle_control_system (
    component_rule_id bigint PRIMARY KEY REFERENCES
        vehicle_component_definition(component_rule_id),
    interface_code text NOT NULL UNIQUE CHECK (
        interface_code ~ '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
    ),
    interface_rank smallint NOT NULL UNIQUE CHECK (
        interface_rank BETWEEN 1 AND 5
    ),
    price_basis text NOT NULL CHECK (
        price_basis IN ('fixed','included','chassis_percent_adjustment')
    ),
    chassis_price_adjustment_percent numeric,
    agility_dm smallint NOT NULL,
    initiative_dm smallint NOT NULL,
    high_speed_dm smallint,
    high_speed_threshold_kph numeric,
    CHECK (
        (price_basis='chassis_percent_adjustment'
         AND chassis_price_adjustment_percent IS NOT NULL)
        OR
        (price_basis<>'chassis_percent_adjustment'
         AND chassis_price_adjustment_percent IS NULL)
    ),
    CHECK (
        (high_speed_dm IS NULL AND high_speed_threshold_kph IS NULL)
        OR
        (high_speed_dm IS NOT NULL AND high_speed_threshold_kph>0)
    )
);

INSERT INTO rule_vehicle_control_system
SELECT component.rule_id,source.*
FROM (
    VALUES
        ('primitive',1,'chassis_percent_adjustment',-20::numeric,-1,0,-2,50::numeric),
        ('basic',2,'included',NULL,0,0,NULL::smallint,NULL::numeric),
        ('advanced',3,'fixed',NULL,1,0,NULL,NULL),
        ('exo-skeleton',4,'fixed',NULL,1,1,NULL,NULL),
        ('neural-linked',5,'fixed',NULL,2,2,NULL,NULL)
) source(
    interface_code,interface_rank,price_basis,
    chassis_price_adjustment_percent,agility_dm,initiative_dm,
    high_speed_dm,high_speed_threshold_kph
)
JOIN rule_rule component
  ON component.rule_code='vehicle.component.control.'||
     source.interface_code;

CREATE TABLE rule_vehicle_drone_controller (
    component_rule_id bigint PRIMARY KEY REFERENCES
        vehicle_component_definition(component_rule_id),
    interface_code text NOT NULL UNIQUE REFERENCES
        rule_vehicle_control_system(interface_code),
    control_dm smallint NOT NULL,
    range_code text NOT NULL REFERENCES
        rule_vehicle_electronics_range(range_code)
);

INSERT INTO rule_vehicle_drone_controller
SELECT component.rule_id,source.interface_code,
       source.control_dm,source.range_code
FROM (
    VALUES
        ('primitive',-3,'long'),
        ('basic',-2,'very-long'),
        ('advanced',-1,'distant'),
        ('exo-skeleton',0,'very-distant'),
        ('neural-linked',1,'regional')
) source(interface_code,control_dm,range_code)
JOIN rule_rule component
  ON component.rule_code='vehicle.component.drone-controller.'||
     source.interface_code;

CREATE TABLE rule_vehicle_robot_brain (
    component_rule_id bigint PRIMARY KEY REFERENCES
        vehicle_component_definition(component_rule_id),
    cpu_code text NOT NULL UNIQUE,
    computer_model smallint NOT NULL CHECK (
        computer_model BETWEEN 0 AND 5
    ),
    maximum_skill_level smallint NOT NULL CHECK (
        maximum_skill_level BETWEEN 0 AND 3
    ),
    minimum_control_rank smallint NOT NULL DEFAULT 3 CHECK (
        minimum_control_rank BETWEEN 1 AND 5
    )
);

INSERT INTO rule_vehicle_robot_brain
SELECT component.rule_id,source.cpu_code,
       source.computer_model,source.maximum_skill_level,3
FROM (
    VALUES
        ('linear',1,1),('parallel',2,2),('synaptic',3,3)
) source(cpu_code,computer_model,maximum_skill_level)
JOIN rule_rule component
  ON component.rule_code='vehicle.component.robot-brain.'||
     source.cpu_code;

CREATE TABLE rule_vehicle_autopilot_formula (
    formula_code text PRIMARY KEY,
    base_skill_level smallint NOT NULL CHECK (base_skill_level>=0),
    tech_levels_per_skill_level smallint NOT NULL CHECK (
        tech_levels_per_skill_level>0
    ),
    maximum_skill_level smallint NOT NULL CHECK (
        maximum_skill_level>=base_skill_level
    ),
    base_price_minor bigint NOT NULL CHECK (base_price_minor>=0),
    price_per_skill_level_minor bigint NOT NULL CHECK (
        price_per_skill_level_minor>=0
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_vehicle_autopilot_formula
SELECT 'standard',0,2,3,2000,5000,locator.source_locator_id
FROM src_locator locator
WHERE locator.heading_path='Vehicle Design > Vehicle Controls';

CREATE TABLE rule_vehicle_autopilot_introduction (
    vehicle_category text PRIMARY KEY CHECK (
        vehicle_category IN ('aircraft','sea_vessel','ground_vehicle')
    ),
    minimum_tech_level smallint NOT NULL CHECK (minimum_tech_level>=0),
    formula_code text NOT NULL REFERENCES
        rule_vehicle_autopilot_formula(formula_code)
);

INSERT INTO rule_vehicle_autopilot_introduction VALUES
    ('aircraft',5,'standard'),('sea_vessel',5,'standard'),
    ('ground_vehicle',9,'standard');

CREATE TABLE rule_vehicle_communication_system (
    component_rule_id bigint PRIMARY KEY REFERENCES
        vehicle_component_definition(component_rule_id),
    communication_class smallint NOT NULL UNIQUE CHECK (
        communication_class BETWEEN 1 AND 4
    ),
    range_code text NOT NULL REFERENCES
        rule_vehicle_electronics_range(range_code)
);

INSERT INTO rule_vehicle_communication_system
SELECT component.rule_id,source.communication_class,
       source.range_code
FROM (
    VALUES
        (1,'distant'),(2,'very-distant'),
        (3,'regional'),(4,'continental')
) source(communication_class,range_code)
JOIN rule_rule component
  ON component.rule_code='vehicle.component.communication.class-'||
     source.communication_class::text;

CREATE TABLE rule_vehicle_communicator_type (
    communicator_type_code text PRIMARY KEY,
    communicator_type_name text NOT NULL UNIQUE,
    minimum_tech_level smallint NOT NULL CHECK (minimum_tech_level>=0),
    space_multiplier numeric NOT NULL CHECK (space_multiplier>0),
    price_multiplier numeric NOT NULL CHECK (price_multiplier>0),
    requires_clear_line_of_sight boolean NOT NULL,
    penetrates_smoke_aerosols boolean NOT NULL,
    cannot_be_jammed_or_blocked boolean NOT NULL,
    requires_stationary_vehicle boolean NOT NULL,
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_vehicle_communicator_type
SELECT source.*,locator.source_locator_id
FROM (
    VALUES
        ('laser','Laser',8,2,3,true,false,false,false),
        ('maser','Maser',10,4,6,true,true,false,false),
        ('meson','Meson',11,10,50,false,true,true,true)
) source(
    communicator_type_code,communicator_type_name,
    minimum_tech_level,space_multiplier,price_multiplier,
    requires_clear_line_of_sight,penetrates_smoke_aerosols,
    cannot_be_jammed_or_blocked,requires_stationary_vehicle
)
JOIN src_locator locator
  ON locator.heading_path=
     'Vehicle Design > Vehicle Communication Systems';

CREATE TABLE rule_vehicle_sensor_package (
    component_rule_id bigint PRIMARY KEY REFERENCES
        vehicle_component_definition(component_rule_id),
    sensor_code text NOT NULL UNIQUE,
    communications_dm smallint NOT NULL,
    range_code text NOT NULL REFERENCES
        rule_vehicle_electronics_range(range_code),
    published_range_text text NOT NULL CHECK (
        btrim(published_range_text)<>''
    )
);

INSERT INTO rule_vehicle_sensor_package
SELECT component.rule_id,source.sensor_code,
       source.communications_dm,source.range_code,
       source.published_range_text
FROM (
    VALUES
        ('standard',-4,'very-long','Very Long (500 km)'),
        ('basic-civilian',-2,'distant','Distant (5 km)'),
        ('basic-military',0,'very-distant','Very Distant (50 km)'),
        ('advanced',1,'regional','Regional (500 km)'),
        ('very-advanced',2,'continental','Continental (5000 km)')
) source(
    sensor_code,communications_dm,range_code,
    published_range_text
)
JOIN rule_rule component
  ON component.rule_code='vehicle.component.sensor.'||
     source.sensor_code;

CREATE TABLE rule_vehicle_underwater_sensor_conversion (
    conversion_code text PRIMARY KEY,
    separate_purchase_required boolean NOT NULL,
    surface_underwater_incompatible boolean NOT NULL,
    additional_spaces numeric NOT NULL CHECK (additional_spaces>=0),
    range_steps_reduced smallint NOT NULL CHECK (range_steps_reduced>=0),
    minimum_range_code text NOT NULL REFERENCES
        rule_vehicle_electronics_range(range_code),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_vehicle_underwater_sensor_conversion
SELECT 'standard',true,true,12,1,'very-long',
       locator.source_locator_id
FROM src_locator locator
WHERE locator.heading_path='Vehicle Design > Vehicle Sensors';

CREATE TABLE rule_vehicle_sensor_capability (
    capability_code text PRIMARY KEY,
    capability_name text NOT NULL UNIQUE,
    capability_description text NOT NULL CHECK (
        btrim(capability_description)<>''
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_vehicle_sensor_capability
SELECT source.*,locator.source_locator_id
FROM (
    VALUES
        ('radar','Radar','Detects physical objects actively or passively.'),
        ('lidar','Lidar','Detects physical objects actively or passively.'),
        ('jammers','Jammers','Jams or counter-jams communications and sensor locks.'),
        ('densitometer','Densitometer','Determines the internal structure and makeup of an object.'),
        ('neural-activity','Neural Activity Sensor','Detects neural activity and intelligence.')
) source(capability_code,capability_name,capability_description)
JOIN src_locator locator
  ON locator.heading_path='Vehicle Design > Vehicle Sensors';

CREATE TABLE rule_vehicle_sensor_package_capability (
    component_rule_id bigint NOT NULL REFERENCES
        rule_vehicle_sensor_package(component_rule_id),
    capability_code text NOT NULL REFERENCES
        rule_vehicle_sensor_capability(capability_code),
    PRIMARY KEY (component_rule_id,capability_code)
);

INSERT INTO rule_vehicle_sensor_package_capability
SELECT package.component_rule_id,capability.capability_code
FROM (
    VALUES
        ('standard','radar'),('standard','lidar'),
        ('basic-civilian','radar'),('basic-civilian','lidar'),
        ('basic-military','radar'),('basic-military','lidar'),
        ('basic-military','jammers'),
        ('advanced','radar'),('advanced','lidar'),
        ('advanced','densitometer'),('advanced','jammers'),
        ('very-advanced','radar'),('very-advanced','lidar'),
        ('very-advanced','densitometer'),('very-advanced','jammers'),
        ('very-advanced','neural-activity')
) source(sensor_code,capability_code)
JOIN rule_vehicle_sensor_package package
  ON package.sensor_code=source.sensor_code
JOIN rule_vehicle_sensor_capability capability
  ON capability.capability_code=source.capability_code;

CREATE TABLE rule_vehicle_computer (
    component_rule_id bigint PRIMARY KEY REFERENCES
        vehicle_component_definition(component_rule_id),
    model_number smallint NOT NULL UNIQUE CHECK (
        model_number BETWEEN 0 AND 5
    ),
    computer_rating smallint NOT NULL CHECK (
        computer_rating=model_number
    ),
    program_capacity smallint NOT NULL CHECK (
        program_capacity=greatest(model_number,1)
    )
);

INSERT INTO rule_vehicle_computer
SELECT component.rule_id,source.model_number,
       source.model_number,greatest(source.model_number,1)
FROM generate_series(0,5) source(model_number)
JOIN rule_rule component
  ON component.rule_code='vehicle.component.computer.model-'||
     source.model_number::text;

CREATE TABLE rule_vehicle_computer_option (
    option_code text PRIMARY KEY,
    option_name text NOT NULL UNIQUE,
    price_multiplier numeric NOT NULL CHECK (price_multiplier>0),
    electromagnetic_pulse_immune boolean NOT NULL,
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_vehicle_computer_option
SELECT 'hardened','Hardened Systems (fib)',1.5,true,
       locator.source_locator_id
FROM src_locator locator
WHERE locator.heading_path='Vehicle Design > Vehicle Computer';

INSERT INTO src_record_provenance (
    rule_id,content_package_id,source_locator_id,
    provenance_class,is_primary_citation
)
SELECT rule.rule_id,rule.content_package_id,
       component.source_locator_id,'direct',true
FROM rule_rule rule
JOIN vehicle_component_definition component
  ON component.component_rule_id=rule.rule_id
WHERE rule.rule_code LIKE 'vehicle.component.%';

INSERT INTO src_issue (
    issue_code,domain_code,issue_type,review_priority,
    subject_code,title,problem_statement,
    published_value,calculated_value,
    reviewer_question,requested_evidence,engine_disposition
)
SELECT source.issue_code,'vehicle.catalogue','source_conflict','high',
       source.subject_code,source.title,source.problem_statement,
       source.published_value,source.calculated_value,
       source.reviewer_question,
       'A corrected printing, publisher errata, or a corroborating authorized source with an explicit replacement value.',
       source.engine_disposition
FROM (
    VALUES
        (
            'vehicle.controls.primitive-tech-level',
            'primitive-controls',
            'Primitive Controls tech-level conflict',
            'The descriptive paragraph states TL2, while the Vehicle Control Systems table states TL1.',
            'Prose TL2; table TL1','TL1 table value',
            'Should Primitive Controls have a minimum tech level of 1 or 2?',
            'preserve_published'
        ),
        (
            'vehicle.sensors.standard-range-distance',
            'standard-sensors',
            'Standard Sensors range-distance conflict',
            'The Standard Sensors row prints Very Long as 500 km, while the electronics range progression and underwater-sensor minimum identify Very Long as 500 m.',
            'Very Long (500 km)','Very Long (500 m)',
            'Is the Standard Sensors distance meant to be 500 metres rather than 500 kilometres?',
            'preserve_rule'
        )
) source(
    issue_code,subject_code,title,problem_statement,
    published_value,calculated_value,reviewer_question,
    engine_disposition
);

INSERT INTO src_issue_locator (
    source_issue_id,source_locator_id,evidence_role
)
SELECT issue.source_issue_id,locator.source_locator_id,'primary'
FROM src_issue issue
JOIN (
    VALUES
        ('vehicle.controls.primitive-tech-level',
         'Vehicle Design > Vehicle Controls'),
        ('vehicle.sensors.standard-range-distance',
         'Vehicle Design > Vehicle Sensors')
) source(issue_code,heading_path)
  ON source.issue_code=issue.issue_code
JOIN src_locator locator USING (heading_path);
