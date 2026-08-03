CREATE TABLE rule_world_size (
    size_code smallint PRIMARY KEY CHECK (size_code BETWEEN 0 AND 10),
    diameter_kilometres integer NOT NULL CHECK (diameter_kilometres>0),
    surface_gravity_g numeric(4,2),
    descriptor text CHECK (descriptor IS NULL OR btrim(descriptor)<>'')
);

INSERT INTO rule_world_size VALUES
    (0,800,NULL,'Typically an asteroid'),
    (1,1600,0.05,NULL),(2,3200,0.15,NULL),
    (3,4800,0.25,NULL),(4,6400,0.35,NULL),
    (5,8000,0.45,NULL),(6,9600,0.70,NULL),
    (7,11200,0.90,NULL),(8,12800,1.00,NULL),
    (9,14400,1.25,NULL),(10,16000,1.40,NULL);

CREATE TABLE rule_world_atmosphere (
    atmosphere_code smallint PRIMARY KEY CHECK (
        atmosphere_code BETWEEN 0 AND 15
    ),
    name text NOT NULL UNIQUE CHECK (btrim(name)<>''),
    pressure_minimum_atmospheres numeric(5,3),
    pressure_maximum_atmospheres numeric(5,3),
    pressure_varies boolean NOT NULL,
    tainted boolean NOT NULL,
    CHECK (
        pressure_minimum_atmospheres IS NULL
        OR pressure_maximum_atmospheres IS NULL
        OR pressure_minimum_atmospheres<=pressure_maximum_atmospheres
    )
);

INSERT INTO rule_world_atmosphere VALUES
    (0,'None',0.000,0.000,false,false),
    (1,'Trace',0.001,0.090,false,false),
    (2,'Very Thin, Tainted',0.100,0.420,false,true),
    (3,'Very Thin',0.100,0.420,false,false),
    (4,'Thin, Tainted',0.430,0.700,false,true),
    (5,'Thin',0.430,0.700,false,false),
    (6,'Standard',0.710,1.490,false,false),
    (7,'Standard, Tainted',0.710,1.490,false,true),
    (8,'Dense',1.500,2.490,false,false),
    (9,'Dense, Tainted',1.500,2.490,false,true),
    (10,'Exotic',NULL,NULL,true,false),
    (11,'Corrosive',NULL,NULL,true,false),
    (12,'Insidious',NULL,NULL,true,false),
    (13,'Dense, High',2.500,NULL,false,false),
    (14,'Thin, Low',NULL,0.500,false,false),
    (15,'Unusual',NULL,NULL,true,false);

CREATE TABLE rule_atmosphere_survival_requirement (
    atmosphere_code smallint NOT NULL REFERENCES
        rule_world_atmosphere(atmosphere_code),
    requirement_code text NOT NULL CHECK (
        requirement_code IN (
            'vacc_suit','respirator','filter','air_supply','varies'
        )
    ),
    PRIMARY KEY (atmosphere_code,requirement_code)
);

INSERT INTO rule_atmosphere_survival_requirement VALUES
    (0,'vacc_suit'),(1,'vacc_suit'),
    (2,'respirator'),(2,'filter'),(3,'respirator'),
    (4,'filter'),(7,'filter'),(9,'filter'),
    (10,'air_supply'),(11,'vacc_suit'),(12,'vacc_suit'),
    (15,'varies');

CREATE TABLE rule_world_hydrographics (
    hydrographics_code smallint PRIMARY KEY CHECK (
        hydrographics_code BETWEEN 0 AND 10
    ),
    minimum_percent smallint NOT NULL CHECK (
        minimum_percent BETWEEN 0 AND 100
    ),
    maximum_percent smallint NOT NULL CHECK (
        maximum_percent BETWEEN 0 AND 100
    ),
    descriptor text CHECK (descriptor IS NULL OR btrim(descriptor)<>''),
    CHECK (minimum_percent<=maximum_percent)
);

