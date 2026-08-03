INSERT INTO src_locator (
    source_work_id,source_artifact_id,locator_type,
    heading_path,display_citation
)
SELECT artifact.source_work_id,artifact.source_artifact_id,
       'heading','Common Vessels > '||source.heading,
       'Cepheus Engine v9.1, Common Vessels: '||source.heading
FROM src_artifact artifact
CROSS JOIN (
    VALUES
        ('TL9 Asteroid Miner'),('TL11 Corvette'),('TL9 Courier'),
        ('TL11 Destroyer'),('TL14 Dreadnought'),('TL9 Frontier Trader'),
        ('TL11 Heavy Cruiser'),('TL11 Light Cruiser'),
        ('TL9 Merchant Freighter'),('TL9 Merchant Liner'),
        ('TL9 Merchant Trader'),('TL11 Patrol Frigate'),('TL9 Raider'),
        ('TL9 Research Vessel'),('TL11 Survey Vessel'),
        ('TL9 System Defense Boat'),('TL9 System Monitor'),('TL9 Yacht'),
        ('TL9 Cutter'),('TL9 Fighter'),('TL9 Launch'),('TL9 Pinnace'),
        ('TL9 Ship''s Boat'),('TL9 Shuttle')
) source(heading)
WHERE artifact.source_uri='src/book2/common-vessels.md';

ALTER TABLE ship_class
    DROP CONSTRAINT ship_class_hull_points_check,
    ADD CONSTRAINT ship_class_hull_points_check CHECK (hull_points>=0),
    ADD COLUMN craft_scale text NOT NULL DEFAULT 'starship' CHECK (
        craft_scale IN ('starship','small_craft')
    );

ALTER TABLE ship_class_characteristic
    DROP CONSTRAINT ship_class_characteristic_characteristic_value_check,
    ADD CONSTRAINT ship_class_characteristic_characteristic_value_check CHECK (
        (characteristic_code='sensors'
         AND characteristic_value BETWEEN -6 AND 6)
        OR
        (characteristic_code<>'sensors' AND characteristic_value>=0)
    );

CREATE TABLE ship_class_source_assertion (
    ship_class_rule_id bigint NOT NULL REFERENCES
        ship_class(ship_class_rule_id),
    field_code text NOT NULL CHECK (
        field_code ~ '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
    ),
    published_value text NOT NULL CHECK (btrim(published_value)<>''),
    canonical_value text CHECK (
        canonical_value IS NULL OR btrim(canonical_value)<>''
    ),
    assertion_status text NOT NULL CHECK (
        assertion_status IN ('accepted','reconciled','unresolved_conflict')
    ),
    rationale text NOT NULL CHECK (btrim(rationale)<>''),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    PRIMARY KEY (ship_class_rule_id,field_code)
);

INSERT INTO rule_rule (
    content_package_id,rule_code,name,rule_category,rule_status
)
SELECT package.content_package_id,'ship.class.'||source.class_code,
       source.class_name,'ship','approved'
FROM sys_content_package package
CROSS JOIN (
    VALUES
        ('asteroid-miner','Asteroid Miner'),('corvette','Corvette'),
        ('courier','Courier'),('destroyer','Destroyer'),
        ('dreadnought','Dreadnought'),('frontier-trader','Frontier Trader'),
        ('heavy-cruiser','Heavy Cruiser'),('light-cruiser','Light Cruiser'),
        ('merchant-freighter','Merchant Freighter'),
        ('merchant-liner','Merchant Liner'),
        ('merchant-trader','Merchant Trader'),
        ('patrol-frigate','Patrol Frigate'),('raider','Raider'),
        ('research-vessel','Research Vessel'),('survey-vessel','Survey Vessel'),
        ('system-defense-boat','System Defense Boat'),
        ('system-monitor','System Monitor'),('yacht','Yacht'),
        ('cutter','Cutter'),('fighter','Fighter'),('launch','Launch'),
        ('pinnace','Pinnace'),('ships-boat','Ship''s Boat'),
        ('shuttle','Shuttle')
) source(class_code,class_name)
WHERE package.package_code='cepheus-engine';

