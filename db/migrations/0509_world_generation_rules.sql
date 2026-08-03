INSERT INTO src_locator(source_work_id,source_artifact_id,locator_type,heading_path,display_citation)
SELECT artifact.source_work_id,artifact.source_artifact_id,'heading',heading.heading_path,
       CASE work.work_code WHEN 'cepheus-engine.ogn' THEN 'Cepheus Engine SRD, ' ELSE 'Cepheus Engine v9.1, ' END || heading.citation
FROM src_artifact artifact JOIN src_work work USING(source_work_id)
CROSS JOIN (VALUES
 ('Worlds > Star Mapping','Worlds: Star Mapping'),
 ('Worlds > World Size','Worlds: World Size'),
 ('Worlds > Atmosphere','Worlds: Atmosphere'),
 ('Worlds > Hydrographics','Worlds: Hydrographics'),
 ('Worlds > World Population','Worlds: World Population'),
 ('Worlds > Primary Starport','Worlds: Primary Starport'),
 ('Worlds > World Government','Worlds: World Government'),
 ('Worlds > Law Level','Worlds: Law Level'),
 ('Worlds > Technology Level','Worlds: Technology Level'),
 ('Worlds > Trade Codes','Worlds: Trade Codes'),
 ('Worlds > Planetoid Belt Presence','Worlds: Planetoid Belt Presence'),
 ('Worlds > Gas Giant Presence','Worlds: Gas Giant Presence'),
 ('Worlds > Bases','Worlds: Bases'),
 ('Worlds > Travel Zones','Worlds: Travel Zones')
) heading(heading_path,citation)
WHERE (work.work_code='cepheus-engine.github-v9.1' AND artifact.source_uri='src/book3/worlds.md')
   OR (work.work_code='cepheus-engine.ogn' AND artifact.source_uri='https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-worlds/')
ON CONFLICT DO NOTHING;

