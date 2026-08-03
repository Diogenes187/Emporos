INSERT INTO src_locator(source_work_id,source_artifact_id,locator_type,heading_path,display_citation)
SELECT artifact.source_work_id,artifact.source_artifact_id,'heading',value.heading,
 CASE work.work_code WHEN 'cepheus-engine.ogn' THEN 'Cepheus Engine SRD, ' ELSE 'Cepheus Engine v9.1, ' END||value.citation
FROM src_artifact artifact JOIN src_work work USING(source_work_id) CROSS JOIN (VALUES
 ('Environments and Hazards > Radiation Exposure','Environments and Hazards: Radiation Exposure'),
 ('Environments and Hazards > Radiation Exposure > Common Radiation Exposure Sources','Environments and Hazards: Common Radiation Exposure Sources'),
 ('Environments and Hazards > Radiation Exposure > Radiation Effects','Environments and Hazards: Radiation Effects')) value(heading,citation)
WHERE artifact.source_uri IN('src/book3/environments-and-hazards.md','https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-environments-and-hazards/') ON CONFLICT DO NOTHING;
WITH package AS(SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine')
INSERT INTO rule_rule(content_package_id,rule_code,name,rule_category,rule_status,description)
SELECT content_package_id,'environment.radiation','Radiation Exposure','other','approved','Cumulative rads, instant and extended exposure, effective Endurance penalties, recurring radiation sickness, anti-radiation reduction, healing boundary, and unconsciousness.' FROM package;
CREATE TABLE rule_radiation_source_profile(
 radiation_source_profile_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,rule_id bigint NOT NULL REFERENCES rule_rule(rule_id),source_code text NOT NULL UNIQUE,name text NOT NULL,
 instant_dice_count smallint,instant_die_sides smallint,instant_multiplier smallint,extended_dice_count smallint NOT NULL CHECK(extended_dice_count BETWEEN 1 AND 12),
 extended_die_sides smallint NOT NULL CHECK(extended_die_sides=6),extended_multiplier smallint NOT NULL CHECK(extended_multiplier IN(1,10,100)),extended_interval text NOT NULL CHECK(extended_interval='hour'),
 CHECK((instant_dice_count IS NULL AND instant_die_sides IS NULL AND instant_multiplier IS NULL) OR (instant_dice_count BETWEEN 1 AND 4 AND instant_die_sides=6 AND instant_multiplier IN(1,10)))
);
INSERT INTO rule_radiation_source_profile(rule_id,source_code,name,instant_dice_count,instant_die_sides,instant_multiplier,extended_dice_count,extended_die_sides,extended_multiplier,extended_interval)
SELECT rule.rule_id,value.* FROM rule_rule rule CROSS JOIN (VALUES
 ('irradiated-low','Irradiated area, low level',NULL::smallint,NULL::smallint,NULL::smallint,1,6,1,'hour'),
 ('irradiated-moderate','Irradiated area, moderate level',NULL::smallint,NULL::smallint,NULL::smallint,2,6,1,'hour'),
 ('irradiated-high','Irradiated area, high level',NULL::smallint,NULL::smallint,NULL::smallint,6,6,1,'hour'),
 ('irradiated-severe','Irradiated area, severe level',NULL::smallint,NULL::smallint,NULL::smallint,12,6,1,'hour'),
 ('active-low','Active exposure, low level',3::smallint,6::smallint,1::smallint,3,6,10,'hour'),
 ('active-moderate','Active exposure, moderate level',1::smallint,6::smallint,10::smallint,1,6,100,'hour'),
 ('active-high','Active exposure, high level',2::smallint,6::smallint,10::smallint,2,6,100,'hour'),
 ('active-severe','Active exposure, severe level',4::smallint,6::smallint,10::smallint,3,6,100,'hour'))
 value(source_code,name,instant_dice_count,instant_die_sides,instant_multiplier,extended_dice_count,extended_die_sides,extended_multiplier,extended_interval)
WHERE rule.rule_code='environment.radiation';
CREATE TABLE rule_radiation_effect_band(
 radiation_effect_band_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,rule_id bigint NOT NULL REFERENCES rule_rule(rule_id),band_code text NOT NULL UNIQUE,name text NOT NULL,
 minimum_rads integer NOT NULL CHECK(minimum_rads>=0),maximum_rads integer,display_order smallint NOT NULL UNIQUE,effective_endurance_penalty smallint NOT NULL CHECK(effective_endurance_penalty BETWEEN 0 AND 10),
 resistance_dm smallint,damage_dice_count smallint NOT NULL CHECK(damage_dice_count BETWEEN 0 AND 1),damage_die_sides smallint,damage_flat_modifier smallint NOT NULL,
 interval_dice_count smallint NOT NULL CHECK(interval_dice_count BETWEEN 0 AND 2),interval_die_sides smallint,interval_unit text CHECK(interval_unit IN('hours','days','weeks')),
 CHECK(maximum_rads IS NULL OR maximum_rads>=minimum_rads),CHECK((damage_dice_count=0)=(damage_die_sides IS NULL)),CHECK((interval_dice_count=0)=(interval_die_sides IS NULL)),
 CHECK((interval_dice_count=0)=(interval_unit IS NULL)),CHECK(damage_die_sides IS NULL OR damage_die_sides=6),CHECK(interval_die_sides IS NULL OR interval_die_sides=6)
);
INSERT INTO rule_radiation_effect_band(rule_id,band_code,name,minimum_rads,maximum_rads,display_order,effective_endurance_penalty,resistance_dm,damage_dice_count,damage_die_sides,damage_flat_modifier,interval_dice_count,interval_die_sides,interval_unit)
SELECT rule.rule_id,value.* FROM rule_rule rule CROSS JOIN (VALUES
 ('mild','Mild',0,99,1,0,NULL::smallint,0,NULL::smallint,0,0,NULL::smallint,NULL::text),
 ('low','Low',100,199,2,1,1::smallint,1,6::smallint,0,1,6::smallint,'weeks'),
 ('moderate','Moderate',200,599,3,3,0::smallint,1,6::smallint,2,2,6::smallint,'days'),
 ('high','High',600,999,4,6,-1::smallint,1,6::smallint,4,1,6::smallint,'days'),
 ('severe','Severe',1000,NULL::integer,5,10,-2::smallint,1,6::smallint,6,1,6::smallint,'hours'))
 value(band_code,name,minimum_rads,maximum_rads,display_order,effective_endurance_penalty,resistance_dm,damage_dice_count,damage_die_sides,damage_flat_modifier,interval_dice_count,interval_die_sides,interval_unit)
WHERE rule.rule_code='environment.radiation';
INSERT INTO src_record_provenance(rule_id,content_package_id,source_locator_id,provenance_class,is_primary_citation)
SELECT rule.rule_id,rule.content_package_id,locator.source_locator_id,CASE work.work_code WHEN 'cepheus-engine.ogn' THEN 'direct' ELSE 'corroborating' END,work.work_code='cepheus-engine.ogn'
FROM rule_rule rule CROSS JOIN src_locator locator JOIN src_work work USING(source_work_id)
WHERE rule.rule_code='environment.radiation' AND locator.heading_path LIKE 'Environments and Hazards > Radiation Exposure%' AND work.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1');
INSERT INTO src_issue(issue_code,domain_code,issue_type,review_priority,issue_status,subject_code,title,problem_statement,published_value,calculated_value,reviewer_question,requested_evidence,engine_disposition,resolved_at,resolution_summary)
VALUES('environment.radiation.below-mild-wording','environment','source_conflict','low','resolved','effective-endurance','Radiation level below Mild wording',
 'The prose says levels below Mild reduce Endurance, while Mild is the lowest numeric band and its table row has no penalty.','below Mild','Low through Severe',
 'Does below mean numerically below Mild or rows printed below Mild?','Publisher errata or explicit clarification.','preserve_rule',clock_timestamp(),
 'The explicit effect table governs: Mild has no penalty; Low, Moderate, High, and Severe apply END penalties of 1, 3, 6, and 10.');
INSERT INTO src_issue_locator(source_issue_id,source_locator_id,evidence_role)
SELECT issue.source_issue_id,locator.source_locator_id,CASE work.work_code WHEN 'cepheus-engine.ogn' THEN 'primary' ELSE 'corroborating' END
FROM src_issue issue CROSS JOIN src_locator locator JOIN src_work work USING(source_work_id)
WHERE issue.issue_code='environment.radiation.below-mild-wording' AND locator.heading_path='Environments and Hazards > Radiation Exposure' AND work.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1');
INSERT INTO rule_interpretation(rule_id,interpretation_type,decision_register_entry,rationale)
SELECT rule_id,'agreed_interpretation','CE-ENV-003','Agreed 2026-08-02: the explicit radiation effect table controls; Mild has no END penalty and Low through Severe apply the listed penalties.'
FROM rule_rule WHERE rule_code='environment.radiation';
