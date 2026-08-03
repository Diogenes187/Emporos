INSERT INTO src_locator(source_work_id,source_artifact_id,locator_type,heading_path,display_citation)
SELECT artifact.source_work_id,artifact.source_artifact_id,'heading','Environments and Hazards > Poisons',
 CASE work.work_code WHEN 'cepheus-engine.ogn' THEN 'Cepheus Engine SRD, Environments and Hazards: Poisons' ELSE 'Cepheus Engine v9.1, Environments and Hazards: Poisons' END
FROM src_artifact artifact JOIN src_work work USING(source_work_id)
WHERE artifact.source_uri IN('src/book3/environments-and-hazards.md','https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-environments-and-hazards/') ON CONFLICT DO NOTHING;
WITH package AS(SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine')
INSERT INTO rule_rule(content_package_id,rule_code,name,rule_category,rule_status,description)
SELECT content_package_id,'environment.poisons','Poisons','other','approved','Immediate Endurance resistance checks with fixed or rolled DMs and physical damage, characteristic damage, or unconsciousness on failure.' FROM package;
CREATE TABLE rule_poison_profile(
 poison_profile_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,rule_id bigint NOT NULL REFERENCES rule_rule(rule_id),poison_code text NOT NULL UNIQUE,name text NOT NULL,
 resistance_characteristic_rule_id bigint NOT NULL REFERENCES rule_characteristic(rule_id),dm_kind text NOT NULL CHECK(dm_kind IN('fixed','negative-die')),
 fixed_dm smallint,dm_dice_count smallint,dm_die_sides smallint,outcome_kind text NOT NULL CHECK(outcome_kind IN('physical-damage','unconsciousness','characteristic-damage')),
 damage_dice_count smallint NOT NULL CHECK(damage_dice_count BETWEEN 0 AND 2),damage_die_sides smallint,affected_characteristic_rule_id bigint REFERENCES rule_characteristic(rule_id),
 interval_kind text NOT NULL CHECK(interval_kind='immediate'),
 CHECK((dm_kind='fixed' AND fixed_dm IS NOT NULL AND dm_dice_count IS NULL AND dm_die_sides IS NULL) OR (dm_kind='negative-die' AND fixed_dm IS NULL AND dm_dice_count=1 AND dm_die_sides=6)),
 CHECK((damage_dice_count=0)=(damage_die_sides IS NULL)),CHECK(damage_die_sides IS NULL OR damage_die_sides=6),
 CHECK((outcome_kind='characteristic-damage')=(affected_characteristic_rule_id IS NOT NULL)),CHECK((outcome_kind='unconsciousness')=(damage_dice_count=0))
);
INSERT INTO rule_poison_profile(rule_id,poison_code,name,resistance_characteristic_rule_id,dm_kind,fixed_dm,dm_dice_count,dm_die_sides,outcome_kind,damage_dice_count,damage_die_sides,affected_characteristic_rule_id,interval_kind)
SELECT poison.rule_id,value.code,value.name,endurance.rule_id,value.dm_kind,value.fixed_dm,value.dm_dice,value.dm_sides,value.outcome,value.damage_dice,
 CASE WHEN value.damage_dice=0 THEN NULL ELSE 6 END,CASE WHEN value.outcome='characteristic-damage' THEN intelligence.rule_id END,'immediate'
FROM rule_rule poison CROSS JOIN rule_rule endurance CROSS JOIN rule_rule intelligence CROSS JOIN (VALUES
 ('arsenic','Arsenic','fixed',-2,NULL::smallint,NULL::smallint,'physical-damage',2),
 ('tranq-gas','Tranq Gas','negative-die',NULL::smallint,1::smallint,6::smallint,'unconsciousness',0),
 ('neurotoxin','Neurotoxin','fixed',-4,NULL::smallint,NULL::smallint,'characteristic-damage',1)
) value(code,name,dm_kind,fixed_dm,dm_dice,dm_sides,outcome,damage_dice)
WHERE poison.rule_code='environment.poisons' AND endurance.rule_code='characteristic.endurance' AND intelligence.rule_code='characteristic.intelligence';
INSERT INTO src_record_provenance(rule_id,content_package_id,source_locator_id,provenance_class,is_primary_citation)
SELECT rule.rule_id,rule.content_package_id,locator.source_locator_id,CASE work.work_code WHEN 'cepheus-engine.ogn' THEN 'direct' ELSE 'corroborating' END,work.work_code='cepheus-engine.ogn'
FROM rule_rule rule CROSS JOIN src_locator locator JOIN src_work work USING(source_work_id)
WHERE rule.rule_code='environment.poisons' AND locator.heading_path='Environments and Hazards > Poisons' AND work.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1');
