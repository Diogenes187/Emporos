INSERT INTO src_locator (
    source_work_id,source_artifact_id,locator_type,
    heading_path,display_citation
)
SELECT artifact.source_work_id,artifact.source_artifact_id,
       'heading',source.heading_path,source.display_citation
FROM src_artifact artifact
CROSS JOIN (
    VALUES
        ('Vehicle Design > Vehicle Armaments',
         'Cepheus Engine VDS, Vehicle Armaments'),
        ('Vehicle Design > Vehicle Armaments > Gun Ports',
         'Cepheus Engine VDS, Vehicle Gun Ports'),
        ('Vehicle Design > Vehicle Armaments > Weapon Mounts',
         'Cepheus Engine VDS, Vehicle Weapon Mounts'),
        ('Vehicle Design > Vehicle Armaments > Vehicle Turrets',
         'Cepheus Engine VDS, Vehicle Turrets'),
        ('Vehicle Design > Vehicle Armaments > Vehicle Armament Options',
         'Cepheus Engine VDS, Vehicle Armament Options')
) source(heading_path,display_citation)
WHERE artifact.source_uri='src/vds/vehicle-design.md';

WITH source(rule_code,rule_name) AS (
    VALUES
        ('vehicle.armament.gun-port','Gun Port'),
        ('vehicle.weapon-mount.fixed','Fixed Weapon Mount'),
        ('vehicle.weapon-mount.pintle','Pintle Weapon Mount'),
        ('vehicle.weapon-mount.ring','Ring Weapon Mount'),
        ('vehicle.weapon-mount.pintle-powered',
         'Powered Pintle Weapon Mount'),
        ('vehicle.weapon-mount.ring-powered',
         'Powered Ring Weapon Mount'),
        ('vehicle.weapon-mount-option.gun-shield','Gun Shield'),
        ('vehicle.turret.small','Small Vehicle Turret'),
        ('vehicle.turret.large','Large Vehicle Turret'),
        ('vehicle.turret-option.pop-up','Pop-Up Vehicle Turret'),
        ('vehicle.armament-option.heavy-turret-weapon',
         'Heavy Turret Weapon'),
        ('vehicle.armament-option.laser-guidance','Laser Guidance'),
        ('vehicle.armament-option.light-turret-weapon',
         'Light Turret Weapon'),
        ('vehicle.armament-option.missile-guidance-system',
         'Missile Guidance System'),
        ('vehicle.armament-option.rotary-turret-weapon',
         'Rotary Turret Weapon')
)
INSERT INTO rule_rule (
    content_package_id,rule_code,name,rule_category,rule_status
)
SELECT package.content_package_id,source.rule_code,
       source.rule_name,'vehicle','approved'
FROM source
CROSS JOIN sys_content_package package
WHERE package.package_code='cepheus-engine';

WITH source(weapon_code,weapon_name) AS (
    VALUES
        ('revolver','Revolver'),
        ('auto-pistol','Auto Pistol'),
        ('carbine','Carbine'),
        ('rifle','Rifle'),
        ('shotgun','Shotgun'),
        ('submachinegun','Submachinegun'),
        ('auto-rifle','Auto Rifle'),
        ('assault-rifle','Assault Rifle'),
        ('body-pistol','Body Pistol'),
        ('grenade-launcher','Grenade Launcher'),
        ('rocket-launcher','Rocket Launcher'),
        ('laser-carbine','Laser Carbine'),
        ('ram-grenade-launcher','RAM Grenade Launcher'),
        ('snub-pistol','Snub Pistol'),
        ('accelerator-rifle','Accelerator Rifle'),
        ('laser-rifle','Laser Rifle'),
        ('advanced-combat-rifle','Advanced Combat Rifle'),
        ('armor-rifle-man-portable',
         'Armor Rifle, Man Portable (ARMP)'),
        ('gauss-rifle','Gauss Rifle'),
        ('laser-pistol','Laser Pistol'),
        ('plasma-gun-man-portable',
         'Plasma Gun, Man Portable (PGMP)'),
        ('stagger-laser','Stagger Laser'),
        ('magrail-rifle','Magrail Rifle'),
        ('fusion-gun-man-portable',
         'Fusion Gun, Man Portable (FGMP)')
)
INSERT INTO rule_rule (
    content_package_id,rule_code,name,rule_category,rule_status
)
SELECT package.content_package_id,
       'vehicle.gun-port-weapon.'||source.weapon_code,
       source.weapon_name,'vehicle','approved'