INSERT INTO ship_class (
    ship_class_rule_id,class_code,hull_tons,hull_points,
    structure_points,minimum_tech_level,construction_cost_minor,
    jump_rating,maneuver_rating,power_rating,cargo_capacity_tons,
    hull_configuration,construction_weeks,standard_design,
    source_locator_id,craft_scale
)
SELECT rule.rule_id,source.class_code,source.hull_tons,
       source.hull_points,source.structure_points,source.minimum_tl,
       source.cost_minor,source.jump_rating,source.maneuver_rating,
       source.power_rating,source.cargo_tons,source.configuration_code,
       source.construction_weeks,true,locator.source_locator_id,
       source.craft_scale
FROM (
    VALUES
        ('asteroid-miner','TL9 Asteroid Miner',200::numeric,4::smallint,
         4::smallint,9::smallint,33219000::bigint,1::smallint,1::smallint,
         1::smallint,84::numeric,'standard',44,'starship'),
        ('corvette','TL11 Corvette',300,6,6,11,194445000,2,6,6,25,
         'standard',52,'starship'),
        ('courier','TL9 Courier',100,2,2,9,35928000,2,4,4,16,
         'streamlined',36,'starship'),
        ('destroyer','TL11 Destroyer',800,16,16,11,422775000,2,4,4,50.5,
         'standard',92,'starship'),
        ('dreadnought','TL14 Dreadnought',5000,100,100,14,2768145000,
         2,2,2,412,'standard',428,'starship'),
        ('frontier-trader','TL9 Frontier Trader',300,6,6,9,82314000,
         1,2,2,75,'standard',13,'starship'),
        ('heavy-cruiser','TL11 Heavy Cruiser',2000,40,40,11,1146915000,
         2,2,2,152.5,'standard',47,'starship'),
        ('light-cruiser','TL11 Light Cruiser',1000,20,20,11,597870000,
         2,3,3,53,'standard',27,'starship'),
        ('merchant-freighter','TL9 Merchant Freighter',400,8,8,9,59814000,
         1,1,1,261,'standard',60,'starship'),
        ('merchant-liner','TL9 Merchant Liner',300,6,6,9,70209000,
         1,1,1,46,'standard',52,'starship'),
        ('merchant-trader','TL9 Merchant Trader',200,4,4,9,34929000,
         1,1,1,85,'standard',44,'starship'),
        ('patrol-frigate','TL11 Patrol Frigate',300,6,6,11,180675000,
         2,4,4,23,'standard',52,'starship'),
        ('raider','TL9 Raider',600,12,12,9,310851000,1,4,4,125,
         'standard',76,'starship'),
        ('research-vessel','TL9 Research Vessel',200,4,4,9,73809000,
         1,1,1,29,'standard',44,'starship'),
        ('survey-vessel','TL11 Survey Vessel',300,6,6,11,120969000,
         1,2,2,39,'standard',52,'starship'),
        ('system-defense-boat','TL9 System Defense Boat',400,8,8,9,
         171574000,0,6,6,109,'streamlined',60,'starship'),
        ('system-monitor','TL9 System Monitor',1000,20,20,9,610461000,
         0,6,6,123.5,'standard',108,'starship'),
        ('yacht','TL9 Yacht',100,2,2,9,26388000,2,2,2,12,
         'streamlined',36,'starship'),
        ('cutter','TL9 Cutter',50,1,1,9,24305000,0,4,4,1.3,
         'standard',32,'small_craft'),
        ('fighter','TL9 Fighter',10,0,1,9,10841000,0,6,6,0,
         'streamlined',28,'small_craft'),
        ('launch','TL9 Launch',20,0,1,9,4797000,0,1,1,10.9,
         'standard',29,'small_craft'),
        ('pinnace','TL9 Pinnace',40,0,1,9,18567000,0,5,5,25,
         'standard',31,'small_craft'),
        ('ships-boat','TL9 Ship''s Boat',30,0,1,9,16677000,0,6,6,16.7,
         'standard',30,'small_craft'),
        ('shuttle','TL9 Shuttle',90,1,1,9,25587000,0,3,3,67.4,
         'standard',35,'small_craft')
) source(
    class_code,heading,hull_tons,hull_points,structure_points,
    minimum_tl,cost_minor,jump_rating,maneuver_rating,power_rating,
    cargo_tons,configuration_code,construction_weeks,craft_scale
)
JOIN rule_rule rule
  ON rule.rule_code='ship.class.'||source.class_code
