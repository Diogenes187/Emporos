INSERT INTO src_locator (
    source_work_id,source_artifact_id,locator_type,
    heading_path,display_citation
)
SELECT artifact.source_work_id,artifact.source_artifact_id,
       'heading',source.heading_path,source.display_citation
FROM src_artifact artifact
CROSS JOIN (
    VALUES
        (
            'Personal Combat > Vehicles in Personal Combat > Vehicle Damage',
            'Cepheus Engine, Vehicle Damage'
        ),
        (
            'Personal Combat > Vehicles in Personal Combat > Vehicle Damage > Vehicle Hit Location',
            'Cepheus Engine, Vehicle Hit Location'
        ),
        (
            'Personal Combat > Vehicles in Personal Combat > Repairs',
            'Cepheus Engine, Vehicle Repairs'
        ),
        (
            'Personal Combat > Vehicles in Personal Combat > Repairs > System Damage',
            'Cepheus Engine, Vehicle System Damage Repair'
        ),
        (
            'Personal Combat > Vehicles in Personal Combat > Repairs > Hull Damage',
            'Cepheus Engine, Vehicle Hull Damage Repair'
        ),
        (
            'Personal Combat > Vehicles in Personal Combat > Repairs > Structure Damage',
            'Cepheus Engine, Vehicle Structure Damage Repair'
        )
) source(heading_path,display_citation)
WHERE artifact.source_uri='src/book1/personal-combat.md';

WITH source(rule_code,rule_name) AS (
    VALUES
        ('vehicle.damage.procedure','Vehicle Damage Procedure'),
        ('vehicle.damage.hit-location','Vehicle Hit Location'),
        ('vehicle.repair.system','Vehicle System Damage Repair'),
        ('vehicle.repair.hull','Vehicle Hull Damage Repair'),
        ('vehicle.repair.structure','Vehicle Structure Damage Repair')
)
INSERT INTO rule_rule (
    content_package_id,rule_code,name,rule_category,rule_status
)
SELECT package.content_package_id,source.rule_code,
       source.rule_name,'vehicle','approved'
FROM source
CROSS JOIN sys_content_package package
WHERE package.package_code='cepheus-engine';

