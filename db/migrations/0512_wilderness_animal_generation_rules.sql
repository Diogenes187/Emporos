INSERT INTO src_locator(source_work_id,source_artifact_id,locator_type,heading_path,display_citation)
SELECT a.source_work_id,a.source_artifact_id,'heading',h.path,
       CASE w.work_code WHEN 'cepheus-engine.ogn' THEN 'Cepheus Engine SRD, ' ELSE 'Cepheus Engine v9.1, ' END||h.citation
FROM src_artifact a JOIN src_work w USING(source_work_id)
CROSS JOIN (VALUES
 ('Planetary Wilderness Encounters > Animal Encounters','Planetary Wilderness Encounters: Animal Encounters'),
 ('Planetary Wilderness Encounters > Creating Encounter Tables','Planetary Wilderness Encounters: Creating Encounter Tables'),
 ('Planetary Wilderness Encounters > Using the Encounter Tables','Planetary Wilderness Encounters: Using the Encounter Tables')
) h(path,citation)
WHERE (w.work_code='cepheus-engine.github-v9.1' AND a.source_uri='src/book3/planetary-wilderness-encounters.md')
   OR (w.work_code='cepheus-engine.ogn' AND a.source_uri='https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-planetary-wilderness-encounters/')
ON CONFLICT DO NOTHING;

