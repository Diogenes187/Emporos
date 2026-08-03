CREATE TABLE rule_ship_drive_design (
    drive_code text NOT NULL CHECK (
        drive_code ~ '^(?:[A-HJ-NP-Z]|s[A-HJ-NP-W])$'
    ),
    craft_scale text NOT NULL CHECK (
        craft_scale IN ('starship','small_craft')
    ),
    jump_drive_tons numeric CHECK (jump_drive_tons>0),
    jump_drive_cost_minor bigint CHECK (jump_drive_cost_minor>0),
    maneuver_drive_tons numeric NOT NULL CHECK (
        maneuver_drive_tons>0
    ),
    maneuver_drive_cost_minor bigint NOT NULL CHECK (
        maneuver_drive_cost_minor>0
    ),
    power_plant_tons numeric NOT NULL CHECK (power_plant_tons>0),
    power_plant_cost_minor bigint NOT NULL CHECK (
        power_plant_cost_minor>0
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    PRIMARY KEY (craft_scale,drive_code),
    CHECK (
        (craft_scale='starship'
         AND jump_drive_tons IS NOT NULL
         AND jump_drive_cost_minor IS NOT NULL)
        OR
        (craft_scale='small_craft'
         AND jump_drive_tons IS NULL
         AND jump_drive_cost_minor IS NULL)
    )
);

INSERT INTO rule_ship_drive_design
SELECT source.drive_code,'starship',
       source.jump_drive_tons,source.jump_drive_cost_minor,
       source.maneuver_drive_tons,source.maneuver_drive_cost_minor,
       source.power_plant_tons,source.power_plant_cost_minor,
       locator.source_locator_id
FROM (
    VALUES
        ('A',10::numeric,10000000::bigint,2::numeric,4000000::bigint,4::numeric,8000000::bigint),
        ('B',15,20000000,3,8000000,7,16000000),
        ('C',20,30000000,5,12000000,10,24000000),
        ('D',25,40000000,7,16000000,13,32000000),
        ('E',30,50000000,9,20000000,16,40000000),
        ('F',35,60000000,11,24000000,19,48000000),
        ('G',40,70000000,13,28000000,22,56000000),
        ('H',45,80000000,15,32000000,25,64000000),
        ('J',50,90000000,17,36000000,28,72000000),
        ('K',55,100000000,19,40000000,31,80000000),
        ('L',60,110000000,21,44000000,34,88000000),
        ('M',65,120000000,23,48000000,37,96000000),
        ('N',70,130000000,25,52000000,40,104000000),
        ('P',75,140000000,27,56000000,43,112000000),
        ('Q',80,150000000,29,60000000,46,120000000),
        ('R',85,160000000,31,64000000,49,128000000),
        ('S',90,170000000,33,68000000,52,136000000),
        ('T',95,180000000,35,72000000,55,144000000),
        ('U',100,190000000,37,76000000,58,152000000),
        ('V',105,200000000,39,80000000,61,160000000),
        ('W',110,210000000,41,84000000,64,168000000),
        ('X',115,220000000,43,88000000,67,176000000),
        ('Y',120,230000000,45,92000000,70,182000000),
        ('Z',125,240000000,47,96000000,73,192000000)
) source(
    drive_code,jump_drive_tons,jump_drive_cost_minor,
    maneuver_drive_tons,maneuver_drive_cost_minor,
    power_plant_tons,power_plant_cost_minor
)
JOIN src_locator locator
  ON locator.heading_path=
     'Ship Design and Construction > Ship Drives';

INSERT INTO rule_ship_drive_design
SELECT source.drive_code,'small_craft',
       NULL::numeric,NULL::bigint,
       source.maneuver_tons,source.maneuver_cost,
       source.power_tons,source.power_cost,
       locator.source_locator_id
FROM (
    VALUES
        ('sA',0.5::numeric,1000000::bigint,1.2::numeric,3000000::bigint),
        ('sB',1,2000000,1.5,3500000),
        ('sC',1.5,3000000,1.8,4000000),
        ('sD',2,3500000,2.1,4500000),
        ('sE',2.5,4000000,2.4,5000000),
        ('sF',3,6000000,2.7,5500000),
        ('sG',3.5,8000000,3,6000000),
        ('sH',4,9000000,3.3,6500000),
        ('sJ',4.5,10000000,3.6,7000000),
        ('sK',5,11000000,3.9,7500000),
        ('sL',6,12000000,4.5,8000000),
        ('sM',7,14000000,5.1,9000000),
        ('sN',8,16000000,5.7,10000000),
        ('sP',9,18000000,6.3,12000000),
        ('sQ',10,20000000,6.9,14000000),
        ('sR',11,22000000,7.5,16000000),
        ('sS',12,24000000,8.1,18000000),
        ('sT',13,26000000,8.7,20000000),
        ('sU',14,28000000,9.3,22000000),
        ('sV',15,30000000,9.9,24000000),
        ('sW',16,32000000,10.5,26000000)
) source(
    drive_code,maneuver_tons,maneuver_cost,power_tons,power_cost
)
JOIN src_locator locator
  ON locator.heading_path=
     'Ship Design and Construction > Small Craft Design';

CREATE TABLE rule_ship_drive_performance (
    craft_scale text NOT NULL,
    drive_code text NOT NULL,
    hull_code text NOT NULL,
    performance smallint NOT NULL CHECK (performance BETWEEN 1 AND 6),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    PRIMARY KEY (craft_scale,drive_code,hull_code),
    FOREIGN KEY (craft_scale,drive_code)
        REFERENCES rule_ship_drive_design(craft_scale,drive_code),
    FOREIGN KEY (hull_code)
        REFERENCES rule_ship_hull_design(hull_code)
);

WITH matrix(drive_code,performance_values) AS (
    VALUES
        ('A',ARRAY[2,1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL]::smallint[]),
        ('B',ARRAY[4,2,1,1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL]::smallint[]),
        ('C',ARRAY[6,3,2,1,1,1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL]::smallint[]),
        ('D',ARRAY[NULL,4,2,2,1,1,1,1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL]::smallint[]),
        ('E',ARRAY[NULL,5,3,2,2,1,1,1,1,1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL]::smallint[]),
        ('F',ARRAY[NULL,6,4,3,2,2,1,1,1,1,1,NULL,NULL,NULL,NULL,NULL,NULL,NULL]::smallint[]),
        ('G',ARRAY[NULL,NULL,4,3,2,2,2,2,1,1,1,1,NULL,NULL,NULL,NULL,NULL,NULL]::smallint[]),
        ('H',ARRAY[NULL,NULL,5,4,3,2,2,2,2,2,1,1,1,NULL,NULL,NULL,NULL,NULL]::smallint[]),
        ('J',ARRAY[NULL,NULL,6,4,3,3,2,2,2,2,2,1,1,1,NULL,NULL,NULL,NULL]::smallint[]),
        ('K',ARRAY[NULL,NULL,NULL,5,4,3,3,3,2,2,2,2,1,1,1,NULL,NULL,NULL]::smallint[]),
        ('L',ARRAY[NULL,NULL,NULL,5,4,3,3,3,3,3,2,2,2,1,1,NULL,NULL,NULL]::smallint[]),
        ('M',ARRAY[NULL,NULL,NULL,6,4,4,3,3,3,3,3,2,2,2,1,NULL,NULL,NULL]::smallint[]),
        ('N',ARRAY[NULL,NULL,NULL,6,5,4,4,4,3,3,3,3,2,2,2,NULL,NULL,NULL]::smallint[]),
        ('P',ARRAY[NULL,NULL,NULL,NULL,5,4,4,4,4,4,3,3,3,2,2,NULL,NULL,NULL]::smallint[]),
        ('Q',ARRAY[NULL,NULL,NULL,NULL,6,5,4,4,4,4,4,3,3,3,2,1,NULL,NULL]::smallint[]),
        ('R',ARRAY[NULL,NULL,NULL,NULL,6,5,5,5,4,4,4,4,3,3,3,1,NULL,NULL]::smallint[]),
        ('S',ARRAY[NULL,NULL,NULL,NULL,6,5,5,5,5,5,4,4,4,3,3,1,NULL,NULL]::smallint[]),
        ('T',ARRAY[NULL,NULL,NULL,NULL,NULL,6,5,5,5,5,5,4,4,4,3,2,NULL,NULL]::smallint[]),
        ('U',ARRAY[NULL,NULL,NULL,NULL,NULL,6,6,5,5,5,5,4,4,4,4,2,NULL,NULL]::smallint[]),
        ('V',ARRAY[NULL,NULL,NULL,NULL,NULL,6,6,6,5,5,5,5,4,4,4,2,1,NULL]::smallint[]),
        ('W',ARRAY[NULL,NULL,NULL,NULL,NULL,NULL,6,6,6,5,5,5,4,4,4,3,1,1]::smallint[]),
        ('X',ARRAY[NULL,NULL,NULL,NULL,NULL,NULL,6,6,6,6,5,5,5,4,4,3,1,1]::smallint[]),
        ('Y',ARRAY[NULL,NULL,NULL,NULL,NULL,NULL,6,6,6,6,5,5,5,4,4,3,2,1]::smallint[]),
        ('Z',ARRAY[NULL,NULL,NULL,NULL,NULL,NULL,6,6,6,6,6,5,5,5,4,4,2,2]::smallint[])
),
hulls(hull_code,display_order) AS (
    VALUES
        ('1',1),('2',2),('3',3),('4',4),('5',5),('6',6),
        ('7',7),('8',8),('9',9),('A',10),('C',11),('E',12),
        ('G',13),('J',14),('L',15),('M',16),('N',17),('P',18)
)
INSERT INTO rule_ship_drive_performance
SELECT 'starship',matrix.drive_code,hulls.hull_code,
       performance.performance,locator.source_locator_id
FROM matrix
CROSS JOIN LATERAL unnest(matrix.performance_values)
    WITH ORDINALITY performance(performance,display_order)
JOIN hulls USING (display_order)
JOIN src_locator locator
  ON locator.heading_path=
     'Ship Design and Construction > Ship Drives'
WHERE performance.performance IS NOT NULL;

WITH matrix(drive_code,performance_values) AS (
    VALUES
        ('sA',ARRAY[2,1,1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL]::smallint[]),
        ('sB',ARRAY[4,2,2,1,1,1,1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL]::smallint[]),
        ('sC',ARRAY[6,4,3,2,2,1,1,1,1,1,1,NULL,NULL,NULL,NULL,NULL,NULL,NULL]::smallint[]),
        ('sD',ARRAY[NULL,5,4,3,2,2,2,1,1,1,1,1,1,1,1,NULL,NULL,NULL]::smallint[]),
        ('sE',ARRAY[NULL,6,5,4,3,2,2,2,2,1,1,1,1,1,1,1,1,1]::smallint[]),
        ('sF',ARRAY[NULL,NULL,6,4,4,3,3,2,2,2,2,1,1,1,1,1,1,1]::smallint[]),
        ('sG',ARRAY[NULL,NULL,NULL,5,4,4,3,3,2,2,2,2,2,1,1,1,1,1]::smallint[]),
        ('sH',ARRAY[NULL,NULL,NULL,6,5,4,4,3,3,2,2,2,2,2,2,1,1,1]::smallint[]),
        ('sJ',ARRAY[NULL,NULL,NULL,NULL,6,5,4,4,3,3,3,2,2,2,2,2,2,1]::smallint[]),
        ('sK',ARRAY[NULL,NULL,NULL,NULL,6,5,5,4,4,3,3,3,2,2,2,2,2,2]::smallint[]),
        ('sL',ARRAY[NULL,NULL,NULL,NULL,NULL,6,6,5,4,4,4,3,3,3,3,2,2,2]::smallint[]),
        ('sM',ARRAY[NULL,NULL,NULL,NULL,NULL,NULL,NULL,6,5,5,4,4,4,3,3,3,3,2]::smallint[]),
        ('sN',ARRAY[NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,6,5,5,4,4,4,4,3,3,3]::smallint[]),
        ('sP',ARRAY[NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,6,6,5,5,4,4,4,4,3]::smallint[]),
        ('sQ',ARRAY[NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,6,6,5,5,5,4,4,4]::smallint[]),
        ('sR',ARRAY[NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,6,6,5,5,5,4,4]::smallint[]),
        ('sS',ARRAY[NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,6,6,6,5,5,5]::smallint[]),
        ('sT',ARRAY[NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,6,6,6,5,5]::smallint[]),
        ('sU',ARRAY[NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,6,6,5]::smallint[]),
        ('sV',ARRAY[NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,6,6]::smallint[]),
        ('sW',ARRAY[NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,6]::smallint[])
),
hulls(hull_code,display_order) AS (
    VALUES
        ('s1',1),('s2',2),('s3',3),('s4',4),('s5',5),('s6',6),
        ('s7',7),('s8',8),('s9',9),('sA',10),('sB',11),('sC',12),
        ('sD',13),('sE',14),('sF',15),('sG',16),('sH',17),('sJ',18)
)
INSERT INTO rule_ship_drive_performance
SELECT 'small_craft',matrix.drive_code,hulls.hull_code,
       performance.performance,locator.source_locator_id
FROM matrix
CROSS JOIN LATERAL unnest(matrix.performance_values)
    WITH ORDINALITY performance(performance,display_order)
JOIN hulls USING (display_order)
JOIN src_locator locator
  ON locator.heading_path=
     'Ship Design and Construction > Small Craft Design'
WHERE performance.performance IS NOT NULL;

CREATE TABLE rule_ship_power_plant_fuel (
    craft_scale text NOT NULL CHECK (
        craft_scale IN ('starship','small_craft')
    ),
    drive_code text NOT NULL CHECK (
        drive_code ~ '^(?:[A-HJ-NP-Z]|s[A-HJ-NP-Z])$'
    ),
    power_plant_tons numeric NOT NULL CHECK (power_plant_tons>0),
    fuel_tons_per_week numeric NOT NULL CHECK (
        fuel_tons_per_week>0
    ),
    minimum_fuel_tons numeric CHECK (minimum_fuel_tons>0),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    PRIMARY KEY (craft_scale,drive_code),
    CHECK (
        (craft_scale='starship' AND minimum_fuel_tons IS NOT NULL)
        OR
        (craft_scale='small_craft' AND minimum_fuel_tons IS NULL)
    )
);

INSERT INTO rule_ship_power_plant_fuel
SELECT 'starship',source.drive_code,source.power_tons,
       source.fuel_week,source.minimum_fuel,
       locator.source_locator_id
FROM (
    VALUES
        ('A',4::numeric,1::numeric,2::numeric),
        ('B',7,2,4),('C',10,3,6),('D',13,4,8),
        ('E',16,5,10),('F',19,6,12),('G',22,7,14),
        ('H',25,8,16),('J',28,9,18),('K',31,10,20),
        ('L',34,11,22),('M',37,12,24),('N',40,13,26),
        ('P',43,14,28),('Q',46,15,30),('R',49,16,32),
        ('S',52,17,34),('T',55,18,36),('U',58,19,38),
        ('V',61,20,40),('W',64,21,42),('X',67,22,44),
        ('Y',70,23,46),('Z',73,24,48)
) source(drive_code,power_tons,fuel_week,minimum_fuel)
JOIN src_locator locator
  ON locator.heading_path='Ship Design and Construction > Fuel';

INSERT INTO rule_ship_power_plant_fuel
SELECT 'small_craft',source.drive_code,source.power_tons,
       source.fuel_week,NULL::numeric,locator.source_locator_id
FROM (
    VALUES
        ('sA',1.2::numeric,0.4::numeric),
        ('sB',1.5,0.5),('sC',1.8,0.6),('sD',2.1,0.7),
        ('sE',2.4,0.8),('sF',2.7,0.9),('sG',3,1),
        ('sH',3.3,1.1),('sJ',3.6,1.2),('sK',3.9,1.3),
        ('sL',4.5,1.5),('sM',5.1,1.7),('sN',5.7,1.9),
        ('sP',6.3,2.1),('sQ',6.9,2.3),('sR',7.5,2.5),
        ('sS',8.1,2.7),('sT',8.7,2.9),('sU',9.3,3.1),
        ('sV',9.9,3.3),('sW',10.5,3.5),('sX',11.1,3.7),
        ('sY',11.7,3.9),('sZ',12.3,4.1)
) source(drive_code,power_tons,fuel_week)
JOIN src_locator locator
  ON locator.heading_path=
     'Ship Design and Construction > Small Craft Design';
