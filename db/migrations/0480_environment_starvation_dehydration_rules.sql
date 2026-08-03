INSERT INTO src_locator(source_work_id,source_artifact_id,locator_type,heading_path,display_citation)
SELECT artifact.source_work_id,artifact.source_artifact_id,'heading','Environments and Hazards > Starvation and Dehydration',CASE work.work_code WHEN 'cepheus-engine.ogn' THEN 'Cepheus Engine SRD, Environments and Hazards: Starvation and Dehydration' ELSE 'Cepheus Engine v9.1, Environments and Hazards: Starvation and Dehydration' END
FROM src_artifact artifact JOIN src_work work USING(source_work_id) WHERE artifact.source_uri IN('src/book3/environments-and-hazards.md','https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-environments-and-hazards/') ON CONFLICT DO NOTHING;
WITH package AS(SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine')
INSERT INTO rule_rule(content_package_id,rule_code,name,rule_category,rule_status,description)
SELECT content_package_id,'environment.starvation-dehydration','Starvation and Dehydration','other','approved','Daily food and fluid requirements, Endurance-based water grace, three-day food grace, escalating Routine Endurance checks, damage, and recovery lock until relieved.' FROM package;
CREATE TABLE rule_deprivation_profile(
 deprivation_profile_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,rule_id bigint NOT NULL REFERENCES rule_rule(rule_id),deprivation_code text NOT NULL UNIQUE,name text NOT NULL,
 normal_daily_requirement numeric(8,2) NOT NULL CHECK(normal_daily_requirement>0),requirement_unit text NOT NULL,hot_climate_multiplier_min smallint,hot_climate_multiplier_max smallint,
 grace_base_seconds bigint NOT NULL CHECK(grace_base_seconds>=0),grace_endurance_seconds bigint NOT NULL CHECK(grace_endurance_seconds>=0),check_interval_seconds bigint NOT NULL CHECK(check_interval_seconds>0),
 difficulty_rule_id bigint NOT NULL REFERENCES rule_difficulty(rule_id),previous_check_dm_step smallint NOT NULL CHECK(previous_check_dm_step=-1),damage_dice_count smallint NOT NULL CHECK(damage_dice_count=1),damage_die_sides smallint NOT NULL CHECK(damage_die_sides=6),
 recovery_locked_until_relief boolean NOT NULL CHECK(recovery_locked_until_relief),CHECK((hot_climate_multiplier_min IS NULL)=(hot_climate_multiplier_max IS NULL)),CHECK(hot_climate_multiplier_min IS NULL OR hot_climate_multiplier_max>=hot_climate_multiplier_min)
);
INSERT INTO rule_deprivation_profile(rule_id,deprivation_code,name,normal_daily_requirement,requirement_unit,hot_climate_multiplier_min,hot_climate_multiplier_max,grace_base_seconds,grace_endurance_seconds,check_interval_seconds,difficulty_rule_id,previous_check_dm_step,damage_dice_count,damage_die_sides,recovery_locked_until_relief)
SELECT rule.rule_id,value.code,value.name,value.requirement,value.unit,value.hot_min,value.hot_max,value.base_seconds,value.end_seconds,value.interval_seconds,difficulty.rule_id,-1,1,6,true
FROM rule_rule rule CROSS JOIN rule_rule difficulty CROSS JOIN (VALUES
 ('dehydration','Dehydration',1.00::numeric,'gallon-fluid-per-day',2::smallint,3::smallint,72000::bigint,7200::bigint,3600::bigint),
 ('starvation','Starvation',1.00::numeric,'pound-food-per-day',NULL::smallint,NULL::smallint,259200::bigint,0::bigint,86400::bigint)) value(code,name,requirement,unit,hot_min,hot_max,base_seconds,end_seconds,interval_seconds)
WHERE rule.rule_code='environment.starvation-dehydration' AND difficulty.rule_code='difficulty.routine';
INSERT INTO src_record_provenance(rule_id,content_package_id,source_locator_id,provenance_class,is_primary_citation)
SELECT rule.rule_id,rule.content_package_id,locator.source_locator_id,CASE work.work_code WHEN 'cepheus-engine.ogn' THEN 'direct' ELSE 'corroborating' END,work.work_code='cepheus-engine.ogn'
FROM rule_rule rule CROSS JOIN src_locator locator JOIN src_work work USING(source_work_id) WHERE rule.rule_code='environment.starvation-dehydration' AND locator.heading_path='Environments and Hazards > Starvation and Dehydration' AND work.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1');
