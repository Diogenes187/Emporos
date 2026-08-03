INSERT INTO src_locator (
    source_work_id,source_artifact_id,locator_type,
    heading_path,display_citation
)
SELECT artifact.source_work_id,artifact.source_artifact_id,
       'heading',source.heading_path,source.display_citation
FROM src_artifact artifact
CROSS JOIN (
    VALUES
        ('Vehicle Design > Special Rules for Vehicles > Alien Vehicles',
         'Cepheus Engine VDS, Alien Vehicles'),
        ('Vehicle Design > Special Rules for Vehicles > Airship/Balloon Lift Envelope',
         'Cepheus Engine VDS, Airship/Balloon Lift Envelope'),
        ('Vehicle Design > Special Rules for Vehicles > Atmospheres and Aircraft',
         'Cepheus Engine VDS, Atmospheres and Aircraft'),
        ('Vehicle Design > Special Rules for Vehicles > Missile and Torpedo Attacks',
         'Cepheus Engine VDS, Missile and Torpedo Attacks'),
        ('Vehicle Design > Special Rules for Vehicles > Non-Powered Vehicles',
         'Cepheus Engine VDS, Non-Powered Vehicles'),
        ('Vehicle Design > Special Rules for Vehicles > Off-Road Movement for Ground Vehicles',
         'Cepheus Engine VDS, Off-Road Movement')
) source(heading_path,display_citation)
WHERE artifact.source_uri='src/vds/vehicle-design.md';

WITH source(rule_code,rule_name) AS (
    VALUES
        ('vehicle.special.alien-design',
         'Alien Vehicle Design Assumption'),
        ('vehicle.special.lift-envelope',
         'Airship and Balloon Lift Envelope'),
        ('vehicle.special.aircraft-environment',
         'Aircraft Operational Environment'),
        ('vehicle.special.aircraft-environment.extended',
         'Extended Aircraft Operational Environment'),
        ('vehicle.special.missile-torpedo-attack',
         'Missile and Torpedo Attack'),
        ('vehicle.special.animal-powered',
         'Animal-Powered Vehicle'),
        ('vehicle.special.wind-powered',
         'Wind-Powered Vehicle'),
        ('vehicle.special.off-road-standard',
         'Standard Off-Road Movement'),
        ('vehicle.special.off-road-capable',
         'Off-Road Capable Movement')
)
INSERT INTO rule_rule (
    content_package_id,rule_code,name,rule_category,rule_status
)
SELECT package.content_package_id,source.rule_code,
       source.rule_name,'vehicle','approved'
FROM source
CROSS JOIN sys_content_package package
WHERE package.package_code='cepheus-engine';

