INSERT INTO src_locator (
    source_work_id,source_artifact_id,locator_type,
    heading_path,display_citation
)
SELECT artifact.source_work_id,artifact.source_artifact_id,
       'heading',source.heading_path,source.display_citation
FROM src_artifact artifact
CROSS JOIN (
    VALUES
        ('Ship Design and Construction > Ship Configuration',
         'Cepheus Engine v9.1, Ship Design: Configuration'),
        ('Ship Design and Construction > Ship Armor',
         'Cepheus Engine v9.1, Ship Design: Armor'),
        ('Ship Design and Construction > Ship Drives',
         'Cepheus Engine v9.1, Ship Design: Drives'),
        ('Ship Design and Construction > Fuel',
         'Cepheus Engine v9.1, Ship Design: Fuel'),
        ('Ship Design and Construction > Bridge',
         'Cepheus Engine v9.1, Ship Design: Bridge'),
        ('Ship Design and Construction > Ship Computer',
         'Cepheus Engine v9.1, Ship Design: Computer'),
        ('Ship Design and Construction > Ship Software',
         'Cepheus Engine v9.1, Ship Design: Software'),
        ('Ship Design and Construction > Ship Electronics',
         'Cepheus Engine v9.1, Ship Design: Electronics'),
        ('Ship Design and Construction > Small Craft Design',
         'Cepheus Engine v9.1, Ship Design: Small Craft')
) source(heading_path,display_citation)
WHERE artifact.source_uri=
      'src/book2/ship-design-and-construction.md';

CREATE TABLE rule_ship_hull_design (
    hull_code text PRIMARY KEY CHECK (
        hull_code ~ '^(?:[1-9A-Z]|s[1-9A-HJ])$'
    ),
    craft_scale text NOT NULL CHECK (
        craft_scale IN ('starship','small_craft')
    ),
    hull_tons numeric NOT NULL CHECK (hull_tons>0),
    base_cost_minor bigint NOT NULL CHECK (base_cost_minor>0),
    construction_weeks integer NOT NULL CHECK (construction_weeks>0),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    UNIQUE (craft_scale,hull_tons)
);

INSERT INTO rule_ship_hull_design
SELECT source.*,locator.source_locator_id
FROM (
    VALUES
        ('1','starship',100::numeric,2000000::bigint,36),
        ('2','starship',200,8000000,44),
        ('3','starship',300,12000000,52),
        ('4','starship',400,16000000,60),
        ('5','starship',500,32000000,68),
        ('6','starship',600,48000000,76),
        ('7','starship',700,64000000,84),
        ('8','starship',800,80000000,92),
        ('9','starship',900,90000000,100),
        ('A','starship',1000,100000000,108),
        ('C','starship',1200,120000000,124),
        ('E','starship',1400,140000000,140),
        ('G','starship',1600,160000000,156),
        ('J','starship',1800,180000000,172),
        ('L','starship',2000,200000000,188),
        ('M','starship',3000,300000000,268),
        ('N','starship',4000,400000000,348),
        ('P','starship',5000,500000000,428)
) source(hull_code,craft_scale,hull_tons,base_cost_minor,
         construction_weeks)
JOIN src_locator locator
  ON locator.heading_path='Ship Design and Construction > Ship Hull';

INSERT INTO rule_ship_hull_design
SELECT source.*,locator.source_locator_id
FROM (
    VALUES
        ('s1','small_craft',10::numeric,1100000::bigint,28),
        ('s2','small_craft',15,1150000,29),
        ('s3','small_craft',20,1200000,29),
        ('s4','small_craft',25,1250000,30),
        ('s5','small_craft',30,1300000,30),
        ('s6','small_craft',35,1350000,30),
        ('s7','small_craft',40,1400000,31),
        ('s8','small_craft',45,1450000,31),
        ('s9','small_craft',50,1500000,32),
        ('sA','small_craft',55,1550000,32),
        ('sB','small_craft',60,1600000,32),
        ('sC','small_craft',65,1650000,33),
        ('sD','small_craft',70,1700000,33),
        ('sE','small_craft',75,1750000,34),
        ('sF','small_craft',80,1800000,34),
        ('sG','small_craft',85,1850000,34),
        ('sH','small_craft',90,1900000,35),
        ('sJ','small_craft',95,1950000,35)
) source(hull_code,craft_scale,hull_tons,base_cost_minor,
         construction_weeks)
JOIN src_locator locator
  ON locator.heading_path=
     'Ship Design and Construction > Small Craft Design';