INSERT INTO rule_world_hydrographics VALUES
    (0,0,5,'Desert world'),(1,6,15,'Dry world'),
    (2,16,25,'A few small seas'),(3,26,35,'Small seas and oceans'),
    (4,36,45,'Wet world'),(5,46,55,'Large oceans'),
    (6,56,65,NULL),(7,66,75,'Earth-like world'),
    (8,76,85,'Water world'),
    (9,86,95,'Only small islands and archipelagos'),
    (10,96,100,'Almost entirely water');

CREATE TABLE rule_world_population (
    population_code smallint PRIMARY KEY CHECK (
        population_code BETWEEN 0 AND 10
    ),
    minimum_population bigint NOT NULL CHECK (minimum_population>=0),
    descriptor text NOT NULL CHECK (btrim(descriptor)<>'')
);

INSERT INTO rule_world_population VALUES
    (0,0,'None'),(1,10,'Few'),(2,100,'Hundreds'),
    (3,1000,'Thousands'),(4,10000,'Tens of thousands'),
    (5,100000,'Hundreds of thousands'),(6,1000000,'Millions'),
    (7,10000000,'Tens of millions'),
    (8,100000000,'Hundreds of millions'),
    (9,1000000000,'Billions'),
    (10,10000000000,'Tens of billions');

CREATE TABLE rule_starport_class (
    starport_code text PRIMARY KEY CHECK (
        starport_code IN ('A','B','C','D','E','X')
    ),
    descriptor text NOT NULL UNIQUE,
    best_fuel text NOT NULL CHECK (
        best_fuel IN ('refined','unrefined','none')
    ),
    annual_maintenance boolean NOT NULL,
    shipyard_capability text NOT NULL CHECK (
        shipyard_capability IN (
            'starships','non_starships','repairs','none'
        )
    )
);

INSERT INTO rule_starport_class VALUES
    ('A','Excellent','refined',true,'starships'),
    ('B','Good','refined',true,'non_starships'),
    ('C','Routine','unrefined',false,'repairs'),
    ('D','Poor','unrefined',false,'none'),
    ('E','Frontier','none',false,'none'),
    ('X','None','none',false,'none');

CREATE TABLE rule_world_government (
    government_code smallint PRIMARY KEY CHECK (
        government_code BETWEEN 0 AND 15
    ),
    name text NOT NULL UNIQUE CHECK (btrim(name)<>'')
);

INSERT INTO rule_world_government VALUES
    (0,'None'),(1,'Company/Corporation'),
    (2,'Participating Democracy'),(3,'Self-Perpetuating Oligarchy'),
    (4,'Representative Democracy'),(5,'Feudal Technocracy'),
    (6,'Captive Government'),(7,'Balkanization'),
    (8,'Civil Service Bureaucracy'),(9,'Impersonal Bureaucracy'),
    (10,'Charismatic Dictator'),(11,'Non-Charismatic Leader'),
    (12,'Charismatic Oligarchy'),(13,'Religious Dictatorship'),
    (14,'Religious Autocracy'),(15,'Totalitarian Oligarchy');

CREATE TABLE rule_world_law_level (
    law_level_code smallint PRIMARY KEY CHECK (law_level_code>=0),
    descriptor text NOT NULL CHECK (btrim(descriptor)<>''),
    prohibited_description text NOT NULL CHECK (
        btrim(prohibited_description)<>''
    )
);

INSERT INTO rule_world_law_level VALUES
    (0,'No Law','No restrictions'),
    (1,'Low Law','Poison gas, explosives and mass-destruction weapons'),
    (2,'Low Law','Portable energy weapons'),
    (3,'Low Law','Heavy weapons'),
    (4,'Medium Law','Light assault weapons and submachine guns'),
    (5,'Medium Law','Personal concealable weapons'),
    (6,'Medium Law','Firearms except shotguns and stunners'),
    (7,'High Law','Shotguns'),
    (8,'High Law','Bladed weapons and stunners'),
    (9,'High Law','Weapons outside one''s residence'),
    (10,'Extreme Law','Any weapons'),(11,'Extreme Law','Any weapons'),
    (12,'Extreme Law','Any weapons'),(13,'Extreme Law','Any weapons'),
    (14,'Extreme Law','Any weapons'),(15,'Extreme Law','Any weapons');

