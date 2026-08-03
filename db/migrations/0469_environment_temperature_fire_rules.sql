INSERT INTO src_locator(source_work_id,source_artifact_id,locator_type,heading_path,display_citation)
SELECT artifact.source_work_id,artifact.source_artifact_id,'heading',value.heading,
 CASE work.work_code WHEN 'cepheus-engine.ogn' THEN 'Cepheus Engine SRD, ' ELSE 'Cepheus Engine v9.1, ' END||value.citation
FROM src_artifact artifact JOIN src_work work USING(source_work_id) CROSS JOIN (VALUES
 ('Environments and Hazards > Extremes of Temperature','Environments and Hazards: Extremes of Temperature'),
 ('Environments and Hazards > Extremes of Temperature > Catching on Fire','Environments and Hazards: Catching on Fire')
) value(heading,citation)
WHERE artifact.source_uri IN('src/book3/environments-and-hazards.md','https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-environments-and-hazards/') ON CONFLICT DO NOTHING;

WITH package AS(SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine')
INSERT INTO rule_rule(content_package_id,rule_code,name,rule_category,rule_status,description)
SELECT content_package_id,value.code,value.name,'other','approved',value.description FROM package CROSS JOIN (VALUES
 ('environment.extreme-temperature','Extremes of Temperature','Eleven Celsius thresholds define unprotected damage dice and round or hour cadence.'),
 ('environment.catching-fire','Catching on Fire','Difficult Dexterity checks avoid ignition or end burning; failure deals 2D6, automatic methods extinguish, and improvised smothering grants DM+2.')
) value(code,name,description);

CREATE TABLE rule_extreme_temperature_band(
 temperature_band_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,rule_id bigint NOT NULL REFERENCES rule_rule(rule_id),display_order smallint NOT NULL UNIQUE,
 boundary_celsius smallint NOT NULL,boundary_relation text NOT NULL CHECK(boundary_relation IN('below','at','above')),
 damage_dice_count smallint NOT NULL CHECK(damage_dice_count BETWEEN 0 AND 3),damage_die_sides smallint CHECK(damage_die_sides=6),
 damage_interval text CHECK(damage_interval IN('round','hour')),example text NOT NULL,
 CHECK((damage_dice_count=0)=(damage_die_sides IS NULL)),CHECK((damage_dice_count=0)=(damage_interval IS NULL)),UNIQUE(rule_id,boundary_celsius,boundary_relation)
);
INSERT INTO rule_extreme_temperature_band(rule_id,display_order,boundary_celsius,boundary_relation,damage_dice_count,damage_die_sides,damage_interval,example)
SELECT rule.rule_id,value.* FROM rule_rule rule CROSS JOIN (VALUES
 (1,-200,'below',3,6,'round','Absolute Zero, Pluto'),(2,-200,'at',2,6,'round','Liquid nitrogen, Neptune'),
 (3,-100,'at',1,6,'round','Ceres'),(4,-50,'at',2,6,'hour','Mars'),(5,-25,'at',1,6,'hour','Arctic'),
 (6,0,'at',0,NULL,NULL,'Water melting point'),(7,50,'at',1,6,'hour','Very hot desert'),
 (8,100,'at',2,6,'hour','Water boiling point'),(9,200,'at',1,6,'round','Mercury'),
 (10,500,'at',2,6,'round','Venus'),(11,500,'above',3,6,'round','Surface of the sun')
) value(display_order,boundary_celsius,boundary_relation,damage_dice_count,damage_die_sides,damage_interval,example)
WHERE rule.rule_code='environment.extreme-temperature';

CREATE TABLE rule_catching_fire(
 rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),check_characteristic_rule_id bigint NOT NULL REFERENCES rule_characteristic(rule_id),
 difficulty_rule_id bigint NOT NULL REFERENCES rule_difficulty(rule_id),damage_dice_count smallint NOT NULL CHECK(damage_dice_count=2),
 damage_die_sides smallint NOT NULL CHECK(damage_die_sides=6),damage_immediate_on_ignition boolean NOT NULL CHECK(damage_immediate_on_ignition),
 repeat_check_each_round boolean NOT NULL CHECK(repeat_check_each_round),success_extinguishes boolean NOT NULL CHECK(success_extinguishes),
 automatic_extinguishing_allowed boolean NOT NULL CHECK(automatic_extinguishing_allowed),improvised_smothering_dm smallint NOT NULL CHECK(improvised_smothering_dm=2)
);
INSERT INTO rule_catching_fire SELECT fire.rule_id,dexterity.rule_id,difficulty.rule_id,2,6,true,true,true,true,2
FROM rule_rule fire CROSS JOIN rule_rule dexterity CROSS JOIN rule_rule difficulty
WHERE fire.rule_code='environment.catching-fire' AND dexterity.rule_code='characteristic.dexterity' AND difficulty.rule_code='difficulty.difficult';

INSERT INTO src_record_provenance(rule_id,content_package_id,source_locator_id,provenance_class,is_primary_citation)
SELECT rule.rule_id,rule.content_package_id,locator.source_locator_id,CASE work.work_code WHEN 'cepheus-engine.ogn' THEN 'direct' ELSE 'corroborating' END,work.work_code='cepheus-engine.ogn'
FROM rule_rule rule JOIN src_locator locator ON locator.heading_path=CASE rule.rule_code WHEN 'environment.extreme-temperature' THEN 'Environments and Hazards > Extremes of Temperature' ELSE 'Environments and Hazards > Extremes of Temperature > Catching on Fire' END
JOIN src_work work USING(source_work_id) WHERE rule.rule_code IN('environment.extreme-temperature','environment.catching-fire') AND work.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1');