CREATE TABLE rule_vehicle_alien_design_assumption (
    assumption_rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    assumes_humanlike_physiology boolean NOT NULL,
    accommodation_exceptions_allowed boolean NOT NULL,
    referee_is_final_arbiter boolean NOT NULL,
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_vehicle_alien_design_assumption
SELECT rule.rule_id,true,true,true,locator.source_locator_id
FROM rule_rule rule
JOIN src_locator locator
  ON locator.heading_path=
     'Vehicle Design > Special Rules for Vehicles > Alien Vehicles'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1'
WHERE rule.rule_code='vehicle.special.alien-design';

CREATE TABLE rule_vehicle_lift_envelope (
    lift_envelope_rule_id bigint PRIMARY KEY REFERENCES
        rule_rule(rule_id),
    stored_size_fraction numeric NOT NULL CHECK (
        stored_size_fraction>0 AND stored_size_fraction<1
    ),
    structure_spaces_per_point numeric NOT NULL CHECK (
        structure_spaces_per_point>0
    ),
    non_explosive_hit_damage smallint NOT NULL CHECK (
        non_explosive_hit_damage>0
    ),
    automatic_hit_damage_basis text NOT NULL CHECK (
        automatic_hit_damage_basis='weapon-automatic-rating'
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_vehicle_lift_envelope
SELECT rule.rule_id,0.01,60,1,'weapon-automatic-rating',
       locator.source_locator_id
FROM rule_rule rule
JOIN src_locator locator
  ON locator.heading_path=
     'Vehicle Design > Special Rules for Vehicles > Airship/Balloon Lift Envelope'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1'
WHERE rule.rule_code='vehicle.special.lift-envelope';

CREATE TABLE rule_vehicle_lift_medium (
    lift_medium_code text PRIMARY KEY CHECK (
        lift_medium_code IN ('hydrogen','helium','hot-air')
    ),
    lift_medium_name text NOT NULL UNIQUE,
    duration_basis text NOT NULL CHECK (
        duration_basis IN ('indefinite','tech-level-hours')
    ),
    duration_hours_per_tech_level numeric CHECK (
        duration_hours_per_tech_level>0
    ),
    envelope_multiplier_class text NOT NULL CHECK (
        envelope_multiplier_class IN ('light-gas','hot-air')
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    CHECK (
        (duration_basis='indefinite'
         AND duration_hours_per_tech_level IS NULL)
        OR
        (duration_basis='tech-level-hours'
         AND duration_hours_per_tech_level IS NOT NULL)
    )
);

INSERT INTO rule_vehicle_lift_medium
SELECT source.*,locator.source_locator_id
FROM (
    VALUES
        ('hydrogen','Hydrogen','indefinite',
         NULL::numeric,'light-gas'),
        ('helium','Helium','indefinite',NULL,'light-gas'),
        ('hot-air','Hot Air','tech-level-hours',2,'hot-air')
) source(
    lift_medium_code,lift_medium_name,duration_basis,
    duration_hours_per_tech_level,envelope_multiplier_class
)
JOIN src_locator locator
  ON locator.heading_path=
     'Vehicle Design > Special Rules for Vehicles > Airship/Balloon Lift Envelope'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1';

CREATE TABLE rule_vehicle_lift_envelope_atmosphere (
    atmosphere_density_code text PRIMARY KEY CHECK (
        atmosphere_density_code IN (
            'very-thin','thin','standard','dense'
        )
    ),
    atmosphere_density_name text NOT NULL UNIQUE,
    display_order smallint NOT NULL UNIQUE CHECK (display_order>0),
    light_gas_size_multiplier numeric NOT NULL CHECK (
        light_gas_size_multiplier>0
    ),
    hot_air_size_multiplier numeric NOT NULL CHECK (
        hot_air_size_multiplier>0
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_vehicle_lift_envelope_atmosphere
SELECT source.*,locator.source_locator_id
FROM (
    VALUES
        ('very-thin','Very Thin',1::smallint,100::numeric,200::numeric),
        ('thin','Thin',2,25,50),
        ('standard','Standard',3,10,20),
        ('dense','Dense',4,5,10)
) source(
    atmosphere_density_code,atmosphere_density_name,
    display_order,light_gas_size_multiplier,
    hot_air_size_multiplier
)
JOIN src_locator locator
  ON locator.heading_path=
     'Vehicle Design > Special Rules for Vehicles > Airship/Balloon Lift Envelope'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1';

CREATE TABLE rule_vehicle_aircraft_environment (
    environment_rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    environment_code text NOT NULL UNIQUE CHECK (
        environment_code IN ('standard','extended')
    ),
    exact_match_maximum_code_difference smallint NOT NULL CHECK (
        exact_match_maximum_code_difference>=0
    ),
    operational_maximum_code_difference smallint NOT NULL CHECK (
        operational_maximum_code_difference>=
        exact_match_maximum_code_difference
    ),
    degraded_agility_dm smallint NOT NULL CHECK (
        degraded_agility_dm<0
    ),
    degraded_in_all_environments boolean NOT NULL,
    minimum_atmosphere_code smallint NOT NULL CHECK (
        minimum_atmosphere_code>=0
    ),
    additional_base_price_multiplier numeric NOT NULL CHECK (
        additional_base_price_multiplier>=0
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

WITH source(
    rule_code,environment_code,exact_difference,
    operational_difference,degraded_dm,degraded_everywhere,
    minimum_atmosphere,price_multiplier
) AS (
    VALUES
        ('vehicle.special.aircraft-environment','standard',
         0::smallint,1::smallint,-1::smallint,false,
         1::smallint,0::numeric),
        ('vehicle.special.aircraft-environment.extended','extended',
         0,2,-1,true,1,1)
)
INSERT INTO rule_vehicle_aircraft_environment
SELECT rule.rule_id,source.environment_code,
       source.exact_difference,source.operational_difference,
       source.degraded_dm,source.degraded_everywhere,
       source.minimum_atmosphere,source.price_multiplier,
       locator.source_locator_id
FROM source
JOIN rule_rule rule USING (rule_code)
JOIN src_locator locator
  ON locator.heading_path=
     'Vehicle Design > Special Rules for Vehicles > Atmospheres and Aircraft'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1';

CREATE TABLE rule_vehicle_missile_impact_time (
    target_range_code text PRIMARY KEY REFERENCES
        rule_vehicle_weapon_target_range(target_range_code),
    attack_permitted boolean NOT NULL,
    turns_to_impact smallint CHECK (turns_to_impact>=0),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    CHECK (
        (attack_permitted AND turns_to_impact IS NOT NULL)
        OR
        (NOT attack_permitted AND turns_to_impact IS NULL)
    )
);

INSERT INTO rule_vehicle_missile_impact_time
SELECT source.target_range_code,source.attack_permitted,
       source.turns_to_impact,locator.source_locator_id
FROM (
    VALUES
        ('personal',false,NULL::smallint),
        ('close',false,NULL),
        ('short',true,0),
        ('medium',true,0),
        ('long',true,0),
        ('very-long',true,0),
        ('distant',true,1),
        ('very-distant',true,4),
        ('extreme',true,8)
) source(target_range_code,attack_permitted,turns_to_impact)
JOIN src_locator locator
  ON locator.heading_path=
     'Vehicle Design > Special Rules for Vehicles > Missile and Torpedo Attacks'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1';

CREATE TABLE rule_vehicle_missile_launch_skill (
    attack_rule_id bigint NOT NULL REFERENCES rule_rule(rule_id),
    skill_rule_id bigint NOT NULL REFERENCES rule_skill(rule_id),
    PRIMARY KEY (attack_rule_id,skill_rule_id)
);

INSERT INTO rule_vehicle_missile_launch_skill
SELECT attack.rule_id,skill.rule_id
FROM rule_rule attack
JOIN rule_rule skill
  ON skill.rule_code IN (
      'skill.turret-weapons','skill.bay-weapons'
  )
WHERE attack.rule_code=
      'vehicle.special.missile-torpedo-attack';

CREATE TABLE rule_vehicle_missile_launch_effect (
    attack_rule_id bigint NOT NULL REFERENCES rule_rule(rule_id),
    effect_minimum smallint,
    effect_maximum smallint,
    skill_check_succeeded boolean NOT NULL,
    missile_target_number smallint NOT NULL CHECK (
        missile_target_number>0
    ),
    display_order smallint NOT NULL CHECK (display_order>0),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    PRIMARY KEY (attack_rule_id,display_order),
    CHECK (
        effect_minimum IS NULL
        OR effect_maximum IS NULL
        OR effect_minimum<=effect_maximum
    )
);

INSERT INTO rule_vehicle_missile_launch_effect
SELECT attack.rule_id,source.effect_minimum,
       source.effect_maximum,source.succeeded,
       source.target_number,source.display_order,
       locator.source_locator_id
FROM (
    VALUES
        (NULL::smallint,-6::smallint,false,11::smallint,1::smallint),
        (-5,-1,false,10,2),
        (0,0,true,8,3),
        (1,5,true,7,4),
        (6,NULL,true,6,5)
) source(
    effect_minimum,effect_maximum,succeeded,
    target_number,display_order
)
JOIN rule_rule attack
  ON attack.rule_code=
     'vehicle.special.missile-torpedo-attack'
JOIN src_locator locator
  ON locator.heading_path=
     'Vehicle Design > Special Rules for Vehicles > Missile and Torpedo Attacks'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1';

CREATE TABLE rule_vehicle_animal_power (
    animal_power_rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    strength_required_per_chassis_space numeric NOT NULL CHECK (
        strength_required_per_chassis_space>0
    ),
    rail_strength_divisor numeric NOT NULL CHECK (
        rail_strength_divisor>0
    ),
    strength_deficit_per_reduction_step numeric NOT NULL CHECK (
        strength_deficit_per_reduction_step>0
    ),
    speed_and_range_reduction_per_step numeric NOT NULL CHECK (
        speed_and_range_reduction_per_step>0
        AND speed_and_range_reduction_per_step<=1
    ),
    minimum_speed_fraction numeric NOT NULL CHECK (
        minimum_speed_fraction>=0
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_vehicle_animal_power
SELECT rule.rule_id,1,2,5,0.1,0,locator.source_locator_id
FROM rule_rule rule
JOIN src_locator locator
  ON locator.heading_path=
     'Vehicle Design > Special Rules for Vehicles > Non-Powered Vehicles'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1'
WHERE rule.rule_code='vehicle.special.animal-powered';

CREATE TABLE rule_vehicle_animal_gait (
    gait_code text PRIMARY KEY CHECK (
        gait_code IN ('walk','trot','canter','run')
    ),
    gait_name text NOT NULL UNIQUE,
    speed_multiplier numeric NOT NULL CHECK (speed_multiplier>0),
    endurance_minutes_multiplier numeric NOT NULL CHECK (
        endurance_minutes_multiplier>0
    ),
    display_order smallint NOT NULL UNIQUE CHECK (display_order>0),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_vehicle_animal_gait
SELECT source.*,locator.source_locator_id
FROM (
    VALUES
        ('walk','Walk',1::numeric,30::numeric,1::smallint),
        ('trot','Trot',2,15,2),
        ('canter','Canter',3,2,3),
        ('run','Run',4,1,4)
) source(
    gait_code,gait_name,speed_multiplier,
    endurance_minutes_multiplier,display_order
)
JOIN src_locator locator
  ON locator.heading_path=
     'Vehicle Design > Special Rules for Vehicles > Non-Powered Vehicles'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1';

CREATE TABLE rule_vehicle_draft_animal_profile (
    animal_code text PRIMARY KEY CHECK (
        animal_code ~
        '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
    ),
    animal_name text NOT NULL UNIQUE,
    strength smallint NOT NULL CHECK (strength>0),
    walk_speed_kph numeric NOT NULL CHECK (walk_speed_kph>0),
    run_speed_kph numeric NOT NULL CHECK (run_speed_kph>0),
    endurance smallint NOT NULL CHECK (endurance>0),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    CHECK (run_speed_kph>=walk_speed_kph)
);

INSERT INTO rule_vehicle_draft_animal_profile
SELECT source.*,locator.source_locator_id
FROM (
    VALUES
        ('elephant','Elephant',24::smallint,6::numeric,24::numeric,15::smallint),
        ('horse','Horse',10,7,28,12),
        ('human','Human',7,6,24,7),
        ('mule','Mule',11,6,24,14),
        ('ox','Ox',18,5,20,18)
) source(
    animal_code,animal_name,strength,walk_speed_kph,
    run_speed_kph,endurance
)
JOIN src_locator locator
  ON locator.heading_path=
     'Vehicle Design > Special Rules for Vehicles > Non-Powered Vehicles'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1';

CREATE TABLE rule_vehicle_wind_sailing_speed (
    wind_power_rule_id bigint NOT NULL REFERENCES rule_rule(rule_id),
    vehicle_medium_code text NOT NULL CHECK (
        vehicle_medium_code IN ('air','ground','water')
    ),
    under_ten_tons_speed_fraction numeric NOT NULL CHECK (
        under_ten_tons_speed_fraction>0
        AND under_ten_tons_speed_fraction<=1
    ),
    ten_tons_or_more_speed_fraction numeric NOT NULL CHECK (
        ten_tons_or_more_speed_fraction>0
        AND ten_tons_or_more_speed_fraction<=1
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    PRIMARY KEY (wind_power_rule_id,vehicle_medium_code)
);

INSERT INTO rule_vehicle_wind_sailing_speed
SELECT rule.rule_id,source.vehicle_medium_code,
       source.under_ten_tons,source.ten_tons_or_more,
       locator.source_locator_id
FROM (
    VALUES
        ('air',0.35::numeric,0.4::numeric),
        ('ground',0.2,0.15),
        ('water',0.2,0.3)
) source(
    vehicle_medium_code,under_ten_tons,ten_tons_or_more
)
JOIN rule_rule rule
  ON rule.rule_code='vehicle.special.wind-powered'
JOIN src_locator locator
  ON locator.heading_path=
     'Vehicle Design > Special Rules for Vehicles > Non-Powered Vehicles'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1';

CREATE TABLE rule_vehicle_off_road_movement (
    movement_rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    off_road_capable boolean NOT NULL UNIQUE,
    normal_off_road_agility_dm smallint NOT NULL,
    normal_off_road_speed_fraction numeric NOT NULL CHECK (
        normal_off_road_speed_fraction>0
        AND normal_off_road_speed_fraction<=1
    ),
    rough_terrain_permitted boolean NOT NULL,
    rough_terrain_agility_dm smallint,
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    CHECK (
        (rough_terrain_permitted
         AND rough_terrain_agility_dm IS NOT NULL)
        OR
        (NOT rough_terrain_permitted
         AND rough_terrain_agility_dm IS NULL)
    )
);

WITH source(
    rule_code,off_road_capable,normal_dm,speed_fraction,
    rough_permitted,rough_dm
) AS (
    VALUES
        ('vehicle.special.off-road-standard',false,
         -2::smallint,0.25::numeric,false,NULL::smallint),
        ('vehicle.special.off-road-capable',true,
         0,1,true,-2)
)
INSERT INTO rule_vehicle_off_road_movement
SELECT rule.rule_id,source.off_road_capable,
       source.normal_dm,source.speed_fraction,
       source.rough_permitted,source.rough_dm,
       locator.source_locator_id
FROM source
JOIN rule_rule rule USING (rule_code)
JOIN src_locator locator
  ON locator.heading_path=
     'Vehicle Design > Special Rules for Vehicles > Off-Road Movement for Ground Vehicles'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1';

INSERT INTO src_record_provenance (
    rule_id,content_package_id,source_locator_id,
    provenance_class,is_primary_citation
)
SELECT rule.rule_id,rule.content_package_id,
       CASE
           WHEN rule.rule_code='vehicle.special.alien-design'
               THEN alien_locator.source_locator_id
           WHEN rule.rule_code='vehicle.special.lift-envelope'
               THEN lift_locator.source_locator_id
           WHEN rule.rule_code LIKE
                'vehicle.special.aircraft-environment%'
               THEN aircraft_locator.source_locator_id
           WHEN rule.rule_code=
                'vehicle.special.missile-torpedo-attack'
               THEN missile_locator.source_locator_id
           WHEN rule.rule_code IN (
                'vehicle.special.animal-powered',
                'vehicle.special.wind-powered'
           )
               THEN power_locator.source_locator_id
           ELSE off_road_locator.source_locator_id
       END,
       'direct',true
FROM rule_rule rule
JOIN src_work work
  ON work.work_code='cepheus-engine.github-v9.1'
LEFT JOIN src_locator alien_locator
  ON alien_locator.source_work_id=work.source_work_id
 AND alien_locator.heading_path=
     'Vehicle Design > Special Rules for Vehicles > Alien Vehicles'
LEFT JOIN src_locator lift_locator
  ON lift_locator.source_work_id=work.source_work_id
 AND lift_locator.heading_path=
     'Vehicle Design > Special Rules for Vehicles > Airship/Balloon Lift Envelope'
LEFT JOIN src_locator aircraft_locator
  ON aircraft_locator.source_work_id=work.source_work_id
 AND aircraft_locator.heading_path=
     'Vehicle Design > Special Rules for Vehicles > Atmospheres and Aircraft'
LEFT JOIN src_locator missile_locator
  ON missile_locator.source_work_id=work.source_work_id
 AND missile_locator.heading_path=
     'Vehicle Design > Special Rules for Vehicles > Missile and Torpedo Attacks'
LEFT JOIN src_locator power_locator
  ON power_locator.source_work_id=work.source_work_id
 AND power_locator.heading_path=
     'Vehicle Design > Special Rules for Vehicles > Non-Powered Vehicles'
LEFT JOIN src_locator off_road_locator
  ON off_road_locator.source_work_id=work.source_work_id
 AND off_road_locator.heading_path=
     'Vehicle Design > Special Rules for Vehicles > Off-Road Movement for Ground Vehicles'
WHERE rule.rule_code LIKE 'vehicle.special.%';

INSERT INTO src_issue (
    issue_code,domain_code,issue_type,review_priority,
    subject_code,title,problem_statement,
    published_value,calculated_value,
    reviewer_question,requested_evidence,engine_disposition
)
VALUES (
    'vehicle.aircraft.environment-tolerance-wording',
    'vehicle.catalogue','source_conflict','medium',
    'aircraft-operational-environment',
    'Aircraft environment tolerance gives overlapping normal and penalized ranges',
    'The rule first says aircraft work properly within one UWP size and atmosphere code, then says aircraft within one code suffer Agility DM -1 and aircraft beyond that cannot fly.',
    'Within one code: both proper operation and Agility DM -1',
    'Exact match operates normally; difference of one applies DM -1',
    'Should an aircraft suffer the Agility penalty only when either design code differs by exactly one?',
    'A corrected printing, publisher errata, or another authorized aircraft-environment rule defining the intended boundary.',
    'preserve_rule'
);

INSERT INTO src_issue_locator (
    source_issue_id,source_locator_id,evidence_role
)
SELECT issue.source_issue_id,locator.source_locator_id,'primary'
FROM src_issue issue
JOIN src_locator locator
  ON locator.heading_path=
     'Vehicle Design > Special Rules for Vehicles > Atmospheres and Aircraft'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1'
WHERE issue.issue_code=
      'vehicle.aircraft.environment-tolerance-wording';
