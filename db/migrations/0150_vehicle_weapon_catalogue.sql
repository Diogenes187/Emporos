INSERT INTO src_locator (
    source_work_id,source_artifact_id,locator_type,
    heading_path,display_citation
)
SELECT artifact.source_work_id,artifact.source_artifact_id,
       'heading',source.heading_path,source.display_citation
FROM src_artifact artifact
CROSS JOIN (
    VALUES
        ('Vehicle-Mounted Weapon Ranges > Attack Difficulties by Weapon Type',
         'Cepheus Engine VDS, Vehicle-Mounted Weapon Ranges'),
        ('Vehicle Design > Vehicle Armaments > Vehicular Weapons',
         'Cepheus Engine VDS, Vehicular Weapons'),
        ('Vehicle Design > Vehicle Armaments > Vehicular Weapons > Special Weapon Rules',
         'Cepheus Engine VDS, Special Weapon Rules'),
        ('Vehicle Design > Vehicle Armaments > Vehicular Weapon Ammunition',
         'Cepheus Engine VDS, Vehicular Weapon Ammunition')
) source(heading_path,display_citation)
WHERE artifact.source_uri=CASE
    WHEN source.heading_path LIKE 'Vehicle-Mounted Weapon Ranges%'
        THEN 'src/vds/introduction.md'
    ELSE 'src/vds/vehicle-design.md'
END;

