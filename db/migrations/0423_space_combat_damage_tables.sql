INSERT INTO src_locator(source_work_id,source_artifact_id,locator_type,heading_path,display_citation)
SELECT a.source_work_id,a.source_artifact_id,'heading',v.heading,
 CASE w.work_code WHEN 'cepheus-engine.ogn' THEN 'Cepheus Engine SRD, Space Combat: '||v.label ELSE 'Cepheus Engine v9.1, Space Combat: '||v.label END
FROM src_artifact a JOIN src_work w USING(source_work_id) CROSS JOIN (VALUES
 ('Space Combat > Damage > Space Combat Damage','Space Combat Damage'),
 ('Space Combat > Damage > Space Combat Hit Location','Space Combat Hit Location')) v(heading,label)
WHERE (w.work_code='cepheus-engine.ogn' AND a.source_uri LIKE '%cepheus-engine-space-combat/')
 OR (w.work_code='cepheus-engine.github-v9.1' AND a.source_uri='src/book2/space-combat.md') ON CONFLICT DO NOTHING;
WITH p AS (SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine')
INSERT INTO rule_rule(content_package_id,rule_code,name,rule_category,rule_status,description)
SELECT content_package_id,v.code,v.name,'combat','approved',v.description FROM p CROSS JOIN (VALUES
 ('combat.space.damage-bands','Space Combat Damage Bands','Armor-adjusted damage converts to single, double, and triple location hits.'),
 ('combat.space.hit-locations','Space Combat Hit Locations','Two-die location routing for external vessel, internal vessel, and small craft damage.')) v(code,name,description);
CREATE TABLE rule_space_combat_damage_band(
 damage_band_rule_id bigint NOT NULL REFERENCES rule_rule(rule_id),damage_range int4range NOT NULL,
 single_hit_groups smallint NOT NULL CHECK(single_hit_groups>=0),double_hit_groups smallint NOT NULL CHECK(double_hit_groups>=0),
 triple_hit_groups smallint NOT NULL CHECK(triple_hit_groups>=0),display_order smallint NOT NULL UNIQUE,
 PRIMARY KEY(damage_band_rule_id,damage_range),CHECK(NOT isempty(damage_range))
);
ALTER TABLE rule_space_combat_damage_band ADD CONSTRAINT rule_space_combat_damage_band_no_overlap
 EXCLUDE USING gist(damage_band_rule_id WITH =,damage_range WITH &&);
WITH r AS (SELECT rule_id FROM rule_rule WHERE rule_code='combat.space.damage-bands')
INSERT INTO rule_space_combat_damage_band SELECT r.rule_id,v.damage_range,v.singles,v.doubles,v.triples,v.ord FROM r CROSS JOIN (VALUES
 (int4range(NULL,1,'[)'),0,0,0,1),(int4range(1,5,'[)'),1,0,0,2),(int4range(5,9,'[)'),2,0,0,3),
 (int4range(9,13,'[)'),0,1,0,4),(int4range(13,17,'[)'),3,0,0,5),(int4range(17,21,'[)'),2,1,0,6),
 (int4range(21,25,'[)'),0,2,0,7),(int4range(25,29,'[)'),0,0,1,8),(int4range(29,33,'[)'),1,0,1,9),
 (int4range(33,37,'[)'),0,1,1,10),(int4range(37,41,'[)'),1,1,1,11),(int4range(41,45,'[)'),0,0,2,12)
) v(damage_range,singles,doubles,triples,ord);
CREATE TABLE rule_space_combat_excess_damage(
 damage_band_rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),threshold_exclusive integer NOT NULL CHECK(threshold_exclusive=44),
 points_per_single_hit smallint NOT NULL CHECK(points_per_single_hit=3),points_per_double_hit smallint NOT NULL CHECK(points_per_double_hit=6),
 cumulative boolean NOT NULL
);
INSERT INTO rule_space_combat_excess_damage SELECT rule_id,44,3,6,true FROM rule_rule WHERE rule_code='combat.space.damage-bands';
CREATE TABLE rule_space_combat_hit_location(
 hit_location_rule_id bigint NOT NULL REFERENCES rule_rule(rule_id),roll_total smallint NOT NULL CHECK(roll_total BETWEEN 2 AND 12),
 external_vessel_location text NOT NULL,internal_vessel_location text NOT NULL,small_craft_location text NOT NULL,
 PRIMARY KEY(hit_location_rule_id,roll_total),
 CHECK(external_vessel_location IN('hull','sensors','m-drive','turret','armor','fuel')),
 CHECK(internal_vessel_location IN('structure','power-plant','j-drive','bay','crew','hold','bridge')),
 CHECK(small_craft_location IN('hull','power-plant','hold','fuel','armor','turret','m-drive','crew','bridge'))
);
WITH r AS (SELECT rule_id FROM rule_rule WHERE rule_code='combat.space.hit-locations')
INSERT INTO rule_space_combat_hit_location SELECT r.rule_id,v.* FROM r CROSS JOIN (VALUES
 (2,'hull','structure','hull'),(3,'sensors','power-plant','power-plant'),(4,'m-drive','j-drive','hold'),
 (5,'turret','bay','fuel'),(6,'hull','structure','hull'),(7,'armor','crew','armor'),
 (8,'hull','structure','hull'),(9,'fuel','hold','turret'),(10,'m-drive','j-drive','m-drive'),
 (11,'sensors','power-plant','crew'),(12,'hull','bridge','bridge')) v(roll_total,external_location,internal_location,small_location);
INSERT INTO rule_interpretation(rule_id,interpretation_type,decision_register_entry,rationale)
SELECT rule_id,'agreed_interpretation','CE-SC-006',
 'Raymond approved continuous non-overlapping four-point damage bands: 9-12, 13-16, 17-20, 21-24, and 25-28; repeated printed endpoints are publication errors.'
FROM rule_rule WHERE rule_code='combat.space.damage-bands';
INSERT INTO src_record_provenance(rule_id,content_package_id,source_locator_id,provenance_class,is_primary_citation)
SELECT r.rule_id,r.content_package_id,l.source_locator_id,CASE w.work_code WHEN 'cepheus-engine.ogn' THEN 'direct' ELSE 'corroborating' END,w.work_code='cepheus-engine.ogn'
FROM rule_rule r JOIN src_locator l ON l.heading_path=CASE r.rule_code WHEN 'combat.space.damage-bands' THEN 'Space Combat > Damage > Space Combat Damage' ELSE 'Space Combat > Damage > Space Combat Hit Location' END
JOIN src_work w USING(source_work_id) WHERE r.rule_code IN('combat.space.damage-bands','combat.space.hit-locations')
 AND w.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1');