CREATE TABLE rule_vehicle_damage_procedure (
    damage_rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    armor_reduces_damage boolean NOT NULL,
    damage_converts_to_location_hits boolean NOT NULL,
    hull_exhaustion_exposes_internal_systems boolean NOT NULL,
    structure_zero_destroys_vehicle boolean NOT NULL,
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_vehicle_damage_procedure
SELECT rule.rule_id,true,true,true,true,locator.source_locator_id
FROM rule_rule rule
JOIN src_locator locator
  ON locator.heading_path=
     'Personal Combat > Vehicles in Personal Combat > Vehicle Damage'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1'
WHERE rule.rule_code='vehicle.damage.procedure';

CREATE TABLE rule_vehicle_damage_band (
    damage_band_code text PRIMARY KEY CHECK (
        damage_band_code ~
        '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
    ),
    minimum_damage integer,
    maximum_damage integer,
    display_order smallint NOT NULL UNIQUE CHECK (
        display_order>0
    ),
    damage_range int4range GENERATED ALWAYS AS (
        int4range(
            minimum_damage,
            CASE
                WHEN maximum_damage IS NULL THEN NULL
                ELSE maximum_damage+1
            END,
            '[)'
        )
    ) STORED,
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    CHECK (
        minimum_damage IS NOT NULL OR maximum_damage IS NOT NULL
    ),
    CHECK (
        minimum_damage IS NULL OR maximum_damage IS NULL
        OR minimum_damage<=maximum_damage
    ),
    EXCLUDE USING gist (damage_range WITH &&)
);

INSERT INTO rule_vehicle_damage_band (
    damage_band_code,minimum_damage,maximum_damage,
    display_order,source_locator_id
)
SELECT source.*,locator.source_locator_id
FROM (
    VALUES
        ('none',NULL::integer,0::integer,1::smallint),
        ('damage-01-03',1,3,2),
        ('damage-04-06',4,6,3),
        ('damage-07-09',7,9,4),
        ('damage-10-12',10,12,5),
        ('damage-13-15',13,15,6),
        ('damage-16-18',16,18,7),
        ('damage-19-21',19,21,8),
        ('damage-22-24',22,24,9),
        ('damage-25-27',25,27,10),
        ('damage-28-30',28,30,11),
        ('damage-31-33',31,33,12)
) source(
    damage_band_code,minimum_damage,maximum_damage,display_order
)
JOIN src_locator locator
  ON locator.heading_path=
     'Personal Combat > Vehicles in Personal Combat > Vehicle Damage'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1';

CREATE TABLE rule_vehicle_damage_band_packet (
    damage_band_code text NOT NULL REFERENCES
        rule_vehicle_damage_band(damage_band_code),
    packet_order smallint NOT NULL CHECK (packet_order>0),
    location_hit_count smallint NOT NULL CHECK (
        location_hit_count BETWEEN 1 AND 3
    ),
    packet_quantity smallint NOT NULL CHECK (packet_quantity>0),
    PRIMARY KEY (damage_band_code,packet_order)
);

INSERT INTO rule_vehicle_damage_band_packet
VALUES
    ('damage-01-03',1,1,1),
    ('damage-04-06',1,1,2),
    ('damage-07-09',1,2,1),
    ('damage-10-12',1,1,3),
    ('damage-13-15',1,1,2),
    ('damage-13-15',2,2,1),
    ('damage-16-18',1,2,2),
    ('damage-19-21',1,3,1),
    ('damage-22-24',1,3,1),
    ('damage-22-24',2,1,1),
    ('damage-25-27',1,3,1),
    ('damage-25-27',2,2,1),
    ('damage-28-30',1,3,1),
    ('damage-28-30',2,2,1),
    ('damage-28-30',3,1,1),
    ('damage-31-33',1,3,2);

CREATE TABLE rule_vehicle_excess_damage_packet (
    damage_increment smallint PRIMARY KEY CHECK (
        damage_increment IN (3,6)
    ),
    location_hit_count smallint NOT NULL CHECK (
        location_hit_count IN (1,2)
    ),
    packet_quantity_per_increment smallint NOT NULL CHECK (
        packet_quantity_per_increment>0
    ),
    cumulative_with_other_increments boolean NOT NULL,
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_vehicle_excess_damage_packet
SELECT source.*,locator.source_locator_id
FROM (
    VALUES
        (3::smallint,1::smallint,1::smallint,true),
        (6::smallint,2::smallint,1::smallint,true)
) source(
    damage_increment,location_hit_count,
    packet_quantity_per_increment,cumulative_with_other_increments
)
JOIN src_locator locator
  ON locator.heading_path=
     'Personal Combat > Vehicles in Personal Combat > Vehicle Damage'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1';

CREATE TABLE rule_vehicle_hit_location (
    location_code text PRIMARY KEY CHECK (
        location_code IN (
            'hull','structure','armor','drive','weapon',
            'sensors','power-plant','limb','passengers',
            'cargo','cockpit','computer'
        )
    ),
    location_kind text NOT NULL CHECK (
        location_kind IN (
            'integrity','protection','system','occupant','cargo'
        )
    ),
    direct_hull_loss smallint NOT NULL DEFAULT 0 CHECK (
        direct_hull_loss>=0
    ),
    direct_structure_loss smallint NOT NULL DEFAULT 0 CHECK (
        direct_structure_loss>=0
    ),
    direct_armor_loss smallint NOT NULL DEFAULT 0 CHECK (
        direct_armor_loss>=0
    ),
    receives_vehicle_damage_amount boolean NOT NULL DEFAULT false,
    cargo_is_at_risk boolean NOT NULL DEFAULT false,
    maximum_staged_hits smallint CHECK (maximum_staged_hits>0),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    CHECK (
        num_nonnulls(maximum_staged_hits)=
        CASE WHEN location_kind='system' THEN 1 ELSE 0 END
    )
);

INSERT INTO rule_vehicle_hit_location
SELECT source.*,locator.source_locator_id
FROM (
    VALUES
        ('hull','integrity',1,0,0,false,false,NULL::smallint),
        ('structure','integrity',0,1,0,false,false,NULL),
        ('armor','protection',0,0,1,false,false,NULL),
        ('drive','system',0,0,0,false,false,3),
        ('weapon','system',0,0,0,false,false,2),
        ('sensors','system',0,0,0,false,false,2),
        ('power-plant','system',0,0,0,false,false,3),
        ('limb','system',0,0,0,false,false,2),
        ('passengers','occupant',0,0,0,true,false,NULL),
        ('cargo','cargo',0,0,0,false,true,NULL),
        ('cockpit','occupant',0,0,0,true,false,NULL),
        ('computer','system',0,0,0,false,false,2)
) source(
    location_code,location_kind,direct_hull_loss,
    direct_structure_loss,direct_armor_loss,
    receives_vehicle_damage_amount,cargo_is_at_risk,
    maximum_staged_hits
)
JOIN src_locator locator
  ON locator.heading_path=
     'Personal Combat > Vehicles in Personal Combat > Vehicle Damage > Vehicle Hit Location'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1';

CREATE TABLE rule_vehicle_hit_location_roll (
    target_context text NOT NULL CHECK (
        target_context IN (
            'vehicle-external','vehicle-internal','robot-drone'
        )
    ),
    roll_total smallint NOT NULL CHECK (
        roll_total BETWEEN 2 AND 12
    ),
    selection_mode text NOT NULL CHECK (
        selection_mode IN ('fixed','random-eligible')
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    PRIMARY KEY (target_context,roll_total)
);

INSERT INTO rule_vehicle_hit_location_roll
SELECT context.target_context,roll.roll_total,
       CASE
           WHEN context.target_context='robot-drone'
                AND roll.roll_total IN (5,9)
               THEN 'random-eligible'
           ELSE 'fixed'
       END,
       locator.source_locator_id
FROM (
    VALUES
        ('vehicle-external'),
        ('vehicle-internal'),
        ('robot-drone')
) context(target_context)
CROSS JOIN generate_series(2,12) roll(roll_total)
JOIN src_locator locator
  ON locator.heading_path=
     'Personal Combat > Vehicles in Personal Combat > Vehicle Damage > Vehicle Hit Location'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1';

CREATE TABLE rule_vehicle_hit_location_roll_option (
    target_context text NOT NULL,
    roll_total smallint NOT NULL,
    option_order smallint NOT NULL CHECK (option_order>0),
    location_code text NOT NULL REFERENCES
        rule_vehicle_hit_location(location_code),
    PRIMARY KEY (target_context,roll_total,option_order),
    FOREIGN KEY (target_context,roll_total) REFERENCES
        rule_vehicle_hit_location_roll(target_context,roll_total),
    UNIQUE (target_context,roll_total,location_code)
);

INSERT INTO rule_vehicle_hit_location_roll_option
VALUES
    ('vehicle-external',2,1,'hull'),
    ('vehicle-external',3,1,'sensors'),
    ('vehicle-external',4,1,'drive'),
    ('vehicle-external',5,1,'weapon'),
    ('vehicle-external',6,1,'hull'),
    ('vehicle-external',7,1,'armor'),
    ('vehicle-external',8,1,'hull'),
    ('vehicle-external',9,1,'weapon'),
    ('vehicle-external',10,1,'drive'),
    ('vehicle-external',11,1,'sensors'),
    ('vehicle-external',12,1,'hull'),
    ('vehicle-internal',2,1,'structure'),
    ('vehicle-internal',3,1,'power-plant'),
    ('vehicle-internal',4,1,'power-plant'),
    ('vehicle-internal',5,1,'cargo'),
    ('vehicle-internal',6,1,'structure'),
    ('vehicle-internal',7,1,'passengers'),
    ('vehicle-internal',8,1,'structure'),
    ('vehicle-internal',9,1,'cargo'),
    ('vehicle-internal',10,1,'computer'),
    ('vehicle-internal',11,1,'cockpit'),
    ('vehicle-internal',12,1,'cockpit'),
    ('robot-drone',2,1,'hull'),
    ('robot-drone',3,1,'power-plant'),
    ('robot-drone',4,1,'sensors'),
    ('robot-drone',5,1,'weapon'),
    ('robot-drone',5,2,'limb'),
    ('robot-drone',6,1,'hull'),
    ('robot-drone',7,1,'armor'),
    ('robot-drone',8,1,'hull'),
    ('robot-drone',9,1,'weapon'),
    ('robot-drone',9,2,'limb'),
    ('robot-drone',10,1,'drive'),
    ('robot-drone',11,1,'sensors'),
    ('robot-drone',12,1,'computer');

CREATE TABLE rule_vehicle_system_hit_stage (
    location_code text NOT NULL REFERENCES
        rule_vehicle_hit_location(location_code),
    hit_number smallint NOT NULL CHECK (hit_number>0),
    system_status text NOT NULL CHECK (
        system_status IN (
            'degraded','disabled','destroyed','blinded',
            'actions-lost'
        )
    ),
    movement_reduction_fraction numeric CHECK (
        movement_reduction_fraction>0
        AND movement_reduction_fraction<=1
    ),
    control_check_dm smallint,
    operation_check_dm smallint,
    sensor_comms_check_dm smallint,
    robot_recon_check_dm smallint,
    actions_lost_rounds smallint CHECK (actions_lost_rounds>0),
    shutdown_dice_count smallint CHECK (shutdown_dice_count>0),
    shutdown_die_sides smallint CHECK (shutdown_die_sides>1),
    shutdown_target_context text CHECK (
        shutdown_target_context='robot-drone'
    ),
    collateral_hull_dice_count smallint CHECK (
        collateral_hull_dice_count>0
    ),
    collateral_hull_die_sides smallint CHECK (
        collateral_hull_die_sides>1
    ),
    PRIMARY KEY (location_code,hit_number),
    CHECK (
        num_nonnulls(shutdown_dice_count,shutdown_die_sides,
                     shutdown_target_context) IN (0,3)
    ),
    CHECK (
        num_nonnulls(collateral_hull_dice_count,
                     collateral_hull_die_sides) IN (0,2)
    )
);

INSERT INTO rule_vehicle_system_hit_stage (
    location_code,hit_number,system_status,
    movement_reduction_fraction,control_check_dm,
    operation_check_dm,sensor_comms_check_dm,
    robot_recon_check_dm,actions_lost_rounds,
    shutdown_dice_count,shutdown_die_sides,
    shutdown_target_context,collateral_hull_dice_count,
    collateral_hull_die_sides
)
VALUES
    ('drive',1,'degraded',0.10,-1,NULL,NULL,NULL,NULL,
     NULL,NULL,NULL,NULL,NULL),
    ('drive',2,'degraded',0.25,-2,NULL,NULL,NULL,NULL,
     NULL,NULL,NULL,NULL,NULL),
    ('drive',3,'disabled',NULL,NULL,NULL,NULL,NULL,NULL,
     NULL,NULL,NULL,NULL,NULL),
    ('weapon',1,'degraded',NULL,NULL,-2,NULL,NULL,NULL,
     NULL,NULL,NULL,NULL,NULL),
    ('weapon',2,'destroyed',NULL,NULL,NULL,NULL,NULL,NULL,
     NULL,NULL,NULL,NULL,NULL),
    ('sensors',1,'degraded',NULL,NULL,NULL,-2,-2,NULL,
     NULL,NULL,NULL,NULL,NULL),
    ('sensors',2,'blinded',NULL,NULL,NULL,NULL,NULL,NULL,
     NULL,NULL,NULL,NULL,NULL),
    ('power-plant',1,'actions-lost',NULL,NULL,NULL,NULL,NULL,1,
     NULL,NULL,NULL,NULL,NULL),
    ('power-plant',2,'degraded',0.50,NULL,NULL,NULL,NULL,NULL,
     NULL,NULL,NULL,NULL,NULL),
    ('power-plant',3,'destroyed',NULL,NULL,NULL,NULL,NULL,NULL,
     NULL,NULL,NULL,1,6),
    ('limb',1,'degraded',NULL,NULL,-2,NULL,NULL,NULL,
     NULL,NULL,NULL,NULL,NULL),
    ('limb',2,'destroyed',NULL,NULL,NULL,NULL,NULL,NULL,
     NULL,NULL,NULL,NULL,NULL),
    ('computer',1,'disabled',NULL,NULL,NULL,NULL,NULL,NULL,
     1,6,'robot-drone',NULL,NULL),
    ('computer',2,'destroyed',NULL,NULL,NULL,NULL,NULL,NULL,
     NULL,NULL,NULL,NULL,NULL);

CREATE TABLE rule_vehicle_location_overflow (
    target_context text NOT NULL CHECK (
        target_context IN (
            'vehicle-external','vehicle-internal',
            'robot-drone','any'
        )
    ),
    location_code text NOT NULL REFERENCES
        rule_vehicle_hit_location(location_code),
    overflow_condition text NOT NULL CHECK (
        overflow_condition IN (
            'integrity-exhausted','after-final-stage',
            'no-eligible-target','no-living-passengers',
            'no-cargo','pilot-dead'
        )
    ),
    overflow_kind text NOT NULL CHECK (
        overflow_kind IN ('location','same-roll-internal')
    ),
    overflow_location_code text REFERENCES
        rule_vehicle_hit_location(location_code),
    PRIMARY KEY (target_context,location_code),
    CHECK (
        (overflow_kind='location'
         AND overflow_location_code IS NOT NULL)
        OR
        (overflow_kind='same-roll-internal'
         AND overflow_location_code IS NULL)
    )
);

INSERT INTO rule_vehicle_location_overflow
VALUES
    (
        'vehicle-external','hull','integrity-exhausted',
        'same-roll-internal',NULL
    ),
    (
        'robot-drone','hull','integrity-exhausted',
        'location','structure'
    ),
    ('any','drive','after-final-stage','location','hull'),
    ('any','weapon','no-eligible-target','location','hull'),
    ('any','sensors','after-final-stage','location','hull'),
    ('robot-drone','limb','after-final-stage','location','hull'),
    (
        'vehicle-internal','passengers','no-living-passengers',
        'location','structure'
    ),
    (
        'vehicle-internal','cargo','no-cargo',
        'location','structure'
    ),
    (
        'vehicle-internal','cockpit','pilot-dead',
        'location','structure'
    ),
    (
        'any','computer','after-final-stage',
        'location','structure'
    );

CREATE TABLE rule_vehicle_destruction (
    damage_rule_id bigint PRIMARY KEY REFERENCES
        rule_vehicle_damage_procedure(damage_rule_id),
    destroyed_at_structure smallint NOT NULL CHECK (
        destroyed_at_structure=0
    ),
    explodes_below_structure smallint NOT NULL CHECK (
        explodes_below_structure=0
    ),
    closed_occupants_may_evade_explosion boolean NOT NULL,
    open_occupants_may_evade_explosion boolean NOT NULL
);

INSERT INTO rule_vehicle_destruction
SELECT damage_rule_id,0,0,false,true
FROM rule_vehicle_damage_procedure;

CREATE TABLE rule_vehicle_explosion_zone (
    damage_rule_id bigint NOT NULL REFERENCES
        rule_vehicle_destruction(damage_rule_id),
    maximum_radius_metres numeric NOT NULL CHECK (
        maximum_radius_metres>0
    ),
    damage_dice_count smallint NOT NULL CHECK (
        damage_dice_count>0
    ),
    damage_die_sides smallint NOT NULL CHECK (
        damage_die_sides>1
    ),
    includes_occupants boolean NOT NULL,
    PRIMARY KEY (damage_rule_id,maximum_radius_metres)
);

INSERT INTO rule_vehicle_explosion_zone
SELECT damage_rule_id,source.*
FROM rule_vehicle_destruction
CROSS JOIN (
    VALUES
        (6::numeric,4::smallint,6::smallint,true),
        (12::numeric,2::smallint,6::smallint,true)
) source(
    maximum_radius_metres,damage_dice_count,
    damage_die_sides,includes_occupants
);

CREATE TABLE rule_vehicle_repair_category (
    repair_rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    repair_category text NOT NULL UNIQUE CHECK (
        repair_category IN ('system','hull','structure')
    ),
    skill_requirement text NOT NULL CHECK (
        skill_requirement IN ('appropriate','fixed','none')
    ),
    fixed_skill_rule_id bigint REFERENCES rule_rule(rule_id),
    difficulty_rule_id bigint REFERENCES rule_difficulty(rule_id),
    time_dice_count smallint NOT NULL CHECK (time_dice_count>0),
    time_die_sides smallint NOT NULL CHECK (time_die_sides>1),
    time_multiplier_hours smallint NOT NULL CHECK (
        time_multiplier_hours>0
    ),
    time_basis text NOT NULL CHECK (
        time_basis IN ('per-repair','per-damage-point')
    ),
    spare_part_hits_consumed smallint CHECK (
        spare_part_hits_consumed>0
    ),
    workshop_required boolean NOT NULL,
    base_vehicle_cost_fraction_per_point numeric CHECK (
        base_vehicle_cost_fraction_per_point>0
        AND base_vehicle_cost_fraction_per_point<=1
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    CHECK (
        (skill_requirement='fixed'
         AND fixed_skill_rule_id IS NOT NULL)
        OR
        (skill_requirement<>'fixed'
         AND fixed_skill_rule_id IS NULL)
    )
);

WITH source(
    rule_code,repair_category,skill_requirement,
    fixed_skill_code,difficulty_code,time_multiplier_hours,
    time_basis,spare_part_hits_consumed,workshop_required,
    base_cost_fraction,heading_path
) AS (
    VALUES
        (
            'vehicle.repair.system','system','appropriate',
            NULL::text,'average',1::smallint,'per-repair',
            1::smallint,false,NULL::numeric,
            'Personal Combat > Vehicles in Personal Combat > Repairs > System Damage'
        ),
        (
            'vehicle.repair.hull','hull','fixed',
            'skill.mechanics',NULL,1,'per-repair',
            1,false,NULL,
            'Personal Combat > Vehicles in Personal Combat > Repairs > Hull Damage'
        ),
        (
            'vehicle.repair.structure','structure','none',
            NULL,NULL,10,'per-damage-point',
            NULL,true,0.20,
            'Personal Combat > Vehicles in Personal Combat > Repairs > Structure Damage'
        )
)
INSERT INTO rule_vehicle_repair_category
SELECT repair_rule.rule_id,source.repair_category,
       source.skill_requirement,skill_rule.rule_id,
       difficulty.rule_id,1,6,source.time_multiplier_hours,
       source.time_basis,source.spare_part_hits_consumed,
       source.workshop_required,source.base_cost_fraction,
       locator.source_locator_id
FROM source
JOIN rule_rule repair_rule
  ON repair_rule.rule_code=source.rule_code
LEFT JOIN rule_rule skill_rule
  ON skill_rule.rule_code=source.fixed_skill_code
LEFT JOIN rule_rule difficulty_rule
  ON difficulty_rule.rule_code=
     'difficulty.'||source.difficulty_code
LEFT JOIN rule_difficulty difficulty
  ON difficulty.rule_id=difficulty_rule.rule_id
JOIN src_locator locator
  ON locator.heading_path=source.heading_path
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1';

CREATE TABLE rule_vehicle_system_repair_state (
    system_damage_state text PRIMARY KEY CHECK (
        system_damage_state IN ('damaged','destroyed')
    ),
    may_be_jury_rigged boolean NOT NULL,
    jury_rig_duration_dice_count smallint CHECK (
        jury_rig_duration_dice_count>0
    ),
    jury_rig_duration_die_sides smallint CHECK (
        jury_rig_duration_die_sides>1
    ),
    jury_rig_duration_unit text CHECK (
        jury_rig_duration_unit='hour'
    ),
    may_use_spare_parts boolean NOT NULL,
    workshop_required boolean NOT NULL,
    specialist_materials_required boolean NOT NULL,
    repair_cost_dice_count smallint CHECK (
        repair_cost_dice_count>0
    ),
    repair_cost_die_sides smallint CHECK (
        repair_cost_die_sides>1
    ),
    repair_cost_fraction_per_die_point numeric CHECK (
        repair_cost_fraction_per_die_point>0
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    CHECK (
        num_nonnulls(
            jury_rig_duration_dice_count,
            jury_rig_duration_die_sides,
            jury_rig_duration_unit
        )=CASE WHEN may_be_jury_rigged THEN 3 ELSE 0 END
    ),
    CHECK (
        num_nonnulls(
            repair_cost_dice_count,repair_cost_die_sides,
            repair_cost_fraction_per_die_point
        )=CASE
            WHEN system_damage_state='destroyed' THEN 3
            ELSE 0
        END
    )
);

INSERT INTO rule_vehicle_system_repair_state
SELECT source.*,locator.source_locator_id
FROM (
    VALUES
        (
            'damaged',true,1::smallint,6::smallint,'hour',
            true,false,false,NULL::smallint,NULL::smallint,
            NULL::numeric
        ),
        (
            'destroyed',false,NULL,NULL,NULL,
            false,true,true,2,6,0.10
        )
) source(
    system_damage_state,may_be_jury_rigged,
    jury_rig_duration_dice_count,jury_rig_duration_die_sides,
    jury_rig_duration_unit,may_use_spare_parts,
    workshop_required,specialist_materials_required,
    repair_cost_dice_count,repair_cost_die_sides,
    repair_cost_fraction_per_die_point
)
JOIN src_locator locator
  ON locator.heading_path=
     'Personal Combat > Vehicles in Personal Combat > Repairs > System Damage'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1';

CREATE TABLE rule_vehicle_spare_part_exclusion (
    location_code text PRIMARY KEY REFERENCES
        rule_vehicle_hit_location(location_code),
    may_supply_spare_parts boolean NOT NULL CHECK (
        NOT may_supply_spare_parts
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_vehicle_spare_part_exclusion
SELECT source.location_code,false,locator.source_locator_id
FROM (
    VALUES ('passengers'),('cockpit')
) source(location_code)
JOIN src_locator locator
  ON locator.heading_path=
     'Personal Combat > Vehicles in Personal Combat > Repairs > System Damage'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1';

INSERT INTO src_record_provenance (
    rule_id,content_package_id,source_locator_id,
    provenance_class,is_primary_citation
)
SELECT rule.rule_id,rule.content_package_id,
       locator.source_locator_id,'direct',true
FROM rule_rule rule
JOIN src_work work
  ON work.work_code='cepheus-engine.github-v9.1'
JOIN src_locator locator
  ON locator.source_work_id=work.source_work_id
 AND locator.heading_path=
     CASE rule.rule_code
         WHEN 'vehicle.damage.procedure'
             THEN 'Personal Combat > Vehicles in Personal Combat > Vehicle Damage'
         WHEN 'vehicle.damage.hit-location'
             THEN 'Personal Combat > Vehicles in Personal Combat > Vehicle Damage > Vehicle Hit Location'
         WHEN 'vehicle.repair.system'
             THEN 'Personal Combat > Vehicles in Personal Combat > Repairs > System Damage'
         WHEN 'vehicle.repair.hull'
             THEN 'Personal Combat > Vehicles in Personal Combat > Repairs > Hull Damage'
         WHEN 'vehicle.repair.structure'
             THEN 'Personal Combat > Vehicles in Personal Combat > Repairs > Structure Damage'
     END
WHERE rule.rule_code LIKE 'vehicle.damage.%'
   OR rule.rule_code LIKE 'vehicle.repair.%';
