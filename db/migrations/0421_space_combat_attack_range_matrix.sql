INSERT INTO src_locator(source_work_id,source_artifact_id,locator_type,heading_path,display_citation)
SELECT a.source_work_id,a.source_artifact_id,'heading','Space Combat > Range > Attack Difficulties by Weapon Type',
 CASE w.work_code WHEN 'cepheus-engine.ogn' THEN 'Cepheus Engine SRD, Space Combat: Attack Difficulties by Weapon Type'
 ELSE 'Cepheus Engine v9.1, Space Combat: Attack Difficulties by Weapon Type' END
FROM src_artifact a JOIN src_work w USING(source_work_id)
WHERE (w.work_code='cepheus-engine.ogn' AND a.source_uri LIKE '%cepheus-engine-space-combat/')
 OR (w.work_code='cepheus-engine.github-v9.1' AND a.source_uri='src/book2/space-combat.md') ON CONFLICT DO NOTHING;
WITH p AS (SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine')
INSERT INTO rule_rule(content_package_id,rule_code,name,rule_category,rule_status,description)
SELECT content_package_id,'combat.space.attack-range-matrix','Space Combat Attack Range Matrix','combat','approved',
 'Published weapon-type Difficulty or unavailability at each space-combat range.' FROM p;
CREATE TABLE rule_space_combat_attack_range(
 rule_id bigint NOT NULL REFERENCES rule_rule(rule_id),weapon_profile_code text NOT NULL,
 range_band_code text NOT NULL REFERENCES rule_space_range_band(range_band_code),
 difficulty_rule_id bigint REFERENCES rule_difficulty(rule_id),available boolean NOT NULL,
 PRIMARY KEY(weapon_profile_code,range_band_code),
 CHECK(weapon_profile_code IN('pulse-laser','beam-laser','particle-beam','fusion-gun','meson-gun','sandcaster')),
 CHECK(available=(difficulty_rule_id IS NOT NULL))
);
WITH matrix(weapon_profile_code,range_band_code,difficulty_code) AS (VALUES
 ('pulse-laser','adjacent','difficulty.difficult'),('pulse-laser','close','difficulty.difficult'),('pulse-laser','short','difficulty.average'),('pulse-laser','medium','difficulty.difficult'),('pulse-laser','long','difficulty.difficult'),('pulse-laser','very_long','difficulty.very-difficult'),('pulse-laser','distant',NULL),
 ('beam-laser','adjacent','difficulty.difficult'),('beam-laser','close','difficulty.difficult'),('beam-laser','short','difficulty.difficult'),('beam-laser','medium','difficulty.average'),('beam-laser','long','difficulty.difficult'),('beam-laser','very_long','difficulty.difficult'),('beam-laser','distant','difficulty.difficult'),
 ('particle-beam','adjacent','difficulty.very-difficult'),('particle-beam','close','difficulty.difficult'),('particle-beam','short','difficulty.difficult'),('particle-beam','medium','difficulty.difficult'),('particle-beam','long','difficulty.average'),('particle-beam','very_long','difficulty.difficult'),('particle-beam','distant','difficulty.difficult'),
 ('fusion-gun','adjacent','difficulty.difficult'),('fusion-gun','close','difficulty.difficult'),('fusion-gun','short','difficulty.difficult'),('fusion-gun','medium','difficulty.average'),('fusion-gun','long','difficulty.difficult'),('fusion-gun','very_long','difficulty.difficult'),('fusion-gun','distant','difficulty.difficult'),
 ('meson-gun','adjacent','difficulty.very-difficult'),('meson-gun','close','difficulty.very-difficult'),('meson-gun','short','difficulty.difficult'),('meson-gun','medium','difficulty.difficult'),('meson-gun','long','difficulty.average'),('meson-gun','very_long','difficulty.difficult'),('meson-gun','distant','difficulty.difficult'),
 ('sandcaster','adjacent','difficulty.routine'),('sandcaster','close','difficulty.average'),('sandcaster','short','difficulty.difficult'),('sandcaster','medium',NULL),('sandcaster','long',NULL),('sandcaster','very_long',NULL),('sandcaster','distant',NULL)
), parent AS (SELECT rule_id FROM rule_rule WHERE rule_code='combat.space.attack-range-matrix')
INSERT INTO rule_space_combat_attack_range(rule_id,weapon_profile_code,range_band_code,difficulty_rule_id,available)
SELECT parent.rule_id,m.weapon_profile_code,m.range_band_code,d.rule_id,m.difficulty_code IS NOT NULL
FROM matrix m CROSS JOIN parent LEFT JOIN rule_rule d ON d.rule_code=m.difficulty_code;
CREATE TABLE rule_space_combat_weapon_profile(
 weapon_rule_id bigint PRIMARY KEY REFERENCES ship_weapon_definition(weapon_rule_id),
 weapon_profile_code text NOT NULL,uses_special_attack_procedure boolean NOT NULL,
 CHECK(weapon_profile_code IN('pulse-laser','beam-laser','particle-beam','fusion-gun','meson-gun','sandcaster'))
);
INSERT INTO rule_space_combat_weapon_profile
SELECT weapon_rule_id,CASE
 WHEN weapon_code IN('particle-beam-turret','particle-beam-bay') THEN 'particle-beam'
 WHEN weapon_code='fusion-gun-bay' THEN 'fusion-gun' WHEN weapon_code='meson-gun-bay' THEN 'meson-gun'
 ELSE weapon_code END,false FROM ship_weapon_definition
WHERE weapon_code IN('pulse-laser','beam-laser','particle-beam-turret','particle-beam-bay','fusion-gun-bay','meson-gun-bay','sandcaster');
INSERT INTO src_record_provenance(rule_id,content_package_id,source_locator_id,provenance_class,is_primary_citation)
SELECT r.rule_id,r.content_package_id,l.source_locator_id,CASE w.work_code WHEN 'cepheus-engine.ogn' THEN 'direct' ELSE 'corroborating' END,w.work_code='cepheus-engine.ogn'
FROM rule_rule r CROSS JOIN src_locator l JOIN src_work w USING(source_work_id)
WHERE r.rule_code='combat.space.attack-range-matrix' AND l.heading_path='Space Combat > Range > Attack Difficulties by Weapon Type'
 AND w.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1');