FROM source
CROSS JOIN sys_content_package package
WHERE package.package_code='cepheus-engine';

CREATE TABLE rule_vehicle_weapon_point_formula (
    formula_code text PRIMARY KEY,
    displacement_tons_per_weapon_point numeric NOT NULL CHECK (
        displacement_tons_per_weapon_point>0
    ),
    minimum_weapon_points smallint NOT NULL CHECK (
        minimum_weapon_points>0
    ),
    allocation_rounding text NOT NULL CHECK (
        allocation_rounding IN ('floor','ceiling')
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_vehicle_weapon_point_formula
SELECT 'standard',5,1,'floor',locator.source_locator_id
FROM src_locator locator
WHERE locator.heading_path=
      'Vehicle Design > Vehicle Armaments > Weapon Mounts';

CREATE TABLE rule_vehicle_gun_port (
    gun_port_rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    unit_cost_minor bigint NOT NULL CHECK (unit_cost_minor>=0),
    unit_spaces numeric NOT NULL CHECK (unit_spaces>=0),
    weapon_points_required smallint NOT NULL CHECK (
        weapon_points_required>=0
    ),
    stabilized boolean NOT NULL,
    fire_control_supported boolean NOT NULL,
    personal_weapon_ranges_only boolean NOT NULL,
    grants_vehicle_armor boolean NOT NULL,
    adjacent_attack_ignores_vehicle_armor boolean NOT NULL,
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_vehicle_gun_port
SELECT rule.rule_id,250,0,0,false,false,true,true,true,
       locator.source_locator_id
FROM rule_rule rule
JOIN src_locator locator
  ON locator.heading_path=
     'Vehicle Design > Vehicle Armaments > Gun Ports'
WHERE rule.rule_code='vehicle.armament.gun-port';

CREATE TABLE rule_vehicle_gun_port_weapon (
    gun_port_weapon_rule_id bigint PRIMARY KEY REFERENCES
        rule_rule(rule_id),
    weapon_code text NOT NULL UNIQUE CHECK (
        weapon_code ~
        '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
    ),
    personal_weapon_rule_id bigint REFERENCES
        inv_weapon_definition(item_rule_id),
    catalogue_link_status text NOT NULL CHECK (
        catalogue_link_status IN ('linked','source-item-not-imported')
    ),
    minimum_tech_level smallint NOT NULL CHECK (
        minimum_tech_level>=0
    ),
    unit_cost_minor bigint NOT NULL CHECK (unit_cost_minor>=0),
    unit_spaces numeric NOT NULL CHECK (unit_spaces>=0),
    single_shot_rate smallint CHECK (single_shot_rate>0),
    burst_shot_rate smallint CHECK (burst_shot_rate>0),
    automatic_fire_rate smallint CHECK (automatic_fire_rate>0),
    attack_profile_code text NOT NULL REFERENCES
        combat_attack_profile(attack_profile_code),
    damage_dice_count smallint CHECK (damage_dice_count>0),
    damage_die_sides smallint CHECK (damage_die_sides>1),
    special_damage_code text CHECK (
        special_damage_code IS NULL
        OR special_damage_code ~
           '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
    ),
    has_recoil boolean NOT NULL,
    illegal_at_law_level smallint NOT NULL CHECK (
        illegal_at_law_level>=0
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    CHECK (
        num_nonnulls(
            single_shot_rate,burst_shot_rate,automatic_fire_rate
        )>0
    ),
    CHECK (
        (damage_dice_count IS NULL)=(damage_die_sides IS NULL)
    ),
    CHECK (
        num_nonnulls(damage_dice_count,special_damage_code)=1
    ),
    CHECK (
        (catalogue_link_status='linked'
         AND personal_weapon_rule_id IS NOT NULL)
        OR
        (catalogue_link_status='source-item-not-imported'
         AND personal_weapon_rule_id IS NULL)
    )
);

WITH source(
    weapon_code,minimum_tl,unit_cost,unit_spaces,
    single_rate,burst_rate,automatic_rate,attack_profile,
    damage_dice,special_damage,has_recoil,law_level
) AS (
    VALUES
        ('revolver',4,150::bigint,0.01::numeric,1::smallint,NULL::smallint,NULL::smallint,'pistol',2::smallint,NULL::text,true,6),
        ('auto-pistol',5,200,0.01,1,NULL,NULL,'pistol',2,NULL,true,6),
        ('carbine',5,200,0.04,1,NULL,NULL,'shotgun',2,NULL,true,6),
        ('rifle',5,200,0.05,1,NULL,NULL,'rifle',3,NULL,true,6),
        ('shotgun',5,150,0.05,1,NULL,NULL,'shotgun',4,NULL,true,7),
        ('submachinegun',5,500,0.03,NULL,4,NULL,'assault-weapon',2,NULL,true,4),
        ('auto-rifle',6,1000,0.06,1,4,NULL,'rifle',3,NULL,true,6),
        ('assault-rifle',7,300,0.04,1,4,NULL,'assault-weapon',3,NULL,true,4),
        ('body-pistol',7,500,0.01,1,NULL,NULL,'pistol',2,NULL,true,1),
        ('grenade-launcher',7,400,0.07,1,NULL,NULL,'shotgun',NULL,'by-grenade',true,3),
        ('rocket-launcher',7,2000,0.07,1,NULL,NULL,'rocket',4,NULL,false,3),
        ('laser-carbine',8,2500,0.06,1,NULL,NULL,'pistol',4,NULL,false,2),
        ('ram-grenade-launcher',8,800,0.07,1,3,NULL,'assault-weapon',NULL,'by-grenade',true,3),
        ('snub-pistol',8,150,0.01,1,NULL,NULL,'pistol',2,NULL,false,6),
        ('accelerator-rifle',9,900,0.03,1,3,NULL,'rifle',3,NULL,false,6),
        ('laser-rifle',9,3500,0.07,1,NULL,NULL,'rifle',5,NULL,false,2),
        ('advanced-combat-rifle',10,1000,0.04,1,4,NULL,'rifle',3,NULL,true,6),
        ('armor-rifle-man-portable',10,10000,0.18,1,4,NULL,'rocket',10,NULL,true,3),
        ('gauss-rifle',12,1500,0.04,1,4,10,'rifle',4,NULL,false,6),
        ('laser-pistol',12,1000,0.02,1,NULL,NULL,'pistol',4,NULL,false,2),
        ('plasma-gun-man-portable',12,20000,0.12,1,4,NULL,'rifle',10,NULL,true,2),
        ('stagger-laser',12,7500,0.11,1,4,NULL,'assault-weapon',5,NULL,false,2),
        ('magrail-rifle',13,2200,0.05,1,4,NULL,'rifle',5,NULL,false,6),
        ('fusion-gun-man-portable',14,100000,0.14,1,4,NULL,'rifle',16,NULL,true,2)
)
INSERT INTO rule_vehicle_gun_port_weapon (
    gun_port_weapon_rule_id,weapon_code,
    personal_weapon_rule_id,catalogue_link_status,
    minimum_tech_level,unit_cost_minor,unit_spaces,
    single_shot_rate,burst_shot_rate,automatic_fire_rate,
    attack_profile_code,damage_dice_count,damage_die_sides,
    special_damage_code,has_recoil,illegal_at_law_level,
    source_locator_id
)
SELECT rule.rule_id,source.weapon_code,
       personal_definition.item_rule_id,
       CASE WHEN personal_definition.item_rule_id IS NULL
            THEN 'source-item-not-imported'
            ELSE 'linked' END,
       source.minimum_tl,source.unit_cost,source.unit_spaces,
       source.single_rate,source.burst_rate,source.automatic_rate,
       source.attack_profile,source.damage_dice,
       CASE WHEN source.damage_dice IS NULL
            THEN NULL ELSE 6 END,
       source.special_damage,source.has_recoil,source.law_level,
       locator.source_locator_id
FROM source
JOIN rule_rule rule
  ON rule.rule_code='vehicle.gun-port-weapon.'||
     source.weapon_code
LEFT JOIN rule_rule personal
  ON personal.rule_code='equipment.weapon.'||source.weapon_code
LEFT JOIN inv_weapon_definition personal_definition
  ON personal_definition.item_rule_id=personal.rule_id
JOIN src_locator locator
  ON locator.heading_path=
     'Vehicle Design > Vehicle Armaments > Gun Ports';

CREATE TABLE rule_vehicle_weapon_mount (
    mount_rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    mount_code text NOT NULL UNIQUE CHECK (
        mount_code IN (
            'fixed','pintle','ring','pintle-powered','ring-powered'
        )
    ),
    minimum_tech_level smallint NOT NULL CHECK (
        minimum_tech_level>=0
    ),
    unit_cost_minor bigint NOT NULL CHECK (unit_cost_minor>=0),
    maximum_weapon_spaces numeric CHECK (maximum_weapon_spaces>0),
    stabilized boolean NOT NULL,
    fixed_direction boolean NOT NULL,
    removable boolean NOT NULL,
    mount_spaces numeric NOT NULL CHECK (mount_spaces>=0),
    weapon_points_required smallint NOT NULL CHECK (
        weapon_points_required>0
    ),
    fire_control_supported boolean NOT NULL,
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

WITH source(
    mount_code,minimum_tl,unit_cost,maximum_weapon_spaces,
    stabilized,fixed_direction,removable
) AS (
    VALUES
        ('fixed',1::smallint,0::bigint,NULL::numeric,false,true,false),
        ('pintle',4,500,1.5,false,false,true),
        ('ring',4,750,1.5,false,false,true),
        ('pintle-powered',7,1500,3,true,false,true),
        ('ring-powered',7,2150,3,true,false,true)
)
INSERT INTO rule_vehicle_weapon_mount
SELECT rule.rule_id,source.mount_code,source.minimum_tl,
       source.unit_cost,source.maximum_weapon_spaces,
       source.stabilized,source.fixed_direction,
       source.removable,0,1,false,locator.source_locator_id
FROM source
JOIN rule_rule rule
  ON rule.rule_code='vehicle.weapon-mount.'||source.mount_code
JOIN src_locator locator
  ON locator.heading_path=
     'Vehicle Design > Vehicle Armaments > Weapon Mounts';

CREATE TABLE rule_vehicle_gun_shield (
    option_rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    cost_per_armor_point_minor bigint NOT NULL CHECK (
        cost_per_armor_point_minor>=0
    ),
    armor_tech_level_divisor smallint NOT NULL CHECK (
        armor_tech_level_divisor>0
    ),
    armor_rounding text NOT NULL CHECK (
        armor_rounding IN ('floor','ceiling')
    ),
    minimum_armor smallint NOT NULL CHECK (minimum_armor>0),
    facing_only boolean NOT NULL,
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_vehicle_gun_shield
SELECT rule.rule_id,200,2,'floor',1,true,locator.source_locator_id
FROM rule_rule rule
JOIN src_locator locator
  ON locator.heading_path=
     'Vehicle Design > Vehicle Armaments > Weapon Mounts'
WHERE rule.rule_code='vehicle.weapon-mount-option.gun-shield';

CREATE TABLE rule_vehicle_gun_shield_mount (
    option_rule_id bigint NOT NULL REFERENCES
        rule_vehicle_gun_shield(option_rule_id),
    mount_rule_id bigint NOT NULL REFERENCES
        rule_vehicle_weapon_mount(mount_rule_id),
    PRIMARY KEY (option_rule_id,mount_rule_id)
);

INSERT INTO rule_vehicle_gun_shield_mount
SELECT shield.option_rule_id,mount.mount_rule_id
FROM rule_vehicle_gun_shield shield
CROSS JOIN rule_vehicle_weapon_mount mount
WHERE mount.mount_code IN (
    'pintle','ring','pintle-powered','ring-powered'
);

CREATE TABLE rule_vehicle_turret (
    turret_rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    turret_code text NOT NULL UNIQUE CHECK (
        turret_code IN ('small','large')
    ),
    base_spaces numeric NOT NULL CHECK (base_spaces>=0),
    weapon_volume_multiplier numeric NOT NULL CHECK (
        weapon_volume_multiplier>0
    ),
    price_per_total_space_minor bigint NOT NULL CHECK (
        price_per_total_space_minor>=0
    ),
    operator_capacity smallint NOT NULL CHECK (operator_capacity>=0),
    remotely_controlled boolean NOT NULL,
    weapon_points_per_spaces numeric NOT NULL CHECK (
        weapon_points_per_spaces>0
    ),
    weapon_point_rounding text NOT NULL CHECK (
        weapon_point_rounding IN ('floor','ceiling')
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

WITH source(
    turret_code,base_spaces,price_per_space,
    operator_capacity,remotely_controlled
) AS (
    VALUES
        ('small',0.5::numeric,8000::bigint,0::smallint,true),
        ('large',3,16000,1,false)
)
INSERT INTO rule_vehicle_turret
SELECT rule.rule_id,source.turret_code,source.base_spaces,
       1,source.price_per_space,source.operator_capacity,
       source.remotely_controlled,60,'ceiling',
       locator.source_locator_id
FROM source
JOIN rule_rule rule
  ON rule.rule_code='vehicle.turret.'||source.turret_code
JOIN src_locator locator
  ON locator.heading_path=
     'Vehicle Design > Vehicle Armaments > Vehicle Turrets';

CREATE TABLE rule_vehicle_coaxial_mount (
    formula_code text PRIMARY KEY,
    shared_firing_arc boolean NOT NULL,
    additional_weapon_points_per_weapon_after_first smallint NOT NULL CHECK (
        additional_weapon_points_per_weapon_after_first>0
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_vehicle_coaxial_mount
SELECT 'standard',true,1,locator.source_locator_id
FROM src_locator locator
WHERE locator.heading_path=
      'Vehicle Design > Vehicle Armaments > Vehicle Turrets';

CREATE TABLE rule_vehicle_pop_up_turret (
    option_rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    total_space_multiplier numeric NOT NULL CHECK (
        total_space_multiplier>0
    ),
    additional_price_per_total_space_minor bigint NOT NULL CHECK (
        additional_price_per_total_space_minor>=0
    ),
    concealed_while_retracted boolean NOT NULL,
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_vehicle_pop_up_turret
SELECT rule.rule_id,2,4000,true,locator.source_locator_id
FROM rule_rule rule
JOIN src_locator locator
  ON locator.heading_path=
     'Vehicle Design > Vehicle Armaments > Vehicle Turrets'
WHERE rule.rule_code='vehicle.turret-option.pop-up';

CREATE TABLE rule_vehicle_armament_option (
    option_rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    option_code text NOT NULL UNIQUE CHECK (
        option_code ~
        '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
    ),
    minimum_tech_level smallint NOT NULL CHECK (
        minimum_tech_level>=0
    ),
    fixed_cost_minor bigint,
    unit_spaces numeric,
    weapon_price_multiplier numeric,
    rate_of_fire_multiplier numeric,
    range_band_steps smallint,
    damage_dice_modifier smallint,
    attack_dm smallint,
    target_motion_requirement text CHECK (
        target_motion_requirement IS NULL
        OR target_motion_requirement IN ('stationary','moving')
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    CHECK (
        fixed_cost_minor IS NULL OR fixed_cost_minor>=0
    ),
    CHECK (unit_spaces IS NULL OR unit_spaces>=0),
    CHECK (
        weapon_price_multiplier IS NULL
        OR weapon_price_multiplier>0
    ),
    CHECK (
        rate_of_fire_multiplier IS NULL
        OR rate_of_fire_multiplier>0
    )
);

WITH source(
    option_code,minimum_tl,fixed_cost,unit_spaces,
    price_multiplier,rof_multiplier,range_steps,
    damage_modifier,attack_dm,target_motion
) AS (
    VALUES
        ('heavy-turret-weapon',3::smallint,NULL::bigint,NULL::numeric,
         1.5::numeric,0.5::numeric,NULL::smallint,1::smallint,
         NULL::smallint,NULL::text),
        ('laser-guidance',8,1000,1,NULL,NULL,NULL,NULL,1,'stationary'),
        ('light-turret-weapon',3,NULL,NULL,0.75,NULL,1,-1,NULL,NULL),
        ('missile-guidance-system',5,10000,6,NULL,NULL,NULL,NULL,1,'moving'),
        ('rotary-turret-weapon',5,NULL,NULL,2,2,NULL,-1,NULL,NULL)
)
INSERT INTO rule_vehicle_armament_option
SELECT rule.rule_id,source.option_code,source.minimum_tl,
       source.fixed_cost,source.unit_spaces,
       source.price_multiplier,source.rof_multiplier,
       source.range_steps,source.damage_modifier,
       source.attack_dm,source.target_motion,
       locator.source_locator_id
FROM source
JOIN rule_rule rule
  ON rule.rule_code='vehicle.armament-option.'||
     source.option_code
JOIN src_locator locator
  ON locator.heading_path=
     'Vehicle Design > Vehicle Armaments > Vehicle Armament Options';

CREATE TABLE rule_vehicle_armament_option_weapon_family (
    option_rule_id bigint NOT NULL REFERENCES
        rule_vehicle_armament_option(option_rule_id),
    weapon_family_code text NOT NULL CHECK (
        weapon_family_code IN (
            'any-turret-weapon','mortar','howitzer',
            'artillery-gun','autocannon','missile','machine-gun'
        )
    ),
    PRIMARY KEY (option_rule_id,weapon_family_code)
);

INSERT INTO rule_vehicle_armament_option_weapon_family
SELECT option.option_rule_id,source.weapon_family_code
FROM (
    VALUES
        ('heavy-turret-weapon','any-turret-weapon'),
        ('laser-guidance','mortar'),
        ('laser-guidance','howitzer'),
        ('laser-guidance','artillery-gun'),
        ('laser-guidance','autocannon'),
        ('light-turret-weapon','any-turret-weapon'),
        ('missile-guidance-system','missile'),
        ('rotary-turret-weapon','machine-gun')
) source(option_code,weapon_family_code)
JOIN rule_vehicle_armament_option option USING (option_code);

CREATE TABLE rule_vehicle_armament_option_incompatibility (
    first_option_rule_id bigint NOT NULL REFERENCES
        rule_vehicle_armament_option(option_rule_id),
    second_option_rule_id bigint NOT NULL REFERENCES
        rule_vehicle_armament_option(option_rule_id),
    PRIMARY KEY (first_option_rule_id,second_option_rule_id),
    CHECK (first_option_rule_id<second_option_rule_id)
);

INSERT INTO rule_vehicle_armament_option_incompatibility
SELECT least(heavy.option_rule_id,light.option_rule_id),
       greatest(heavy.option_rule_id,light.option_rule_id)
FROM rule_vehicle_armament_option heavy
JOIN rule_vehicle_armament_option light
  ON light.option_code='light-turret-weapon'
WHERE heavy.option_code='heavy-turret-weapon';

INSERT INTO src_record_provenance (
    rule_id,content_package_id,source_locator_id,
    provenance_class,is_primary_citation
)
SELECT rule.rule_id,rule.content_package_id,
       CASE
           WHEN rule.rule_code LIKE 'vehicle.gun-port-weapon.%'
             OR rule.rule_code='vehicle.armament.gun-port'
               THEN gun_port_locator.source_locator_id
           WHEN rule.rule_code LIKE 'vehicle.weapon-mount.%'
             OR rule.rule_code LIKE 'vehicle.weapon-mount-option.%'
               THEN mount_locator.source_locator_id
           WHEN rule.rule_code LIKE 'vehicle.turret.%'
             OR rule.rule_code LIKE 'vehicle.turret-option.%'
               THEN turret_locator.source_locator_id
           ELSE option_locator.source_locator_id
       END,
       'direct',true
FROM rule_rule rule
LEFT JOIN src_locator gun_port_locator
  ON gun_port_locator.heading_path=
     'Vehicle Design > Vehicle Armaments > Gun Ports'
LEFT JOIN src_locator mount_locator
  ON mount_locator.heading_path=
     'Vehicle Design > Vehicle Armaments > Weapon Mounts'
LEFT JOIN src_locator turret_locator
  ON turret_locator.heading_path=
     'Vehicle Design > Vehicle Armaments > Vehicle Turrets'
LEFT JOIN src_locator option_locator
  ON option_locator.heading_path=
     'Vehicle Design > Vehicle Armaments > Vehicle Armament Options'
WHERE rule.rule_code='vehicle.armament.gun-port'
   OR rule.rule_code LIKE 'vehicle.gun-port-weapon.%'
   OR rule.rule_code LIKE 'vehicle.weapon-mount.%'
   OR rule.rule_code LIKE 'vehicle.weapon-mount-option.%'
   OR rule.rule_code LIKE 'vehicle.turret.%'
   OR rule.rule_code LIKE 'vehicle.turret-option.%'
   OR rule.rule_code LIKE 'vehicle.armament-option.%';

INSERT INTO src_issue (
    issue_code,domain_code,issue_type,review_priority,
    subject_code,title,problem_statement,
    published_value,calculated_value,
    reviewer_question,requested_evidence,engine_disposition
)
SELECT
    'vehicle.armament.heavy-weapon-rof-rounding',
    'vehicle.catalogue','source_omission','medium',
    'heavy-turret-weapon',
    'Heavy Turret Weapon rate-of-fire rounding unspecified',
    'Heavy Turret Weapon halves rate of fire, but the rule does not say how to round odd rates or multi-mode rate-of-fire profiles.',
    'Rate of fire multiplied by 0.5',
    'Rounding method source-unspecified',
    'Should each Heavy Turret Weapon rate-of-fire mode round down, round up, or to the nearest shot?',
    'A corrected printing, publisher errata, or a corroborating authorized source with an explicit rounding rule.',
    'source_gap_pending';

INSERT INTO src_issue_locator (
    source_issue_id,source_locator_id,evidence_role
)
SELECT issue.source_issue_id,locator.source_locator_id,'primary'
FROM src_issue issue
JOIN src_locator locator
  ON locator.heading_path=
     'Vehicle Design > Vehicle Armaments > Vehicle Armament Options'
WHERE issue.issue_code=
      'vehicle.armament.heavy-weapon-rof-rounding';