WITH package AS(SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine')
INSERT INTO rule_rule(content_package_id,rule_code,name,rule_category,rule_status,description)
SELECT content_package_id,code,name,'world','approved',description FROM package CROSS JOIN (VALUES
 ('world.subsector-star-mapping','Subsector Star Mapping','Each subsector hex uses one D6 plus regional density DM; an adjusted 4+ contains a system.'),
 ('world.uwp-generation','Universal World Profile Generation','Sequential audited generation of Size, Atmosphere, Hydrographics, Population, Starport, Government, Law Level, and Technology Level.'),
 ('world.system-details-generation','World System Details Generation','Audited population multiplier, planetoid belts, gas giants, and naval, scout, or pirate bases.'),
 ('world.travel-zone-classification','World Travel Zone Classification','Normalized Amber candidate conditions while Red interdiction remains Referee-assigned campaign state.')
) r(code,name,description);

CREATE TABLE rule_world_hex_density(
 density_code text PRIMARY KEY CHECK(density_code IN('rift','sparse','standard','dense')),
 dice_count smallint NOT NULL CHECK(dice_count=1), die_sides smallint NOT NULL CHECK(die_sides=6),
 density_modifier smallint NOT NULL, presence_target smallint NOT NULL CHECK(presence_target=4)
);
INSERT INTO rule_world_hex_density VALUES('rift',1,6,-2,4),('sparse',1,6,-1,4),('standard',1,6,0,4),('dense',1,6,1,4);

CREATE TABLE rule_world_generation_component(
 component_code text PRIMARY KEY CHECK(component_code IN('size','atmosphere','hydrographics','population','starport','government','law_level','technology_level')),
 sequence_order smallint NOT NULL UNIQUE, dice_count smallint NOT NULL CHECK(dice_count IN(1,2)), die_sides smallint NOT NULL CHECK(die_sides=6),
 flat_modifier smallint NOT NULL, dependent_component text REFERENCES rule_world_generation_component(component_code),
 dependent_multiplier smallint NOT NULL DEFAULT 0, minimum_value smallint, maximum_value smallint,
 forced_zero_when_component text REFERENCES rule_world_generation_component(component_code), forced_zero_maximum smallint,
 CHECK((forced_zero_when_component IS NULL)=(forced_zero_maximum IS NULL))
);
INSERT INTO rule_world_generation_component VALUES
 ('size',1,2,6,-2,NULL,0,0,10,NULL,NULL),
 ('atmosphere',2,2,6,-7,'size',1,0,15,'size',0),
 ('hydrographics',3,2,6,-7,'size',1,0,10,'size',1),
 ('population',4,2,6,-2,NULL,0,0,10,NULL,NULL),
 ('starport',5,2,6,-7,'population',1,NULL,NULL,NULL,NULL),
 ('government',6,2,6,-7,'population',1,0,15,'population',0),
 ('law_level',7,2,6,-7,'government',1,0,15,'government',0),
 ('technology_level',8,1,6,0,NULL,0,0,NULL,'population',0);

CREATE TABLE rule_world_generation_modifier(
 modifier_code text PRIMARY KEY, target_component text NOT NULL REFERENCES rule_world_generation_component(component_code),
 modifier_value smallint NOT NULL
);
CREATE TABLE rule_world_generation_modifier_condition(
 modifier_code text NOT NULL REFERENCES rule_world_generation_modifier(modifier_code), condition_order smallint NOT NULL,
 source_component text NOT NULL REFERENCES rule_world_generation_component(component_code), minimum_value smallint, maximum_value smallint,
 PRIMARY KEY(modifier_code,condition_order), CHECK(minimum_value IS NOT NULL OR maximum_value IS NOT NULL)
);
INSERT INTO rule_world_generation_modifier VALUES
 ('hydro-atmosphere-0-1', 'hydrographics',-4),('hydro-atmosphere-10-12','hydrographics',-4),('hydro-atmosphere-14','hydrographics',-2),
 ('population-size-0-2','population',-1),('population-atmosphere-10-15','population',-2),('population-atmosphere-6','population',3),
 ('population-atmosphere-5','population',1),('population-atmosphere-8','population',1),('population-dry-thin','population',-2),
 ('tech-size-0-1','technology_level',2),('tech-size-2-4','technology_level',1),('tech-atmosphere-0-3','technology_level',1),
 ('tech-atmosphere-10-15','technology_level',1),('tech-hydro-0','technology_level',1),('tech-hydro-9','technology_level',1),
 ('tech-hydro-10','technology_level',2),('tech-population-1-5','technology_level',1),('tech-population-9','technology_level',1),
 ('tech-population-10','technology_level',2),('tech-government-0','technology_level',1),('tech-government-5','technology_level',1),
 ('tech-government-7','technology_level',2),('tech-government-13-14','technology_level',-2);
INSERT INTO rule_world_generation_modifier_condition VALUES
 ('hydro-atmosphere-0-1',1,'atmosphere',0,1),('hydro-atmosphere-10-12',1,'atmosphere',10,12),('hydro-atmosphere-14',1,'atmosphere',14,14),
 ('population-size-0-2',1,'size',0,2),('population-atmosphere-10-15',1,'atmosphere',10,15),('population-atmosphere-6',1,'atmosphere',6,6),
 ('population-atmosphere-5',1,'atmosphere',5,5),('population-atmosphere-8',1,'atmosphere',8,8),
 ('population-dry-thin',1,'hydrographics',0,0),('population-dry-thin',2,'atmosphere',NULL,2),
 ('tech-size-0-1',1,'size',0,1),('tech-size-2-4',1,'size',2,4),('tech-atmosphere-0-3',1,'atmosphere',0,3),
 ('tech-atmosphere-10-15',1,'atmosphere',10,15),('tech-hydro-0',1,'hydrographics',0,0),('tech-hydro-9',1,'hydrographics',9,9),
 ('tech-hydro-10',1,'hydrographics',10,10),('tech-population-1-5',1,'population',1,5),('tech-population-9',1,'population',9,9),
 ('tech-population-10',1,'population',10,10),('tech-government-0',1,'government',0,0),('tech-government-5',1,'government',5,5),
 ('tech-government-7',1,'government',7,7),('tech-government-13-14',1,'government',13,14);

CREATE TABLE rule_world_starport_band(minimum_total smallint PRIMARY KEY,maximum_total smallint,starport_code text NOT NULL REFERENCES rule_starport_class(starport_code),CHECK(maximum_total IS NULL OR minimum_total<=maximum_total));
INSERT INTO rule_world_starport_band VALUES(-20,2,'X'),(3,4,'E'),(5,6,'D'),(7,8,'C'),(9,10,'B'),(11,NULL,'A');
CREATE TABLE rule_world_starport_technology_modifier(
 starport_code text PRIMARY KEY REFERENCES rule_starport_class(starport_code),modifier_value smallint NOT NULL
);
INSERT INTO rule_world_starport_technology_modifier VALUES('A',6),('B',4),('C',2),('D',0),('E',0),('X',-4);

CREATE TABLE rule_world_technology_minimum(
 minimum_code text PRIMARY KEY,minimum_technology_level smallint NOT NULL CHECK(minimum_technology_level IN(4,5,7))
);
CREATE TABLE rule_world_technology_minimum_condition(
 minimum_code text NOT NULL REFERENCES rule_world_technology_minimum(minimum_code),condition_group smallint NOT NULL,condition_order smallint NOT NULL,
 source_component text NOT NULL REFERENCES rule_world_generation_component(component_code),minimum_value smallint,maximum_value smallint,
 PRIMARY KEY(minimum_code,condition_group,condition_order),CHECK(minimum_value IS NOT NULL OR maximum_value IS NOT NULL)
);
INSERT INTO rule_world_technology_minimum VALUES('hydro-extreme-populated',4),('tainted-atmosphere',5),('hostile-atmosphere',7),('dense-thin-water',7);
INSERT INTO rule_world_technology_minimum_condition VALUES
 ('hydro-extreme-populated',1,1,'hydrographics',0,0),('hydro-extreme-populated',1,2,'population',6,NULL),
 ('hydro-extreme-populated',2,1,'hydrographics',10,10),('hydro-extreme-populated',2,2,'population',6,NULL),
 ('tainted-atmosphere',1,1,'atmosphere',4,4),('tainted-atmosphere',2,1,'atmosphere',7,7),('tainted-atmosphere',3,1,'atmosphere',9,9),
 ('hostile-atmosphere',1,1,'atmosphere',0,3),('hostile-atmosphere',2,1,'atmosphere',10,12),
 ('dense-thin-water',1,1,'atmosphere',13,14),('dense-thin-water',1,2,'hydrographics',10,10);

CREATE TABLE rule_world_system_detail_procedure(
 rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),population_dice smallint NOT NULL CHECK(population_dice=2),population_flat_modifier smallint NOT NULL CHECK(population_flat_modifier=-2),
 belt_presence_target smallint NOT NULL CHECK(belt_presence_target=4),belt_count_flat_modifier smallint NOT NULL CHECK(belt_count_flat_modifier=-3),
 gas_presence_target smallint NOT NULL CHECK(gas_presence_target=5),gas_count_flat_modifier smallint NOT NULL CHECK(gas_count_flat_modifier=-2),minimum_present_count smallint NOT NULL CHECK(minimum_present_count=1),
 naval_target smallint NOT NULL CHECK(naval_target=8),scout_target smallint NOT NULL CHECK(scout_target=7),pirate_target smallint NOT NULL CHECK(pirate_target=12)
);
INSERT INTO rule_world_system_detail_procedure SELECT rule_id,2,-2,4,-3,5,-2,1,8,7,12 FROM rule_rule WHERE rule_code='world.system-details-generation';

