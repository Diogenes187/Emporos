ALTER TABLE ship_class_component
    ADD COLUMN source_locator_id bigint REFERENCES
        src_locator(source_locator_id);

ALTER TABLE ship_class_hangar_option
    ADD COLUMN source_locator_id bigint REFERENCES
        src_locator(source_locator_id);

UPDATE ship_class_hangar_option hangar
SET source_locator_id=class.source_locator_id
FROM ship_class class
WHERE class.ship_class_rule_id=hangar.ship_class_rule_id
  AND class.standard_design;

WITH fact(
    class_code,component_code,quantity,rating,allocated_tons,sort_key
) AS (
    VALUES
        ('asteroid-miner','stateroom',3::smallint,NULL::numeric,12::numeric,10),
        ('corvette','stateroom',9,NULL,36,10),
        ('courier','stateroom',4,NULL,16,10),
        ('destroyer','stateroom',12,NULL,48,10),
        ('dreadnought','stateroom',101,NULL,404,10),
        ('frontier-trader','stateroom',25,NULL,100,10),
        ('heavy-cruiser','stateroom',42,NULL,168,10),
        ('light-cruiser','stateroom',23,NULL,92,10),
        ('merchant-freighter','stateroom',4,NULL,16,10),
        ('merchant-liner','stateroom',35,NULL,140,10),
        ('merchant-trader','stateroom',10,NULL,40,10),
        ('patrol-frigate','stateroom',10,NULL,40,10),
        ('raider','stateroom',12,NULL,48,10),
        ('research-vessel','stateroom',6,NULL,24,10),
        ('survey-vessel','stateroom',8,NULL,32,10),
        ('system-defense-boat','stateroom',10,NULL,40,10),
        ('system-monitor','stateroom',24,NULL,96,10),
        ('yacht','stateroom',6,NULL,24,10),

        ('asteroid-miner','low-berth',5,NULL,2.5,20),
        ('dreadnought','low-berth',223,NULL,111.5,20),
        ('frontier-trader','low-berth',12,NULL,6,20),
        ('merchant-liner','low-berth',20,NULL,10,20),
        ('merchant-trader','low-berth',20,NULL,10,20),

        ('corvette','emergency-low-berth',5,NULL,5,21),
        ('courier','emergency-low-berth',1,NULL,1,21),
        ('destroyer','emergency-low-berth',6,NULL,6,21),
        ('dreadnought','emergency-low-berth',56,NULL,56,21),
        ('heavy-cruiser','emergency-low-berth',20,NULL,20,21),
        ('light-cruiser','emergency-low-berth',11,NULL,11,21),
        ('merchant-freighter','emergency-low-berth',2,NULL,2,21),
        ('patrol-frigate','emergency-low-berth',5,NULL,5,21),
        ('raider','emergency-low-berth',6,NULL,6,21),
        ('research-vessel','emergency-low-berth',3,NULL,3,21),
        ('survey-vessel','emergency-low-berth',4,NULL,4,21),
        ('system-defense-boat','emergency-low-berth',5,NULL,5,21),
        ('system-monitor','emergency-low-berth',12,NULL,12,21),
        ('yacht','emergency-low-berth',3,NULL,3,21),

        ('dreadnought','barracks',1,60,120,30),
        ('corvette','armory',1,NULL,2,31),
        ('destroyer','armory',1,NULL,2,31),
        ('dreadnought','armory',6,NULL,12,31),
        ('heavy-cruiser','armory',3,NULL,6,31),
        ('light-cruiser','armory',2,NULL,4,31),
        ('patrol-frigate','armory',1,NULL,2,31),
        ('raider','armory',1,NULL,2,31),
        ('system-defense-boat','armory',1,NULL,2,31),
        ('system-monitor','armory',2,NULL,4,31),
        ('corvette','detention-cell',4,NULL,8,32),
        ('raider','detention-cell',4,NULL,8,32),
        ('research-vessel','laboratory',6,1,24,33),
        ('survey-vessel','laboratory',6,1,24,33),
        ('yacht','luxuries',2,NULL,2,34),

        ('asteroid-miner','fuel-processor',3,NULL,3,40),
        ('corvette','fuel-processor',5,NULL,5,40),
        ('courier','fuel-processor',2,NULL,2,40),
        ('destroyer','fuel-processor',19,NULL,19,40),
        ('dreadnought','fuel-processor',54,NULL,54,40),
        ('frontier-trader','fuel-processor',3,NULL,3,40),
        ('heavy-cruiser','fuel-processor',23,NULL,23,40),
        ('light-cruiser','fuel-processor',18,NULL,18,40),
        ('merchant-freighter','fuel-processor',3,NULL,3,40),
        ('merchant-liner','fuel-processor',2,NULL,2,40),
        ('merchant-trader','fuel-processor',2,NULL,2,40),
        ('patrol-frigate','fuel-processor',5,NULL,5,40),
        ('raider','fuel-processor',6,NULL,6,40),
        ('research-vessel','fuel-processor',2,NULL,2,40),
        ('survey-vessel','fuel-processor',4,NULL,4,40),
        ('system-defense-boat','fuel-processor',3,NULL,3,40),
        ('system-monitor','fuel-processor',5,NULL,5,40),
        ('yacht','fuel-processor',2,NULL,2,40),

        ('asteroid-miner','fuel-scoop',1,NULL,0,41),
        ('corvette','fuel-scoop',1,NULL,0,41),
        ('courier','fuel-scoop',1,NULL,0,41),
        ('destroyer','fuel-scoop',1,NULL,0,41),
        ('dreadnought','fuel-scoop',1,NULL,0,41),
        ('frontier-trader','fuel-scoop',1,NULL,0,41),
        ('heavy-cruiser','fuel-scoop',1,NULL,0,41),
        ('light-cruiser','fuel-scoop',1,NULL,0,41),
        ('merchant-freighter','fuel-scoop',1,NULL,0,41),
        ('merchant-liner','fuel-scoop',1,NULL,0,41),
        ('merchant-trader','fuel-scoop',1,NULL,0,41),
        ('patrol-frigate','fuel-scoop',1,NULL,0,41),
        ('raider','fuel-scoop',1,NULL,0,41),
        ('research-vessel','fuel-scoop',1,NULL,0,41),
        ('survey-vessel','fuel-scoop',1,NULL,0,41),
        ('system-defense-boat','fuel-scoop',1,NULL,0,41),
        ('system-monitor','fuel-scoop',1,NULL,0,41),
        ('yacht','fuel-scoop',1,NULL,0,41),
        ('fighter','fuel-scoop',1,NULL,0,41),

        ('asteroid-miner','smelter',1,NULL,0,50),
        ('cutter','one-person-control-cabin',1,NULL,3,50),
        ('cutter','cutter-module-berth',1,NULL,30,51),
        ('fighter','one-person-cockpit',1,NULL,1.5,50),
        ('launch','two-person-control-cabin',1,NULL,6,50),
        ('pinnace','one-person-control-cabin',1,NULL,3,50),
        ('ships-boat','one-person-control-cabin',1,NULL,3,50),
        ('shuttle','two-person-control-cabin',1,NULL,6,50),

        ('asteroid-miner','cargo-hold',1,NULL,84,90),
        ('corvette','cargo-hold',1,NULL,25,90),
        ('courier','cargo-hold',1,NULL,16,90),
        ('destroyer','cargo-hold',1,NULL,50.5,90),
        ('dreadnought','cargo-hold',1,NULL,412,90),
        ('frontier-trader','cargo-hold',1,NULL,75,90),
        ('heavy-cruiser','cargo-hold',1,NULL,152.5,90),
        ('light-cruiser','cargo-hold',1,NULL,53,90),
        ('merchant-freighter','cargo-hold',1,NULL,261,90),
        ('merchant-liner','cargo-hold',1,NULL,46,90),
        ('merchant-trader','cargo-hold',1,NULL,85,90),
        ('patrol-frigate','cargo-hold',1,NULL,23,90),
        ('raider','cargo-hold',1,NULL,125,90),
        ('research-vessel','cargo-hold',1,NULL,29,90),
        ('survey-vessel','cargo-hold',1,NULL,39,90),
        ('system-defense-boat','cargo-hold',1,NULL,109,90),
        ('system-monitor','cargo-hold',1,NULL,123.5,90),
        ('yacht','cargo-hold',1,NULL,12,90),
        ('cutter','cargo-hold',1,NULL,1.3,90),
        ('fighter','cargo-hold',1,NULL,0,90),
        ('launch','cargo-hold',1,NULL,10.9,90),
        ('pinnace','cargo-hold',1,NULL,25,90),
        ('ships-boat','cargo-hold',1,NULL,16.7,90),
        ('shuttle','cargo-hold',1,NULL,67.4,90)
),
ordered AS (
    SELECT fact.*,
           row_number() OVER (
               PARTITION BY class_code
               ORDER BY sort_key,component_code
           )::smallint AS display_order
    FROM fact
)
INSERT INTO ship_class_component (
    ship_class_rule_id,component_rule_id,quantity,rating,
    allocated_tons,display_order,source_locator_id
)
SELECT class.ship_class_rule_id,component.component_rule_id,
       ordered.quantity,ordered.rating,ordered.allocated_tons,
       ordered.display_order,class.source_locator_id
FROM ordered
JOIN ship_class class
  ON class.class_code=ordered.class_code
JOIN ship_component_definition component
  ON component.component_code=ordered.component_code;
