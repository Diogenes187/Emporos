INSERT INTO src_locator(source_work_id,source_artifact_id,locator_type,heading_path,display_citation)
SELECT a.source_work_id,a.source_artifact_id,'heading','Starship Encounters > '||x.heading,
 CASE w.work_code WHEN 'cepheus-engine.ogn' THEN 'Cepheus Engine SRD, ' ELSE 'Cepheus Engine v9.1, ' END||x.heading
FROM src_artifact a JOIN src_work w USING(source_work_id) CROSS JOIN (VALUES
 ('Alien Vessel Encounter Table'),('Astrogation Encounter Table'),('Derelict Encounter Table'),('Hostile Vessel Encounter Table'),
 ('Merchant Vessel Encounter Table'),('Military Vessel Encounter Table'),('Personal Vessel Encounter Table'),('Spacecraft Encounter Table'),
 ('Space Habitat Encounter Table'),('Space Junk Encounter Table')
) x(heading)
WHERE (w.work_code='cepheus-engine.github-v9.1' AND a.source_uri='src/book3/starship-encounters.md')
 OR (w.work_code='cepheus-engine.ogn' AND a.source_uri='https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-starship-encounters/')
ON CONFLICT DO NOTHING;

WITH p AS(SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine')
INSERT INTO rule_rule(content_package_id,rule_code,name,rule_category,rule_status,description)
SELECT content_package_id,'encounter.starship-subtype-resolution','Starship Encounter Subtype Resolution','encounter','approved',
 'A one-D6 category subtable chain resolves a broad starship encounter into a concrete vessel, object, facility, phenomenon, or scenario.' FROM p;
INSERT INTO src_record_provenance(rule_id,content_package_id,source_locator_id,provenance_class,is_primary_citation)
SELECT r.rule_id,r.content_package_id,l.source_locator_id,CASE w.work_code WHEN 'cepheus-engine.ogn' THEN 'direct' ELSE 'corroborating' END,w.work_code='cepheus-engine.ogn'
FROM rule_rule r CROSS JOIN src_locator l JOIN src_work w USING(source_work_id)
WHERE r.rule_code='encounter.starship-subtype-resolution' AND l.heading_path='Starship Encounters > Alien Vessel Encounter Table'
 AND w.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1');

CREATE TABLE rule_starship_encounter_subtable(
 subtable_code text PRIMARY KEY,category_rule_id bigint UNIQUE REFERENCES rule_starship_encounter_category,
 name text NOT NULL UNIQUE,dice_count smallint NOT NULL CHECK(dice_count=1),die_sides smallint NOT NULL CHECK(die_sides=6),
 CHECK((subtable_code='warship')=(category_rule_id IS NULL))
);
INSERT INTO rule_starship_encounter_subtable
SELECT c.category_code,c.rule_id,replace(initcap(replace(c.category_code,'_',' ')),'Astrogation','Astrogation')||' Encounter',1,6 FROM rule_starship_encounter_category c;
INSERT INTO rule_starship_encounter_subtable VALUES('warship',NULL,'Warship',1,6);

CREATE TABLE rule_starship_encounter_result(
 result_code text PRIMARY KEY,result_name text NOT NULL,result_kind text NOT NULL CHECK(result_kind IN('ship-class','alien-vessel','facility','object','phenomenon','scenario','subtable')),
 ship_class_rule_id bigint REFERENCES ship_class(ship_class_rule_id),next_subtable_code text REFERENCES rule_starship_encounter_subtable(subtable_code),
 effect_code text CHECK(effect_code IN('comet-sensor-interference','collision-debris','dust-cloud-interference','jettisoned-cargo')),
 CHECK((result_kind='ship-class')=(ship_class_rule_id IS NOT NULL)),CHECK((result_kind='subtable')=(next_subtable_code IS NOT NULL))
);

WITH data(result_code,result_name,result_kind,class_code,next_table,effect_code) AS(VALUES
 ('alien-courier','Alien courier','alien-vessel',NULL,NULL,NULL),('alien-frontier-trader','Alien frontier trader','alien-vessel',NULL,NULL,NULL),('alien-merchant-freighter','Alien merchant freighter','alien-vessel',NULL,NULL,NULL),('alien-military-vessel','Alien military vessel','alien-vessel',NULL,NULL,NULL),('alien-raider','Alien raider','alien-vessel',NULL,NULL,NULL),('alien-research-vessel','Alien research vessel','alien-vessel',NULL,NULL,NULL),
 ('asteroid-inhabited','Asteroid (inhabited)','object',NULL,NULL,NULL),('asteroid-uninhabited','Asteroid (uninhabited)','object',NULL,NULL,NULL),('comet','Comet','phenomenon',NULL,NULL,'comet-sensor-interference'),('interplanetary-dust-cloud','Interplanetary dust cloud','phenomenon',NULL,NULL,'dust-cloud-interference'),('micrometeorite-storm','Micrometeorite storm','phenomenon',NULL,NULL,'collision-debris'),('solar-flares','Solar flares','phenomenon',NULL,NULL,NULL),
 ('escape-pod-life-boat','Escape pod or life boat','ship-class','launch',NULL,NULL),('merchant-vessel-subtable','Merchant vessel','subtable',NULL,'merchant_vessel',NULL),('military-vessel-subtable','Military vessel','subtable',NULL,'military_vessel',NULL),('personal-vessel-subtable','Personal vessel','subtable',NULL,'personal_vessel',NULL),('research-vessel','Research vessel','ship-class','research-vessel',NULL,NULL),('space-habitat-subtable','Space habitat','subtable',NULL,'space_habitat',NULL),
 ('captured-merchant-vessel','Captured merchant vessel','subtable',NULL,'merchant_vessel',NULL),('captured-military-vessel','Captured military vessel','subtable',NULL,'military_vessel',NULL),('enemy-military-vessel','Enemy military vessel','subtable',NULL,'military_vessel',NULL),('raider','Raider','ship-class','raider',NULL,NULL),('false-distress','Ship in distress (false)','scenario',NULL,NULL,NULL),('true-distress','Ship in distress (true)','scenario',NULL,NULL,NULL),
 ('frontier-trader','Frontier trader','ship-class','frontier-trader',NULL,NULL),('merchant-freighter','Merchant freighter','ship-class','merchant-freighter',NULL,NULL),('merchant-liner','Merchant liner','ship-class','merchant-liner',NULL,NULL),('merchant-trader','Merchant trader','ship-class','merchant-trader',NULL,NULL),
 ('corvette','Corvette','ship-class','corvette',NULL,NULL),('destroyer','Destroyer','ship-class','destroyer',NULL,NULL),('patrol-frigate','Patrol frigate','ship-class','patrol-frigate',NULL,NULL),('system-defense-boat','System defense boat','ship-class','system-defense-boat',NULL,NULL),('system-monitor','System monitor','ship-class','system-monitor',NULL,NULL),('warship-subtable','Warship','subtable',NULL,'warship',NULL),
 ('asteroid-miner','Asteroid miner','ship-class','asteroid-miner',NULL,NULL),('courier','Courier','ship-class','courier',NULL,NULL),('survey-vessel','Survey vessel','ship-class','survey-vessel',NULL,NULL),('unusual-ship','Unusual ship','scenario',NULL,NULL,NULL),('yacht','Yacht','ship-class','yacht',NULL,NULL),
 ('cutter','Cutter','ship-class','cutter',NULL,NULL),('launch-life-boat','Launch or life boat','ship-class','launch',NULL,NULL),('fighter','Fighter','ship-class','fighter',NULL,NULL),('pinnace','Pinnace','ship-class','pinnace',NULL,NULL),('ships-boat','Ship''s boat','ship-class','ships-boat',NULL,NULL),('shuttle','Shuttle','ship-class','shuttle',NULL,NULL),
 ('medical-facility','Medical facility','facility',NULL,NULL,NULL),('military-facility','Military facility','facility',NULL,NULL,NULL),('orbital-factory','Orbital factory','facility',NULL,NULL,NULL),('orbital-habitat','Orbital habitat','facility',NULL,NULL,NULL),('refueling-station-spaceport','Refueling station or spaceport','facility',NULL,NULL,NULL),('research-facility','Research facility','facility',NULL,NULL,NULL),
 ('astrogational-buoy-beacon','Astrogational buoy or beacon','object',NULL,NULL,NULL),('communications-satellite','Communications satellite','object',NULL,NULL,NULL),('collision-attack-debris','Debris from collision or attack','object',NULL,NULL,'collision-debris'),('defense-satellite','Defense satellite','object',NULL,NULL,NULL),('jettisoned-cargo-pod','Jettisoned cargo pod','object',NULL,NULL,'jettisoned-cargo'),('lost-abandoned-equipment','Lost or abandoned equipment or garbage','object',NULL,NULL,'collision-debris'),
 ('dreadnought','Dreadnought','ship-class','dreadnought',NULL,NULL),('heavy-cruiser','Heavy cruiser','ship-class','heavy-cruiser',NULL,NULL),('light-cruiser','Light cruiser','ship-class','light-cruiser',NULL,NULL)
)
INSERT INTO rule_starship_encounter_result
SELECT d.result_code,d.result_name,d.result_kind,s.ship_class_rule_id,d.next_table,d.effect_code FROM data d LEFT JOIN ship_class s ON s.class_code=d.class_code;

CREATE TABLE rule_starship_encounter_subtype_roll(
 subtable_code text NOT NULL REFERENCES rule_starship_encounter_subtable,roll_total smallint NOT NULL CHECK(roll_total BETWEEN 1 AND 6),
 result_code text NOT NULL REFERENCES rule_starship_encounter_result,PRIMARY KEY(subtable_code,roll_total)
);
INSERT INTO rule_starship_encounter_subtype_roll VALUES
 ('alien_vessel',1,'alien-courier'),('alien_vessel',2,'alien-frontier-trader'),('alien_vessel',3,'alien-merchant-freighter'),('alien_vessel',4,'alien-military-vessel'),('alien_vessel',5,'alien-raider'),('alien_vessel',6,'alien-research-vessel'),
 ('astrogation',1,'asteroid-inhabited'),('astrogation',2,'asteroid-uninhabited'),('astrogation',3,'comet'),('astrogation',4,'interplanetary-dust-cloud'),('astrogation',5,'micrometeorite-storm'),('astrogation',6,'solar-flares'),
 ('derelict',1,'escape-pod-life-boat'),('derelict',2,'merchant-vessel-subtable'),('derelict',3,'military-vessel-subtable'),('derelict',4,'personal-vessel-subtable'),('derelict',5,'research-vessel'),('derelict',6,'space-habitat-subtable'),
 ('hostile_vessel',1,'captured-merchant-vessel'),('hostile_vessel',2,'captured-military-vessel'),('hostile_vessel',3,'enemy-military-vessel'),('hostile_vessel',4,'raider'),('hostile_vessel',5,'false-distress'),('hostile_vessel',6,'true-distress'),
 ('merchant_vessel',1,'frontier-trader'),('merchant_vessel',2,'frontier-trader'),('merchant_vessel',3,'merchant-freighter'),('merchant_vessel',4,'merchant-liner'),('merchant_vessel',5,'merchant-trader'),('merchant_vessel',6,'merchant-trader'),
 ('military_vessel',1,'corvette'),('military_vessel',2,'destroyer'),('military_vessel',3,'patrol-frigate'),('military_vessel',4,'system-defense-boat'),('military_vessel',5,'system-monitor'),('military_vessel',6,'warship-subtable'),
 ('personal_vessel',1,'asteroid-miner'),('personal_vessel',2,'courier'),('personal_vessel',3,'research-vessel'),('personal_vessel',4,'survey-vessel'),('personal_vessel',5,'unusual-ship'),('personal_vessel',6,'yacht'),
 ('spacecraft',1,'cutter'),('spacecraft',2,'launch-life-boat'),('spacecraft',3,'fighter'),('spacecraft',4,'pinnace'),('spacecraft',5,'ships-boat'),('spacecraft',6,'shuttle'),
 ('space_habitat',1,'medical-facility'),('space_habitat',2,'military-facility'),('space_habitat',3,'orbital-factory'),('space_habitat',4,'orbital-habitat'),('space_habitat',5,'refueling-station-spaceport'),('space_habitat',6,'research-facility'),
 ('space_junk',1,'astrogational-buoy-beacon'),('space_junk',2,'communications-satellite'),('space_junk',3,'collision-attack-debris'),('space_junk',4,'defense-satellite'),('space_junk',5,'jettisoned-cargo-pod'),('space_junk',6,'lost-abandoned-equipment'),
 ('warship',1,'dreadnought'),('warship',2,'heavy-cruiser'),('warship',3,'heavy-cruiser'),('warship',4,'light-cruiser'),('warship',5,'light-cruiser'),('warship',6,'light-cruiser');

CREATE TABLE src_starship_encounter_subtype_roll_provenance(
 subtable_code text NOT NULL,roll_total smallint NOT NULL,source_locator_id bigint NOT NULL REFERENCES src_locator,
 provenance_class text NOT NULL CHECK(provenance_class IN('direct','corroborating')),is_primary_citation boolean NOT NULL,
 PRIMARY KEY(subtable_code,roll_total,source_locator_id,provenance_class),
 FOREIGN KEY(subtable_code,roll_total) REFERENCES rule_starship_encounter_subtype_roll
);
INSERT INTO src_starship_encounter_subtype_roll_provenance
SELECT roll.subtable_code,roll.roll_total,l.source_locator_id,CASE w.work_code WHEN 'cepheus-engine.ogn' THEN 'direct' ELSE 'corroborating' END,w.work_code='cepheus-engine.ogn'
FROM rule_starship_encounter_subtype_roll roll JOIN src_locator l ON l.heading_path='Starship Encounters > '||CASE roll.subtable_code
 WHEN 'alien_vessel' THEN 'Alien Vessel Encounter Table' WHEN 'astrogation' THEN 'Astrogation Encounter Table' WHEN 'derelict' THEN 'Derelict Encounter Table'
 WHEN 'hostile_vessel' THEN 'Hostile Vessel Encounter Table' WHEN 'merchant_vessel' THEN 'Merchant Vessel Encounter Table' WHEN 'military_vessel' THEN 'Military Vessel Encounter Table'
 WHEN 'personal_vessel' THEN 'Personal Vessel Encounter Table' WHEN 'spacecraft' THEN 'Spacecraft Encounter Table' WHEN 'space_habitat' THEN 'Space Habitat Encounter Table'
 WHEN 'space_junk' THEN 'Space Junk Encounter Table' WHEN 'warship' THEN 'Military Vessel Encounter Table' END JOIN src_work w USING(source_work_id)
WHERE w.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1');