CREATE TABLE rule_ship_configuration (
    configuration_code text PRIMARY KEY CHECK (
        configuration_code IN ('distributed','standard','streamlined')
    ),
    hull_cost_multiplier numeric NOT NULL CHECK (
        hull_cost_multiplier>0
    ),
    atmospheric_operation_dm smallint,
    failed_check_damage_dice smallint CHECK (
        failed_check_damage_dice IS NULL
        OR failed_check_damage_dice>0
    ),
    fuel_scoops_included boolean NOT NULL,
    fuel_scoops_permitted boolean NOT NULL,
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_ship_configuration
SELECT source.*,locator.source_locator_id
FROM (
    VALUES
        ('distributed',0.9::numeric,-4::smallint,2::smallint,false,false),
        ('standard',1,-2,NULL::smallint,false,true),
        ('streamlined',1.1,NULL::smallint,NULL::smallint,true,true)
) source(
    configuration_code,hull_cost_multiplier,
    atmospheric_operation_dm,failed_check_damage_dice,
    fuel_scoops_included,fuel_scoops_permitted
)
JOIN src_locator locator
  ON locator.heading_path=
     'Ship Design and Construction > Ship Configuration';

CREATE TABLE rule_ship_armor_design (
    armor_code text PRIMARY KEY CHECK (
        armor_code IN (
            'titanium-steel','crystaliron','bonded-superdense'
        )
    ),
    minimum_tech_level smallint NOT NULL CHECK (
        minimum_tech_level>=0
    ),
    protection_per_increment smallint NOT NULL CHECK (
        protection_per_increment>0
    ),
    hull_percent_per_increment numeric NOT NULL CHECK (
        hull_percent_per_increment>0
    ),
    minimum_increment_tons numeric NOT NULL CHECK (
        minimum_increment_tons>0
    ),
    base_hull_cost_multiplier numeric NOT NULL CHECK (
        base_hull_cost_multiplier>0
    ),
    small_craft_maximum_rule text NOT NULL CHECK (
        btrim(small_craft_maximum_rule)<>''
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_ship_armor_design
SELECT source.*,locator.source_locator_id
FROM (
    VALUES
        ('titanium-steel',7::smallint,2::smallint,0.05::numeric,
         1::numeric,0.05::numeric,'minimum(tech_level,9)'),
        ('crystaliron',10,4,0.05,1,0.20,'minimum(tech_level,13)'),
        ('bonded-superdense',14,6,0.05,1,0.50,'tech_level')
) source(
    armor_code,minimum_tech_level,protection_per_increment,
    hull_percent_per_increment,minimum_increment_tons,
    base_hull_cost_multiplier,small_craft_maximum_rule
)
JOIN src_locator locator
  ON locator.heading_path=
     'Ship Design and Construction > Ship Armor';

CREATE TABLE rule_ship_armor_option (
    armor_option_code text PRIMARY KEY CHECK (
        armor_option_code IN ('reflec','self-sealing','stealth')
    ),
    minimum_tech_level smallint NOT NULL CHECK (
        minimum_tech_level>=0
    ),
    cost_minor_per_hull_ton bigint NOT NULL CHECK (
        cost_minor_per_hull_ton>=0
    ),
    laser_armor_bonus smallint,
    detection_dm smallint,
    self_sealing boolean NOT NULL,
    maximum_installations smallint NOT NULL CHECK (
        maximum_installations>0
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_ship_armor_option
SELECT source.*,locator.source_locator_id
FROM (
    VALUES
        ('reflec',10::smallint,100000::bigint,3::smallint,
         NULL::smallint,false,1::smallint),
        ('self-sealing',9,10000,NULL,NULL,true,1),
        ('stealth',11,100000,NULL,-4,false,1)
) source(
    armor_option_code,minimum_tech_level,cost_minor_per_hull_ton,
    laser_armor_bonus,detection_dm,self_sealing,
    maximum_installations
)
JOIN src_locator locator
  ON locator.heading_path=
     'Ship Design and Construction > Ship Armor';

CREATE TABLE rule_ship_bridge_band (
    bridge_band_code text PRIMARY KEY,
    minimum_hull_tons numeric NOT NULL CHECK (minimum_hull_tons>0),
    maximum_hull_tons numeric CHECK (
        maximum_hull_tons IS NULL
        OR maximum_hull_tons>=minimum_hull_tons
    ),
    bridge_tons numeric NOT NULL CHECK (bridge_tons>0),
    bridge_cost_minor_per_100_tons bigint NOT NULL CHECK (
        bridge_cost_minor_per_100_tons>=0
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    EXCLUDE USING gist (
        numrange(
            minimum_hull_tons,
            coalesce(maximum_hull_tons+1,'Infinity'::numeric),
            '[)'
        ) WITH &&
    )
);

INSERT INTO rule_ship_bridge_band
SELECT source.*,locator.source_locator_id
FROM (
    VALUES
        ('up-to-200',1::numeric,200::numeric,10::numeric,500000::bigint),
        ('300-to-1000',201,1000,20,500000),
        ('1100-to-2000',1001,2000,40,500000),
        ('over-2000',2001,NULL::numeric,60,500000)
) source(
    bridge_band_code,minimum_hull_tons,maximum_hull_tons,
    bridge_tons,bridge_cost_minor_per_100_tons
)
JOIN src_locator locator
  ON locator.heading_path='Ship Design and Construction > Bridge';

CREATE TABLE rule_ship_computer (
    computer_code text PRIMARY KEY CHECK (
        computer_code ~ '^model-[1-7]$'
    ),
    minimum_tech_level smallint NOT NULL CHECK (
        minimum_tech_level>=0
    ),
    rating smallint NOT NULL CHECK (rating>0),
    cost_minor bigint NOT NULL CHECK (cost_minor>0),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_ship_computer
SELECT source.*,locator.source_locator_id
FROM (
    VALUES
        ('model-1',7::smallint,5::smallint,30000::bigint),
        ('model-2',9,10,160000),
        ('model-3',11,15,2000000),
        ('model-4',12,20,5000000),
        ('model-5',13,25,10000000),
        ('model-6',14,30,20000000),
        ('model-7',15,35,30000000)
) source(
    computer_code,minimum_tech_level,rating,cost_minor
)
JOIN src_locator locator
  ON locator.heading_path=
     'Ship Design and Construction > Ship Computer';

CREATE TABLE rule_ship_computer_option (
    computer_option_code text PRIMARY KEY CHECK (
        computer_option_code IN ('bis','fib')
    ),
    cost_multiplier_increment numeric NOT NULL CHECK (
        cost_multiplier_increment>0
    ),
    jump_control_rating_bonus smallint NOT NULL DEFAULT 0,
    emp_immune boolean NOT NULL DEFAULT false,
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_ship_computer_option
SELECT source.*,locator.source_locator_id
FROM (
    VALUES
        ('bis',0.5::numeric,5::smallint,false),
        ('fib',0.5::numeric,0::smallint,true)
) source(
    computer_option_code,cost_multiplier_increment,
    jump_control_rating_bonus,emp_immune
)
JOIN src_locator locator
  ON locator.heading_path=
     'Ship Design and Construction > Ship Computer';

CREATE TABLE rule_ship_software (
    software_code text PRIMARY KEY CHECK (
        software_code IN (
            'auto-repair','evade','fire-control',
            'jump-control','jump-course-tape'
        )
    ),
    minimum_tech_level smallint NOT NULL CHECK (
        minimum_tech_level>=0
    ),
    rating_base smallint NOT NULL CHECK (rating_base>=0),
    rating_per_level smallint NOT NULL CHECK (rating_per_level>0),
    cost_minor_per_level bigint NOT NULL CHECK (
        cost_minor_per_level>=0
    ),
    maximum_level smallint CHECK (maximum_level>0),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_ship_software
SELECT source.*,locator.source_locator_id
FROM (
    VALUES
        ('auto-repair',10::smallint,0::smallint,10::smallint,
         5000000::bigint,NULL::smallint),
        ('evade',9,0,5,1000000,3),
        ('fire-control',9,0,5,2000000,5),
        ('jump-control',9,0,5,100000,NULL),
        ('jump-course-tape',9,0,1,1000,NULL)
) source(
    software_code,minimum_tech_level,rating_base,rating_per_level,
    cost_minor_per_level,maximum_level
)
JOIN src_locator locator
  ON locator.heading_path=
     'Ship Design and Construction > Ship Software';

CREATE TABLE rule_ship_electronics_suite (
    electronics_code text PRIMARY KEY CHECK (
        electronics_code IN (
            'standard','basic-civilian','basic-military',
            'advanced','very-advanced'
        )
    ),
    minimum_tech_level smallint NOT NULL CHECK (
        minimum_tech_level>=0
    ),
    communications_dm smallint NOT NULL,
    unit_tons numeric NOT NULL CHECK (unit_tons>=0),
    cost_minor bigint NOT NULL CHECK (cost_minor>=0),
    radar_lidar boolean NOT NULL,
    jammers boolean NOT NULL,
    densitometer boolean NOT NULL,
    neural_activity_sensor boolean NOT NULL,
    included_in_bridge boolean NOT NULL,
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_ship_electronics_suite
SELECT source.*,locator.source_locator_id
FROM (
    VALUES
        ('standard',8::smallint,-4::smallint,0::numeric,0::bigint,
         true,false,false,false,true),
        ('basic-civilian',9,-2,1,50000,true,false,false,false,false),
        ('basic-military',10,0,2,1000000,true,true,false,false,false),
        ('advanced',11,1,3,2000000,true,true,true,false,false),
        ('very-advanced',12,2,5,4000000,true,true,true,true,false)
) source(
    electronics_code,minimum_tech_level,communications_dm,
    unit_tons,cost_minor,radar_lidar,jammers,densitometer,
    neural_activity_sensor,included_in_bridge
)
JOIN src_locator locator
  ON locator.heading_path=
     'Ship Design and Construction > Ship Electronics';