CREATE TABLE rule_world_base_eligibility(
 base_kind text NOT NULL CHECK(base_kind IN('naval','scout','pirate')),starport_code text NOT NULL REFERENCES rule_starport_class(starport_code),roll_modifier smallint NOT NULL,target_number smallint NOT NULL,
 requires_no_naval boolean NOT NULL DEFAULT false,PRIMARY KEY(base_kind,starport_code)
);
INSERT INTO rule_world_base_eligibility VALUES
 ('naval','A',0,8,false),('naval','B',0,8,false),('scout','A',-3,7,false),('scout','B',-2,7,false),('scout','C',-1,7,false),('scout','D',0,7,false),
 ('pirate','B',0,12,true),('pirate','C',0,12,true),('pirate','D',0,12,true),('pirate','E',0,12,true),('pirate','X',0,12,true);

CREATE TABLE rule_world_amber_candidate_condition(
 condition_code text PRIMARY KEY,profile_component text NOT NULL CHECK(profile_component IN('atmosphere','government','law_level')),
 minimum_value smallint,maximum_value smallint,CHECK(minimum_value IS NOT NULL OR maximum_value IS NOT NULL)
);
INSERT INTO rule_world_amber_candidate_condition VALUES
 ('hazardous-atmosphere','atmosphere',10,NULL),('no-government','government',0,0),('balkanized-government','government',7,7),('charismatic-dictator','government',10,10),
 ('no-law','law_level',0,0),('extreme-law','law_level',9,NULL);

INSERT INTO src_record_provenance(rule_id,content_package_id,source_locator_id,provenance_class,is_primary_citation)
SELECT rule.rule_id,rule.content_package_id,locator.source_locator_id,
       CASE work.work_code WHEN 'cepheus-engine.ogn' THEN 'direct' ELSE 'corroborating' END,work.work_code='cepheus-engine.ogn'
FROM rule_rule rule JOIN (VALUES
 ('world.subsector-star-mapping','Worlds > Star Mapping'),
 ('world.uwp-generation','Worlds > World Size'),('world.uwp-generation','Worlds > Atmosphere'),('world.uwp-generation','Worlds > Hydrographics'),
 ('world.uwp-generation','Worlds > World Population'),('world.uwp-generation','Worlds > Primary Starport'),('world.uwp-generation','Worlds > World Government'),
 ('world.uwp-generation','Worlds > Law Level'),('world.uwp-generation','Worlds > Technology Level'),('world.uwp-generation','Worlds > Trade Codes'),
 ('world.system-details-generation','Worlds > World Population'),('world.system-details-generation','Worlds > Planetoid Belt Presence'),
 ('world.system-details-generation','Worlds > Gas Giant Presence'),('world.system-details-generation','Worlds > Bases'),
 ('world.travel-zone-classification','Worlds > Travel Zones')
) link(rule_code,heading_path) ON link.rule_code=rule.rule_code
JOIN src_locator locator ON locator.heading_path=link.heading_path JOIN src_work work USING(source_work_id)
WHERE work.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1')
ON CONFLICT DO NOTHING;