JOIN src_locator locator
  ON locator.heading_path='Common Vessels > '||source.heading;

INSERT INTO ship_class_characteristic (
    ship_class_rule_id,characteristic_code,characteristic_value
)
SELECT rule.rule_id,fact.characteristic_code,fact.characteristic_value
FROM (
    VALUES
        ('asteroid-miner',2,2,-2,44,3,5,2,3),
        ('corvette',8,3,1,96,9,5,3,18),
        ('courier',2,2,-2,28,4,1,1,3),
        ('destroyer',11,3,1,368,12,6,8,23),
        ('dreadnought',14,6,2,1096,101,279,50,223),
        ('frontier-trader',2,2,-2,42,25,12,3,8),
        ('heavy-cruiser',11,3,1,452,42,20,20,79),
        ('light-cruiser',11,3,1,344,23,11,10,43),
        ('merchant-freighter',2,2,-2,48,4,2,4,3),
        ('merchant-liner',2,2,-2,38,35,20,3,7),
        ('merchant-trader',2,2,-2,24,10,20,2,3),
        ('patrol-frigate',8,3,1,84,10,5,3,20),
        ('raider',8,2,-2,108,12,6,6,24),
        ('research-vessel',2,2,-2,24,6,3,2,9),
        ('survey-vessel',2,2,-2,72,8,4,3,14),
        ('system-defense-boat',8,2,-2,48,10,5,4,18),
        ('system-monitor',9,2,-2,88,24,12,10,45),
        ('yacht',2,2,-2,24,6,3,1,3),
        ('cutter',0,1,-4,1.3,0,0,1,1),
        ('fighter',0,1,-4,1.5,0,0,1,1),
        ('launch',0,1,-4,0.4,0,0,1,1),
        ('pinnace',0,1,-4,1.5,0,0,1,1),
        ('ships-boat',0,1,-4,1.2,0,0,1,1),
        ('shuttle',0,1,-4,1.9,0,0,1,2)
) source(
    class_code,armor,computer,sensors,fuel_tons,staterooms,
    low_berths,hardpoints,crew
)
JOIN rule_rule rule
  ON rule.rule_code='ship.class.'||source.class_code
CROSS JOIN LATERAL (
    VALUES
        ('armor',source.armor::numeric),
        ('computer',source.computer::numeric),
        ('sensors',source.sensors::numeric),
        ('fuel_tons',source.fuel_tons::numeric),
        ('staterooms',source.staterooms::numeric),
        ('low_berths',source.low_berths::numeric),
        ('hardpoints',source.hardpoints::numeric),
        ('crew',source.crew::numeric)
) fact(characteristic_code,characteristic_value);

INSERT INTO ship_class_source_assertion (
    ship_class_rule_id,field_code,published_value,canonical_value,
    assertion_status,rationale,source_locator_id
)
SELECT rule.rule_id,source.field_code,source.published_value,
       source.canonical_value,'reconciled',source.rationale,
       locator.source_locator_id
FROM (
    VALUES
        ('raider','hull-points','6','12',
         'The 600-ton hull formula gives 12 Hull and 12 Structure; the common-vessel paragraph repeats 6 for both.'),
        ('raider','hardpoints','3','6',
         'A 600-ton hull provides six hardpoints and the same paragraph installs six triple turrets.'),
        ('system-monitor','maneuver-drive','drivexand','X',
         'The run-together text is reconciled with power plant X and the published 6-G performance matrix.')
) source(class_code,field_code,published_value,canonical_value,rationale)
JOIN rule_rule rule
  ON rule.rule_code='ship.class.'||source.class_code
JOIN ship_class class
  ON class.ship_class_rule_id=rule.rule_id
JOIN src_locator locator
  ON locator.source_locator_id=class.source_locator_id;

INSERT INTO src_record_provenance (
    rule_id,content_package_id,source_locator_id,
    provenance_class,is_primary_citation
)
SELECT rule.rule_id,rule.content_package_id,class.source_locator_id,
       'direct',true
FROM rule_rule rule
JOIN ship_class class
  ON class.ship_class_rule_id=rule.rule_id
WHERE rule.rule_code LIKE 'ship.class.%';