CREATE TABLE rule_vehicle_weapon_target_range (
    target_range_code text PRIMARY KEY CHECK (
        target_range_code ~
        '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
    ),
    range_name text NOT NULL UNIQUE,
    display_order smallint NOT NULL UNIQUE CHECK (display_order>0),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_vehicle_weapon_target_range
SELECT source.target_range_code,source.range_name,
       source.display_order,locator.source_locator_id
FROM (
    VALUES
        ('personal','Personal',1::smallint),
        ('close','Close',2),
        ('short','Short',3),
        ('medium','Medium',4),
        ('long','Long',5),
        ('very-long','Very Long',6),
        ('distant','Distant',7),
        ('very-distant','Very Distant',8),
        ('extreme','Extreme',9),
        ('continental','Continental',10)
) source(target_range_code,range_name,display_order)
JOIN src_locator locator
  ON locator.heading_path=
     'Vehicle-Mounted Weapon Ranges > Attack Difficulties by Weapon Type'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1';

CREATE TABLE rule_vehicle_weapon_range_profile (
    range_profile_code text PRIMARY KEY CHECK (
        range_profile_code ~
        '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
    ),
    profile_name text NOT NULL UNIQUE,
    combat_attack_profile_code text REFERENCES
        combat_attack_profile(attack_profile_code),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_vehicle_weapon_range_profile
SELECT source.range_profile_code,source.profile_name,
       source.combat_profile,locator.source_locator_id
FROM (
    VALUES
        ('close-quarters','Close Quarters','close-quarters'),
        ('extended-reach','Extended Reach','extended-reach'),
        ('thrown','Thrown','thrown'),
        ('pistol','Pistol','pistol'),
        ('rifle','Rifle','rifle'),
        ('shotgun','Shotgun','shotgun'),
        ('assault-weapon','Assault Weapon','assault-weapon'),
        ('rocket','Rocket','rocket'),
        ('very-long','Very Long',NULL),
        ('distant','Distant',NULL),
        ('very-distant','Very Distant',NULL),
        ('extreme','Extreme',NULL),
        ('continental','Continental',NULL)
) source(range_profile_code,profile_name,combat_profile)
JOIN src_locator locator
  ON locator.heading_path=
     'Vehicle-Mounted Weapon Ranges > Attack Difficulties by Weapon Type'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1';

CREATE TABLE rule_vehicle_weapon_range_difficulty (
    range_profile_code text NOT NULL REFERENCES
        rule_vehicle_weapon_range_profile(range_profile_code),
    target_range_code text NOT NULL REFERENCES
        rule_vehicle_weapon_target_range(target_range_code),
    difficulty_rule_id bigint NOT NULL REFERENCES
        rule_difficulty(rule_id),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    PRIMARY KEY (range_profile_code,target_range_code)
);

WITH source(
    range_profile_code,target_range_code,difficulty_code
) AS (
    VALUES
        ('close-quarters','personal','average'),
        ('close-quarters','close','difficult'),
        ('extended-reach','personal','difficult'),
        ('extended-reach','close','average'),
        ('thrown','close','average'),
        ('thrown','short','difficult'),
        ('thrown','medium','difficult'),
        ('pistol','personal','difficult'),
        ('pistol','close','average'),
        ('pistol','short','average'),
        ('pistol','medium','difficult'),
        ('pistol','long','very-difficult'),
        ('rifle','personal','very-difficult'),
        ('rifle','close','difficult'),
        ('rifle','short','average'),
        ('rifle','medium','average'),
        ('rifle','long','average'),
        ('rifle','very-long','difficult'),
        ('rifle','distant','very-difficult'),
        ('shotgun','personal','difficult'),
        ('shotgun','close','average'),
        ('shotgun','short','difficult'),
        ('shotgun','medium','difficult'),
        ('shotgun','long','very-difficult'),
        ('assault-weapon','personal','difficult'),
        ('assault-weapon','close','average'),
        ('assault-weapon','short','average'),
        ('assault-weapon','medium','average'),
        ('assault-weapon','long','difficult'),
        ('assault-weapon','very-long','very-difficult'),
        ('assault-weapon','distant','formidable'),
        ('rocket','personal','very-difficult'),
        ('rocket','close','difficult'),
        ('rocket','short','difficult'),
        ('rocket','medium','average'),
        ('rocket','long','average'),
        ('rocket','very-long','difficult'),
        ('rocket','distant','very-difficult'),
        ('very-long','close','difficult'),
        ('very-long','short','average'),
        ('very-long','medium','difficult'),
        ('very-long','long','very-difficult'),
        ('very-long','very-long','formidable'),
        ('distant','close','very-difficult'),
        ('distant','short','difficult'),
        ('distant','medium','average'),
        ('distant','long','difficult'),
        ('distant','very-long','very-difficult'),
        ('distant','distant','formidable'),
        ('very-distant','close','very-difficult'),
        ('very-distant','short','difficult'),
        ('very-distant','medium','average'),
        ('very-distant','long','average'),
        ('very-distant','very-long','difficult'),
        ('very-distant','distant','very-difficult'),
        ('very-distant','very-distant','formidable'),
        ('extreme','close','formidable'),
        ('extreme','short','very-difficult'),
        ('extreme','medium','difficult'),
        ('extreme','long','average'),
        ('extreme','very-long','average'),
        ('extreme','distant','difficult'),
        ('extreme','very-distant','very-difficult'),
        ('extreme','extreme','formidable'),
        ('continental','close','formidable'),
        ('continental','short','very-difficult'),
        ('continental','medium','difficult'),
        ('continental','long','average'),
        ('continental','very-long','average'),
        ('continental','distant','average'),
        ('continental','very-distant','difficult'),
        ('continental','extreme','very-difficult'),
        ('continental','continental','formidable')
)
INSERT INTO rule_vehicle_weapon_range_difficulty
SELECT source.range_profile_code,source.target_range_code,
       difficulty.rule_id,locator.source_locator_id
FROM source
JOIN rule_rule difficulty
  ON difficulty.rule_code='difficulty.'||source.difficulty_code
JOIN src_locator locator
  ON locator.heading_path=
     'Vehicle-Mounted Weapon Ranges > Attack Difficulties by Weapon Type'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1';

CREATE TABLE rule_vehicle_weapon_family (
    weapon_family_code text PRIMARY KEY CHECK (
        weapon_family_code ~
        '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
    ),
    family_name text NOT NULL UNIQUE,
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_vehicle_weapon_family
SELECT source.weapon_family_code,source.family_name,
       locator.source_locator_id
FROM (
    VALUES
        ('ballista-catapult','Ballista/Catapult'),
        ('mortar','Mortar'),
        ('rocket-artillery','Rocket Artillery'),
        ('artillery-gun','Artillery Gun'),
        ('howitzer','Howitzer'),
        ('machine-gun','Machine Gun'),
        ('autocannon','Autocannon'),
        ('missile-rack','Missile Rack'),
        ('pulse-laser','Pulse Laser'),
        ('mass-driver','Mass Driver'),
        ('railgun','Railgun'),
        ('beam-laser','Beam Laser'),
        ('plasma-gun','Plasma Gun'),
        ('meson-accelerator','Meson Accelerator'),
        ('fusion-gun','Fusion Gun'),
        ('gauss-cannon','Gauss Cannon'),
        ('rapid-pulse-plasma-gun','Rapid Pulse Plasma Gun'),
        ('rapid-pulse-fusion-gun','Rapid Pulse Fusion Gun'),
        ('disintegrator','Disintegrator')
) source(weapon_family_code,family_name)
JOIN src_locator locator
  ON locator.heading_path=
     'Vehicle Design > Vehicle Armaments > Vehicular Weapons'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1';

CREATE TEMP TABLE seed_vehicle_weapon (
    weapon_code text PRIMARY KEY,
    weapon_family_code text NOT NULL,
    minimum_tech_level smallint NOT NULL,
    unit_cost_minor bigint NOT NULL,
    unit_spaces numeric NOT NULL,
    single_shot_rate smallint,
    burst_shot_rate smallint,
    automatic_fire_rate smallint,
    range_profile_code text,
    damage_dice_count smallint,
    blast_radius_metres numeric,
    blast_radius_squares smallint,
    has_recoil boolean NOT NULL,
    illegal_at_law_level smallint NOT NULL
) ON COMMIT DROP;

INSERT INTO seed_vehicle_weapon VALUES
    ('ballista-catapult-tl-1','ballista-catapult',1,1500,6,1,NULL,NULL,'very-long',3,NULL,NULL,true,3),
    ('mortar-tl-2','mortar',2,6000,6,1,NULL,NULL,'distant',3,10,7,true,3),
    ('rocket-artillery-tl-2','rocket-artillery',2,4000,15,1,NULL,NULL,'very-long',2,5,3,false,3),
    ('artillery-gun-tl-3','artillery-gun',3,120000,24,1,NULL,NULL,'very-distant',7,10,7,true,3),
    ('howitzer-tl-3','howitzer',3,60000,12,1,NULL,NULL,'distant',5,10,7,true,3),
    ('artillery-gun-tl-4','artillery-gun',4,160000,24,1,NULL,NULL,'very-distant',8,10,7,true,3),
    ('howitzer-tl-4','howitzer',4,80000,12,1,NULL,NULL,'distant',6,10,7,true,3),
    ('machine-gun-tl-5','machine-gun',5,6000,3,NULL,20,NULL,'rifle',4,NULL,NULL,true,3),
    ('mortar-tl-5','mortar',5,8000,6,1,NULL,NULL,'distant',4,10,7,true,3),
    ('rocket-artillery-tl-5','rocket-artillery',5,6000,15,1,3,NULL,'distant',3,5,3,false,3),
    ('autocannon-tl-6','autocannon',6,200000,24,1,4,NULL,'distant',6,1.5,1,true,3),
    ('missile-rack','missile-rack',6,48000,12,1,3,NULL,NULL,NULL,NULL,NULL,true,3),
    ('artillery-gun-tl-7','artillery-gun',7,240000,24,1,NULL,NULL,'very-distant',10,20,13,true,3),
    ('howitzer-tl-7','howitzer',7,120000,12,1,NULL,NULL,'distant',8,20,13,true,3),
    ('mortar-tl-7','mortar',7,12000,6,1,2,NULL,'distant',6,20,13,true,3),
    ('pulse-laser-tl-7','pulse-laser',7,80000,3,1,6,NULL,'very-distant',6,10,7,false,2),
    ('rocket-artillery-tl-7','rocket-artillery',7,10000,15,1,6,NULL,'distant',5,10,7,false,3),
    ('autocannon-tl-8','autocannon',8,300000,24,1,6,NULL,'distant',8,3,2,true,3),
    ('machine-gun-tl-8','machine-gun',8,9000,3,NULL,100,NULL,'rifle',6,NULL,NULL,true,3),
    ('mass-driver-tl-8','mass-driver',8,250000,180,1,NULL,NULL,'very-distant',10,3,2,true,3),
    ('railgun-tl-8','railgun',8,150000,18,1,3,NULL,'very-distant',6,3,2,true,3),
    ('beam-laser-tl-9','beam-laser',9,100000,3,1,3,NULL,'very-distant',6,10,7,false,2),
    ('artillery-gun-tl-10','artillery-gun',10,280000,24,1,NULL,NULL,'very-distant',11,30,20,true,3),
    ('autocannon-tl-10','autocannon',10,350000,24,1,6,NULL,'distant',9,4.5,3,true,3),
    ('howitzer-tl-10','howitzer',10,140000,12,1,2,NULL,'distant',9,30,20,true,3),
    ('mass-driver-tl-10','mass-driver',10,275000,180,1,NULL,NULL,'very-distant',11,4.5,3,true,3),
    ('mortar-tl-10','mortar',10,14000,6,1,3,NULL,'distant',7,30,20,true,3),
    ('plasma-gun-tl-10','plasma-gun',10,70000,3,1,6,NULL,'very-distant',9,15,10,false,2),
    ('pulse-laser-tl-10','pulse-laser',10,90000,3,1,6,NULL,'very-distant',7,15,10,false,2),
    ('railgun-tl-10','railgun',10,175000,18,1,6,NULL,'very-distant',7,4.5,3,true,3),
    ('rocket-artillery-tl-10','rocket-artillery',10,12000,15,1,12,NULL,'distant',6,15,10,false,3),
    ('beam-laser-tl-11','beam-laser',11,120000,3,1,3,NULL,'very-distant',7,15,10,false,2),
    ('meson-accelerator-tl-11','meson-accelerator',11,180000,12,1,6,NULL,'distant',11,10,7,true,2),
    ('artillery-gun-tl-12','artillery-gun',12,360000,24,1,NULL,NULL,'very-distant',13,40,27,true,3),
    ('fusion-gun-tl-12','fusion-gun',12,180000,3,1,6,NULL,'very-distant',13,40,27,false,2),
    ('gauss-cannon-tl-12','gauss-cannon',12,450000,24,1,10,NULL,'distant',11,6,4,true,3),
    ('howitzer-tl-12','howitzer',12,180000,12,1,2,NULL,'distant',11,40,27,true,3),
    ('mortar-tl-12','mortar',12,18000,6,1,3,NULL,'distant',9,40,27,true,3),
    ('plasma-gun-tl-12','plasma-gun',12,90000,3,1,6,NULL,'very-distant',11,20,13,false,2),
    ('rapid-pulse-plasma-gun-tl-12','rapid-pulse-plasma-gun',12,90000,3,1,12,NULL,'very-distant',11,20,13,false,2),
    ('rocket-artillery-tl-12','rocket-artillery',12,16000,15,1,12,NULL,'distant',8,20,13,false,3),
    ('beam-laser-tl-13','beam-laser',13,160000,3,1,3,NULL,'extreme',9,20,13,false,2),
    ('mass-driver-tl-13','mass-driver',13,325000,180,1,NULL,NULL,'extreme',13,6,4,true,3),
    ('meson-accelerator-tl-13','meson-accelerator',13,180000,12,1,6,NULL,'distant',13,10,7,true,2),
    ('pulse-laser-tl-13','pulse-laser',13,110000,3,1,6,NULL,'extreme',9,20,13,false,2),
    ('railgun-tl-13','railgun',13,225000,18,1,8,NULL,'extreme',9,6,4,true,3),
    ('rapid-pulse-fusion-gun-tl-14','rapid-pulse-fusion-gun',14,360000,3,1,12,NULL,'very-distant',13,40,27,false,2),
    ('artillery-gun-tl-15','artillery-gun',15,400000,24,1,2,NULL,'very-distant',14,50,33,true,3),
    ('fusion-gun-tl-15','fusion-gun',15,200000,3,1,6,NULL,'very-distant',14,50,33,false,2),
    ('gauss-cannon-tl-15','gauss-cannon',15,500000,24,1,15,NULL,'distant',12,7.5,5,true,3),
    ('howitzer-tl-15','howitzer',15,200000,12,1,3,NULL,'distant',12,50,33,true,3),
    ('meson-accelerator-tl-15','meson-accelerator',15,200000,12,1,12,NULL,'distant',14,15,10,true,2),
    ('mortar-tl-15','mortar',15,20000,6,1,4,NULL,'distant',10,50,33,true,3),
    ('plasma-gun-tl-15','plasma-gun',15,100000,3,1,6,NULL,'very-distant',12,25,17,false,2),
    ('pulse-laser-tl-15','pulse-laser',15,120000,3,1,6,NULL,'extreme',10,25,17,false,2),
    ('rapid-pulse-plasma-gun-tl-15','rapid-pulse-plasma-gun',15,100000,3,1,15,NULL,'very-distant',12,25,17,false,2),
    ('rocket-artillery-tl-15','rocket-artillery',15,18000,15,1,12,NULL,'distant',9,25,17,false,3),
    ('beam-laser-tl-16','beam-laser',16,180000,3,1,3,NULL,'extreme',10,25,17,false,2),
    ('mass-driver-tl-16','mass-driver',16,350000,180,1,NULL,NULL,'extreme',14,7.5,5,true,3),
    ('railgun-tl-16','railgun',16,250000,18,1,12,NULL,'extreme',10,7.5,5,true,3),
    ('rapid-pulse-fusion-gun-tl-16','rapid-pulse-fusion-gun',16,400000,3,1,15,NULL,'very-distant',14,50,33,false,2),
    ('artillery-gun-tl-17','artillery-gun',17,800000,24,1,2,NULL,'extreme',17,60,40,false,3),
    ('fusion-gun-tl-17','fusion-gun',17,260000,3,1,6,NULL,'very-distant',17,60,40,false,2),
    ('gauss-cannon-tl-17','gauss-cannon',17,1000000,24,1,15,NULL,'very-distant',15,9,6,false,3),
    ('howitzer-tl-17','howitzer',17,400000,12,1,3,NULL,'very-distant',15,60,40,false,3),
    ('mortar-tl-17','mortar',17,40000,6,1,4,NULL,'distant',13,60,40,false,3),
    ('plasma-gun-tl-17','plasma-gun',17,130000,3,1,6,NULL,'very-distant',15,30,20,false,2),
    ('pulse-laser-tl-17','pulse-laser',17,150000,3,1,6,NULL,'extreme',13,30,20,false,2),
    ('rapid-pulse-plasma-gun-tl-17','rapid-pulse-plasma-gun',17,130000,3,1,24,NULL,'very-distant',15,30,20,false,2),
    ('rocket-artillery-tl-17','rocket-artillery',17,24000,15,1,12,NULL,'very-distant',12,30,20,false,3),
    ('beam-laser-tl-18','beam-laser',18,240000,3,1,3,NULL,'extreme',13,30,20,false,2),
    ('disintegrator-tl-18','disintegrator',18,5000000,24,1,3,NULL,'very-distant',17,9,6,false,2),
    ('mass-driver-tl-18','mass-driver',18,600000,180,1,NULL,NULL,'extreme',17,9,6,false,3),
    ('meson-accelerator-tl-18','meson-accelerator',18,250000,12,1,12,NULL,'very-distant',17,15,10,false,2),
    ('railgun-tl-18','railgun',18,500000,18,1,15,NULL,'extreme',13,9,6,false,3),
    ('rapid-pulse-fusion-gun-tl-18','rapid-pulse-fusion-gun',18,520000,3,1,24,NULL,'very-distant',17,60,40,false,2);

INSERT INTO rule_rule (
    content_package_id,rule_code,name,rule_category,rule_status
)
SELECT package.content_package_id,'vehicle.weapon.'||seed.weapon_code,
       family.family_name||
       CASE
           WHEN seed.weapon_code<>seed.weapon_family_code
               THEN ' TL '||seed.minimum_tech_level
           ELSE ''
       END,
       'vehicle','approved'
FROM seed_vehicle_weapon seed
JOIN rule_vehicle_weapon_family family USING (weapon_family_code)
CROSS JOIN sys_content_package package
WHERE package.package_code='cepheus-engine';

CREATE TABLE rule_vehicle_weapon_definition (
    weapon_rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    weapon_code text NOT NULL UNIQUE CHECK (
        weapon_code ~
        '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
    ),
    weapon_family_code text NOT NULL REFERENCES
        rule_vehicle_weapon_family(weapon_family_code),
    minimum_tech_level smallint NOT NULL CHECK (
        minimum_tech_level>=0
    ),
    unit_cost_minor bigint NOT NULL CHECK (unit_cost_minor>=0),
    unit_spaces numeric NOT NULL CHECK (unit_spaces>0),
    single_shot_rate smallint CHECK (single_shot_rate>0),
    burst_shot_rate smallint CHECK (burst_shot_rate>0),
    automatic_fire_rate smallint CHECK (automatic_fire_rate>0),
    range_profile_code text REFERENCES
        rule_vehicle_weapon_range_profile(range_profile_code),
    range_by_missile boolean NOT NULL,
    damage_dice_count smallint CHECK (damage_dice_count>0),
    damage_die_sides smallint CHECK (damage_die_sides>1),
    damage_by_missile boolean NOT NULL,
    blast_radius_metres numeric CHECK (blast_radius_metres>0),
    blast_radius_squares smallint CHECK (blast_radius_squares>0),
    blast_radius_by_missile boolean NOT NULL,
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
        (range_by_missile AND range_profile_code IS NULL)
        OR
        (NOT range_by_missile AND range_profile_code IS NOT NULL)
    ),
    CHECK (
        (damage_dice_count IS NULL)=(damage_die_sides IS NULL)
    ),
    CHECK (
        (damage_by_missile AND damage_dice_count IS NULL)
        OR
        (NOT damage_by_missile AND damage_dice_count IS NOT NULL)
    ),
    CHECK (
        (blast_radius_metres IS NULL)=
        (blast_radius_squares IS NULL)
    ),
    CHECK (
        NOT blast_radius_by_missile
        OR blast_radius_metres IS NULL
    )
);

INSERT INTO rule_vehicle_weapon_definition
SELECT rule.rule_id,seed.weapon_code,seed.weapon_family_code,
       seed.minimum_tech_level,seed.unit_cost_minor,
       seed.unit_spaces,seed.single_shot_rate,
       seed.burst_shot_rate,seed.automatic_fire_rate,
       seed.range_profile_code,
       seed.weapon_family_code='missile-rack',
       seed.damage_dice_count,
       CASE WHEN seed.damage_dice_count IS NULL
            THEN NULL ELSE 6 END,
       seed.weapon_family_code='missile-rack',
       seed.blast_radius_metres,seed.blast_radius_squares,
       seed.weapon_family_code='missile-rack',
       seed.has_recoil,seed.illegal_at_law_level,
       locator.source_locator_id
FROM seed_vehicle_weapon seed
JOIN rule_rule rule
  ON rule.rule_code='vehicle.weapon.'||seed.weapon_code
JOIN src_locator locator
  ON locator.heading_path=
     'Vehicle Design > Vehicle Armaments > Vehicular Weapons'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1';

WITH source(rule_code,rule_name) AS (
    VALUES
        ('vehicle.weapon-special.disintegrator',
         'Disintegrator Special Rule'),
        ('vehicle.weapon-special.meson',
         'Meson Weapon Special Rule'),
        ('vehicle.weapon-special.pulse',
         'Pulse Weapon Special Rule')
)
INSERT INTO rule_rule (
    content_package_id,rule_code,name,rule_category,rule_status
)
SELECT package.content_package_id,source.rule_code,
       source.rule_name,'vehicle','approved'
FROM source
CROSS JOIN sys_content_package package
WHERE package.package_code='cepheus-engine';

CREATE TABLE rule_vehicle_weapon_special_rule (
    special_rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    special_rule_code text NOT NULL UNIQUE CHECK (
        special_rule_code IN ('disintegrator','meson','pulse')
    ),
    effect_equals_target_armor boolean NOT NULL,
    ignores_armor boolean NOT NULL,
    automatic_crew_radiation_hits smallint NOT NULL CHECK (
        automatic_crew_radiation_hits>=0
    ),
    attack_dm smallint NOT NULL,
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_vehicle_weapon_special_rule
SELECT rule.rule_id,source.special_rule_code,
       source.effect_equals_target_armor,source.ignores_armor,
       source.automatic_radiation_hits,source.attack_dm,
       locator.source_locator_id
FROM (
    VALUES
        ('disintegrator',true,false,0::smallint,0::smallint),
        ('meson',false,true,1,0),
        ('pulse',false,false,0,-2)
) source(
    special_rule_code,effect_equals_target_armor,ignores_armor,
    automatic_radiation_hits,attack_dm
)
JOIN rule_rule rule
  ON rule.rule_code=
     'vehicle.weapon-special.'||source.special_rule_code
JOIN src_locator locator
  ON locator.heading_path=
     'Vehicle Design > Vehicle Armaments > Vehicular Weapons > Special Weapon Rules'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1';

CREATE TABLE rule_vehicle_weapon_family_special_rule (
    weapon_family_code text NOT NULL REFERENCES
        rule_vehicle_weapon_family(weapon_family_code),
    special_rule_id bigint NOT NULL REFERENCES
        rule_vehicle_weapon_special_rule(special_rule_id),
    PRIMARY KEY (weapon_family_code,special_rule_id)
);

INSERT INTO rule_vehicle_weapon_family_special_rule
SELECT source.weapon_family_code,special.special_rule_id
FROM (
    VALUES
        ('disintegrator','disintegrator'),
        ('meson-accelerator','meson'),
        ('pulse-laser','pulse'),
        ('rapid-pulse-plasma-gun','pulse'),
        ('rapid-pulse-fusion-gun','pulse')
) source(weapon_family_code,special_rule_code)
JOIN rule_vehicle_weapon_special_rule special
  USING (special_rule_code);

CREATE TABLE rule_vehicle_weapon_ammunition (
    weapon_family_code text PRIMARY KEY REFERENCES
        rule_vehicle_weapon_family(weapon_family_code),
    price_basis text NOT NULL CHECK (
        price_basis IN ('per-space','by-missile')
    ),
    price_per_space_minor bigint CHECK (
        price_per_space_minor>0
    ),
    rounds_per_space integer NOT NULL CHECK (
        rounds_per_space>0
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    CHECK (
        (price_basis='per-space'
         AND price_per_space_minor IS NOT NULL)
        OR
        (price_basis='by-missile'
         AND price_per_space_minor IS NULL)
    )
);

INSERT INTO rule_vehicle_weapon_ammunition
SELECT source.weapon_family_code,source.price_basis,
       source.price_per_space,source.rounds_per_space,
       locator.source_locator_id
FROM (
    VALUES
        ('artillery-gun','per-space',4000::bigint,25),
        ('autocannon','per-space',4000,25),
        ('ballista-catapult','per-space',100,50),
        ('gauss-cannon','per-space',25000,18000),
        ('howitzer','per-space',2000,25),
        ('machine-gun','per-space',5000,10000),
        ('mass-driver','per-space',9000,2),
        ('missile-rack','by-missile',NULL,1),
        ('mortar','per-space',900,15),
        ('railgun','per-space',900,15),
        ('rocket-artillery','per-space',5000,3)
) source(
    weapon_family_code,price_basis,price_per_space,
    rounds_per_space
)
JOIN src_locator locator
  ON locator.heading_path=
     'Vehicle Design > Vehicle Armaments > Vehicular Weapon Ammunition'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1';

INSERT INTO src_record_provenance (
    rule_id,content_package_id,source_locator_id,
    provenance_class,is_primary_citation
)
SELECT rule.rule_id,rule.content_package_id,
       CASE
           WHEN rule.rule_code LIKE 'vehicle.weapon-special.%'
               THEN special_locator.source_locator_id
           ELSE weapon_locator.source_locator_id
       END,
       'direct',true
FROM rule_rule rule
JOIN src_work work
  ON work.work_code='cepheus-engine.github-v9.1'
LEFT JOIN src_locator weapon_locator
  ON weapon_locator.source_work_id=work.source_work_id
 AND weapon_locator.heading_path=
     'Vehicle Design > Vehicle Armaments > Vehicular Weapons'
LEFT JOIN src_locator special_locator
  ON special_locator.source_work_id=work.source_work_id
 AND special_locator.heading_path=
     'Vehicle Design > Vehicle Armaments > Vehicular Weapons > Special Weapon Rules'
WHERE rule.rule_code LIKE 'vehicle.weapon.%'
   OR rule.rule_code LIKE 'vehicle.weapon-special.%';