INSERT INTO rule_rule (
    content_package_id,rule_code,name,rule_category,rule_status
)
SELECT package.content_package_id,
       'world.trade-code.'||source.slug,
       source.name,'world','approved'
FROM sys_content_package package
CROSS JOIN (
    VALUES
        ('agricultural','Agricultural'),('asteroid','Asteroid'),
        ('barren','Barren'),('desert','Desert'),
        ('fluid-oceans','Fluid Oceans'),('garden','Garden'),
        ('high-population','High Population'),
        ('high-technology','High Technology'),
        ('ice-capped','Ice-Capped'),('industrial','Industrial'),
        ('low-population','Low Population'),
        ('low-technology','Low Technology'),
        ('non-agricultural','Non-Agricultural'),
        ('non-industrial','Non-Industrial'),('poor','Poor'),
        ('rich','Rich'),('water-world','Water World'),
        ('vacuum','Vacuum')
) source(slug,name)
WHERE package.package_code='cepheus-engine';

INSERT INTO loc_trade_code(trade_code_rule_id,trade_code)
SELECT rule.rule_id,source.trade_code
FROM rule_rule rule
JOIN (
    VALUES
        ('world.trade-code.agricultural','Ag'),
        ('world.trade-code.asteroid','As'),
        ('world.trade-code.barren','Ba'),
        ('world.trade-code.desert','De'),
        ('world.trade-code.fluid-oceans','Fl'),
        ('world.trade-code.garden','Ga'),
        ('world.trade-code.high-population','Hi'),
        ('world.trade-code.high-technology','Ht'),
        ('world.trade-code.ice-capped','Ic'),
        ('world.trade-code.industrial','In'),
        ('world.trade-code.low-population','Lo'),
        ('world.trade-code.low-technology','Lt'),
        ('world.trade-code.non-agricultural','Na'),
        ('world.trade-code.non-industrial','Ni'),
        ('world.trade-code.poor','Po'),
        ('world.trade-code.rich','Ri'),
        ('world.trade-code.water-world','Wa'),
        ('world.trade-code.vacuum','Va')
) source(rule_code,trade_code)
  ON source.rule_code=rule.rule_code;

ALTER TABLE loc_world_profile
    ADD CONSTRAINT loc_world_profile_starport_definition_fkey
        FOREIGN KEY (starport_code)
        REFERENCES rule_starport_class(starport_code),
    ADD CONSTRAINT loc_world_profile_size_definition_fkey
        FOREIGN KEY (size_code) REFERENCES rule_world_size(size_code),
    ADD CONSTRAINT loc_world_profile_atmosphere_definition_fkey
        FOREIGN KEY (atmosphere_code)
        REFERENCES rule_world_atmosphere(atmosphere_code),
    ADD CONSTRAINT loc_world_profile_hydrographics_definition_fkey
        FOREIGN KEY (hydrographics_code)
        REFERENCES rule_world_hydrographics(hydrographics_code),
    ADD CONSTRAINT loc_world_profile_population_definition_fkey
        FOREIGN KEY (population_code)
        REFERENCES rule_world_population(population_code),
    ADD CONSTRAINT loc_world_profile_government_definition_fkey
        FOREIGN KEY (government_code)
        REFERENCES rule_world_government(government_code);