WITH p AS(SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine')
INSERT INTO rule_rule(content_package_id,rule_code,name,rule_category,rule_status,description)
SELECT content_package_id,code,name,'encounter','approved',description FROM p CROSS JOIN (VALUES
 ('encounter.wilderness-animal-generation','Wilderness Animal Generation','Terrain, subtype, size, characteristics, skills, natural weapons, armor, speed, and number appearing.'),
 ('encounter.wilderness-table-generation','Wilderness Encounter Table Generation','One-D6 and two-D6 terrain encounter table templates with reusable animal and event entries.'),
 ('encounter.wilderness-occurrence','Wilderness Encounter Occurrence','One travelling and one halted check per day; an unmodified 5+ on one D6 produces an encounter.')
) r(code,name,description);

INSERT INTO src_record_provenance(rule_id,content_package_id,source_locator_id,provenance_class,is_primary_citation)
SELECT r.rule_id,r.content_package_id,l.source_locator_id,
       CASE w.work_code WHEN 'cepheus-engine.ogn' THEN 'direct' ELSE 'corroborating' END,
       w.work_code='cepheus-engine.ogn'
FROM rule_rule r CROSS JOIN src_locator l JOIN src_work w USING(source_work_id)
WHERE (r.rule_code='encounter.wilderness-animal-generation' AND l.heading_path='Planetary Wilderness Encounters > Animal Encounters'
    OR r.rule_code='encounter.wilderness-table-generation' AND l.heading_path='Planetary Wilderness Encounters > Creating Encounter Tables'
    OR r.rule_code='encounter.wilderness-occurrence' AND l.heading_path='Planetary Wilderness Encounters > Using the Encounter Tables')
  AND w.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1');

CREATE TABLE rule_animal_terrain(
 terrain_code text PRIMARY KEY,terrain_name text NOT NULL UNIQUE,subtype_modifier smallint NOT NULL,size_modifier smallint NOT NULL
);
INSERT INTO rule_animal_terrain VALUES
 ('clear','Clear',3,0),('plain-prairie','Plain or Prairie',4,0),('desert','Desert (hot or cold)',3,-3),('hills','Hills, Foothills',0,0),
 ('mountain','Mountain',0,0),('forest','Forest',-4,-4),('woods','Woods',-2,-1),('jungle','Jungle',-4,-3),('rainforest','Rainforest',-2,-2),
 ('rough-broken','Rough, Broken',-3,-3),('swamp-marsh','Swamp, Marsh',-2,4),('beach-shore','Beach, Shore',3,2),('riverbank','Riverbank',1,1),
 ('ocean-shallows','Ocean shallows',4,1),('open-ocean','Open ocean',4,-4),('deep-ocean','Deep ocean',4,2);

CREATE TABLE rule_animal_terrain_movement(
 terrain_code text NOT NULL REFERENCES rule_animal_terrain,roll_result smallint NOT NULL CHECK(roll_result BETWEEN 1 AND 6),
 movement_code text NOT NULL CHECK(movement_code IN('A','F','S','W')),additional_size_modifier smallint NOT NULL,
 PRIMARY KEY(terrain_code,roll_result)
);
INSERT INTO rule_animal_terrain_movement
SELECT terrain_code,ordinality,split_part(m,':',1),split_part(m,':',2)::smallint FROM (VALUES
 ('clear',ARRAY['W:0','W:0','W:0','W:0','W:2','F:-6']),('plain-prairie',ARRAY['W:0','W:0','W:0','W:2','W:4','F:-6']),('desert',ARRAY['W:0','W:0','W:0','W:0','F:-4','F:-6']),
 ('hills',ARRAY['W:0','W:0','W:0','W:2','F:-4','F:-6']),('mountain',ARRAY['W:0','W:0','W:0','F:-2','F:-4','F:-6']),('forest',ARRAY['W:0','W:0','W:0','W:0','F:-4','F:-6']),
 ('woods',ARRAY['W:0','W:0','W:0','W:0','W:0','F:-6']),('jungle',ARRAY['W:0','W:0','W:0','W:0','W:2','F:-6']),('rainforest',ARRAY['W:0','W:0','W:0','W:2','W:4','F:-6']),
 ('rough-broken',ARRAY['W:0','W:0','W:0','W:2','F:-4','F:-6']),('swamp-marsh',ARRAY['S:-6','A:2','W:0','W:0','F:-4','F:-6']),('beach-shore',ARRAY['S:1','A:2','W:0','W:0','F:-4','F:-6']),
 ('riverbank',ARRAY['S:-4','A:0','W:0','W:0','W:0','F:-6']),('ocean-shallows',ARRAY['S:4','S:2','S:0','S:0','F:-4','F:-6']),('open-ocean',ARRAY['S:6','S:4','S:2','S:0','F:-4','F:-6']),
 ('deep-ocean',ARRAY['S:8','S:6','S:4','S:2','S:0','S:-2'])
) v(terrain_code,moves) CROSS JOIN LATERAL unnest(moves) WITH ORDINALITY u(m,ordinality);

CREATE TABLE rule_animal_subtype_band(
 animal_type text NOT NULL CHECK(animal_type IN('carnivore','herbivore','omnivore','scavenger')),minimum_total smallint NOT NULL,maximum_total smallint NOT NULL,
 subtype_rule_id bigint NOT NULL REFERENCES rule_animal_subtype,PRIMARY KEY(animal_type,minimum_total),CHECK(minimum_total<=maximum_total)
);
INSERT INTO rule_animal_subtype_band
SELECT typ,n,n,(SELECT rule_id FROM rule_animal_subtype WHERE subtype_code=code) FROM (VALUES
 ('herbivore',1,'filter'),('herbivore',2,'filter'),('herbivore',3,'intermittent'),('herbivore',4,'intermittent'),('herbivore',5,'intermittent'),('herbivore',6,'intermittent'),('herbivore',7,'grazer'),('herbivore',8,'grazer'),('herbivore',9,'grazer'),('herbivore',10,'grazer'),('herbivore',11,'grazer'),('herbivore',12,'grazer'),('herbivore',13,'grazer'),
 ('omnivore',1,'gatherer'),('omnivore',2,'eater'),('omnivore',3,'gatherer'),('omnivore',4,'eater'),('omnivore',5,'gatherer'),('omnivore',6,'hunter'),('omnivore',7,'hunter'),('omnivore',8,'hunter'),('omnivore',9,'gatherer'),('omnivore',10,'eater'),('omnivore',11,'hunter'),('omnivore',12,'gatherer'),('omnivore',13,'gatherer'),
 ('carnivore',1,'pouncer'),('carnivore',2,'siren'),('carnivore',3,'pouncer'),('carnivore',4,'killer'),('carnivore',5,'trapper'),('carnivore',6,'pouncer'),('carnivore',7,'chaser'),('carnivore',8,'chaser'),('carnivore',9,'chaser'),('carnivore',10,'killer'),('carnivore',11,'chaser'),('carnivore',12,'siren'),('carnivore',13,'chaser'),
 ('scavenger',1,'carrion-eater'),('scavenger',2,'reducer'),('scavenger',3,'hijacker'),('scavenger',4,'carrion-eater'),('scavenger',5,'intimidator'),('scavenger',6,'reducer'),('scavenger',7,'carrion-eater'),('scavenger',8,'reducer'),('scavenger',9,'hijacker'),('scavenger',10,'intimidator'),('scavenger',11,'reducer'),('scavenger',12,'hijacker'),('scavenger',13,'intimidator')
) x(typ,n,code);
UPDATE rule_animal_subtype_band SET minimum_total=-20 WHERE minimum_total=1;
UPDATE rule_animal_subtype_band SET maximum_total=20 WHERE minimum_total=13;

CREATE TABLE rule_animal_subtype_generation(
 subtype_rule_id bigint PRIMARY KEY REFERENCES rule_animal_subtype,strength_modifier smallint NOT NULL DEFAULT 0,dexterity_modifier smallint NOT NULL DEFAULT 0,
 endurance_modifier smallint NOT NULL DEFAULT 0,instinct_modifier smallint NOT NULL DEFAULT 0,pack_modifier smallint NOT NULL DEFAULT 0,
 choice_strength_or_dexterity_modifier smallint NOT NULL DEFAULT 0,speed_roll_modifier smallint NOT NULL,minimum_speed_multiplier smallint NOT NULL CHECK(minimum_speed_multiplier>=0)
);
INSERT INTO rule_animal_subtype_generation
SELECT rule_id,str,dex,en,ins,pack,choice,speed,minspeed FROM rule_animal_subtype s JOIN (VALUES
 ('chaser',0,4,0,2,2,0,-2,2),('killer',0,0,0,4,-2,4,-3,1),('pouncer',0,4,0,4,0,0,-4,1),('siren',0,0,0,0,-4,0,-4,0),('trapper',0,0,0,0,-2,0,-5,0),
 ('filter',0,0,4,0,0,0,-5,0),('grazer',0,0,0,2,4,0,-2,2),('intermittent',0,0,0,0,4,0,-4,1),('eater',0,0,4,0,2,0,-3,1),
 ('gatherer',0,0,0,0,2,0,-3,1),('hunter',0,0,0,2,0,0,-4,1),('carrion-eater',0,0,0,2,0,0,-3,1),('hijacker',2,0,0,0,2,0,-4,1),
 ('intimidator',0,0,0,0,0,0,-4,1),('reducer',0,0,0,0,4,0,-4,1)
) x(code,str,dex,en,ins,pack,choice,speed,minspeed) ON x.code=s.subtype_code;

CREATE TABLE rule_animal_size_band(minimum_total smallint PRIMARY KEY,maximum_total smallint NOT NULL,weight_kg integer NOT NULL,strength_dice smallint NOT NULL,strength_flat smallint,dexterity_dice smallint NOT NULL,dexterity_flat smallint,endurance_dice smallint NOT NULL,endurance_flat smallint,CHECK(minimum_total<=maximum_total));
INSERT INTO rule_animal_size_band VALUES
 (-20,1,1,0,1,1,NULL,0,1),(2,2,3,0,2,1,NULL,0,2),(3,3,6,1,NULL,2,NULL,1,NULL),(4,4,12,1,NULL,2,NULL,1,NULL),(5,5,25,2,NULL,3,NULL,2,NULL),(6,6,50,2,NULL,4,NULL,2,NULL),(7,7,100,3,NULL,3,NULL,3,NULL),(8,8,200,3,NULL,3,NULL,3,NULL),(9,9,400,4,NULL,2,NULL,4,NULL),(10,10,800,4,NULL,2,NULL,4,NULL),(11,11,1600,5,NULL,2,NULL,5,NULL),(12,12,3200,5,NULL,1,NULL,5,NULL),(13,13,5000,6,NULL,1,NULL,6,NULL),(14,14,10000,6,NULL,1,NULL,6,NULL),(15,15,15000,7,NULL,1,NULL,7,NULL),(16,16,20000,7,NULL,1,NULL,7,NULL),(17,17,25000,8,NULL,1,NULL,8,NULL),(18,18,30000,8,NULL,1,NULL,8,NULL),(19,19,35000,9,NULL,1,NULL,9,NULL),(20,40,40000,9,NULL,1,NULL,9,NULL);

CREATE TABLE rule_animal_number_appearing(minimum_pack smallint PRIMARY KEY,maximum_pack smallint NOT NULL,dice_count smallint NOT NULL,die_sides smallint NOT NULL,CHECK(minimum_pack<=maximum_pack));
INSERT INTO rule_animal_number_appearing VALUES(0,0,1,1),(1,2,1,3),(3,5,1,6),(6,8,2,6),(9,11,3,6),(12,14,4,6),(15,99,5,6);
CREATE TABLE rule_animal_damage_band(minimum_strength smallint PRIMARY KEY,maximum_strength smallint NOT NULL,damage_dice smallint NOT NULL,CHECK(minimum_strength<=maximum_strength));
INSERT INTO rule_animal_damage_band SELECT n,CASE WHEN n=91 THEN 999 ELSE n+9 END,(n+9)/10 FROM generate_series(1,91,10) n;

CREATE TABLE rule_animal_weapon_band(minimum_total smallint PRIMARY KEY,maximum_total smallint NOT NULL,weapon_spec text NOT NULL,CHECK(minimum_total<=maximum_total));
INSERT INTO rule_animal_weapon_band VALUES(-20,1,'hooves'),(2,2,'hooves,horns'),(3,3,'horns'),(4,4,'hooves,teeth'),(5,5,'horns,teeth'),(6,6,'thrasher'),(7,7,'claws'),(8,8,'teeth'),(9,9,'claws,teeth'),(10,10,'claws+1'),(11,11,'stinger'),(12,12,'teeth+1'),(13,13,'claws+1,teeth+1'),(14,14,'claws+1,stinger+1'),(15,15,'claws+2'),(16,16,'teeth+2'),(17,17,'claws+2,teeth+2'),(18,18,'claws+2,stinger+2'),(19,40,'projectile');
CREATE TABLE rule_animal_weapon(weapon_code text PRIMARY KEY,range_band text NOT NULL CHECK(range_band IN('melee-close','melee-extended','ranged-thrown')));
INSERT INTO rule_animal_weapon VALUES('claws','melee-extended'),('hooves','melee-extended'),('horns','melee-extended'),('projectile','ranged-thrown'),('stinger','melee-close'),('teeth','melee-close'),('thrasher','melee-close');
CREATE TABLE rule_animal_armor_band(minimum_total smallint PRIMARY KEY,maximum_total smallint NOT NULL,armor_rating smallint NOT NULL CHECK(armor_rating BETWEEN 0 AND 7),CHECK(minimum_total<=maximum_total));
INSERT INTO rule_animal_armor_band VALUES(-20,3,0),(4,5,1),(6,7,2),(8,9,3),(10,11,4),(12,13,5),(14,15,6),(16,40,7);

CREATE TABLE rule_wilderness_encounter_template(template_code text NOT NULL CHECK(template_code IN('1d6','2d6')),roll_total smallint NOT NULL,result_kind text NOT NULL CHECK(result_kind IN('carnivore','herbivore','omnivore','scavenger','event')),PRIMARY KEY(template_code,roll_total));
INSERT INTO rule_wilderness_encounter_template VALUES
 ('1d6',1,'scavenger'),('1d6',2,'herbivore'),('1d6',3,'herbivore'),('1d6',4,'herbivore'),('1d6',5,'omnivore'),('1d6',6,'carnivore'),
 ('2d6',2,'scavenger'),('2d6',3,'omnivore'),('2d6',4,'scavenger'),('2d6',5,'omnivore'),('2d6',6,'herbivore'),('2d6',7,'herbivore'),('2d6',8,'herbivore'),('2d6',9,'carnivore'),('2d6',10,'event'),('2d6',11,'carnivore'),('2d6',12,'carnivore');