CREATE TABLE rule_jump_travel_system (
    jump_system_code text PRIMARY KEY,
    safe_distance_diameters smallint NOT NULL CHECK (
        safe_distance_diameters>0
    ),
    duration_base_hours smallint NOT NULL CHECK (duration_base_hours>0),
    duration_dice_count smallint NOT NULL CHECK (duration_dice_count>0),
    duration_die_sides smallint NOT NULL CHECK (duration_die_sides>1),
    success_target smallint NOT NULL,
    misjump_maximum_result smallint NOT NULL,
    inaccurate_jump_extra_dice_count smallint NOT NULL,
    inaccurate_jump_extra_die_sides smallint NOT NULL,
    fuel_unrefined_modifier smallint NOT NULL,
    within_limit_modifier smallint NOT NULL
);

INSERT INTO rule_jump_travel_system VALUES
    ('cepheus-standard',100,148,6,6,8,0,1,6,-2,-8);

CREATE TABLE rule_passage_class (
    passage_class text PRIMARY KEY CHECK (
        passage_class IN ('high','middle','low','working','stowaway')
    ),
    price_credits integer CHECK (price_credits>=0),
    baggage_allowance_kg integer CHECK (baggage_allowance_kg>=0),
    maximum_working_jumps smallint CHECK (maximum_working_jumps>0)
);

INSERT INTO rule_passage_class VALUES
    ('high',10000,1000,NULL),('middle',8000,100,NULL),
    ('low',1000,10,NULL),('working',NULL,1000,3),
    ('stowaway',0,NULL,NULL);

CREATE TABLE rule_fuel_type (
    fuel_type_code text PRIMARY KEY CHECK (
        fuel_type_code IN ('refined','unrefined')
    ),
    starport_price_per_ton integer NOT NULL CHECK (
        starport_price_per_ton>=0
    ),
    jump_success_modifier smallint NOT NULL
);

INSERT INTO rule_fuel_type VALUES
    ('refined',500,0),('unrefined',100,-2);

CREATE TABLE rule_starport_traffic_expression (
    starport_code text NOT NULL REFERENCES
        rule_starport_class(starport_code),
    traffic_kind text NOT NULL CHECK (
        traffic_kind IN (
            'freight_tons','high_passengers',
            'middle_passengers','low_passengers'
        )
    ),
    dice_count smallint NOT NULL CHECK (dice_count>=0),
    die_sides smallint NOT NULL CHECK (die_sides>=0),
    flat_modifier smallint NOT NULL DEFAULT 0,
    multiplier smallint NOT NULL DEFAULT 1 CHECK (multiplier>0),
    PRIMARY KEY (starport_code,traffic_kind),
    CHECK (
        (dice_count=0 AND die_sides=0)
        OR (dice_count>0 AND die_sides>1)
    )
);

INSERT INTO rule_starport_traffic_expression VALUES
    ('A','freight_tons',3,6,0,10),
    ('A','high_passengers',3,6,0,1),
    ('A','middle_passengers',3,6,0,1),
    ('A','low_passengers',3,6,0,3),
    ('B','freight_tons',3,6,0,5),
    ('B','high_passengers',2,6,0,1),
    ('B','middle_passengers',3,6,0,1),
    ('B','low_passengers',3,6,0,3),
    ('C','freight_tons',3,6,0,2),
    ('C','high_passengers',1,6,-1,1),
    ('C','middle_passengers',2,6,0,1),
    ('C','low_passengers',3,6,0,1),
    ('D','freight_tons',3,6,0,1),
    ('D','high_passengers',0,0,0,1),
    ('D','middle_passengers',1,6,-1,1),
    ('D','low_passengers',2,6,0,1),
    ('E','freight_tons',1,6,0,1),
    ('E','high_passengers',0,0,0,1),
    ('E','middle_passengers',1,3,-1,1),
    ('E','low_passengers',1,6,-1,1),
    ('X','freight_tons',0,0,0,1),
    ('X','high_passengers',0,0,0,1),
    ('X','middle_passengers',0,0,0,1),
    ('X','low_passengers',0,0,0,1);
