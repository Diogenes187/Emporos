INSERT INTO src_locator(source_work_id,source_artifact_id,locator_type,heading_path,display_citation)
SELECT a.source_work_id,a.source_artifact_id,'heading','Social Encounters > '||x.heading,
 CASE w.work_code WHEN 'cepheus-engine.ogn' THEN 'Cepheus Engine SRD, Social Encounters: ' ELSE 'Cepheus Engine v9.1, Social Encounters: ' END||x.heading
FROM src_artifact a JOIN src_work w USING(source_work_id) CROSS JOIN (VALUES('Patron Encounters'),('Random Rumor Content')) x(heading)
WHERE (w.work_code='cepheus-engine.github-v9.1' AND a.source_uri='src/book3/social-encounters.md')
 OR (w.work_code='cepheus-engine.ogn' AND a.source_uri='https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-social-encounters/')
ON CONFLICT DO NOTHING;

WITH p AS(SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine'),d(rule_code,name,description) AS(VALUES
 ('encounter.patron-role-table','Patron Role Table','A D66 roll suggests the role of a potential patron; 66 is Referee choice.'),
 ('encounter.rumor-content-table','Rumor Content Table','A D66 roll suggests the informational content of a rumor; 66 is Referee choice.')
) INSERT INTO rule_rule(content_package_id,rule_code,name,rule_category,rule_status,description)
SELECT p.content_package_id,d.rule_code,d.name,'encounter','approved',d.description FROM p CROSS JOIN d;

CREATE TABLE rule_patron_role_roll(
 d66_result smallint PRIMARY KEY CHECK(d66_result BETWEEN 11 AND 66 AND d66_result/10 BETWEEN 1 AND 6 AND d66_result%10 BETWEEN 1 AND 6),
 role_code text NOT NULL CHECK(btrim(role_code)<>''),role_name text NOT NULL CHECK(btrim(role_name)<>''),referee_choice boolean NOT NULL,
 CHECK(referee_choice=(d66_result=66))
);
INSERT INTO rule_patron_role_roll VALUES
 (11,'agent','Agent',false),(12,'athlete','Athlete',false),(13,'barbarian','Barbarian',false),(14,'belter','Belter',false),(15,'broker','Broker',false),(16,'bureaucrat','Bureaucrat',false),
 (21,'celebrity','Celebrity',false),(22,'colonist','Colonist',false),(23,'con-artist','Con Artist',false),(24,'corporate-executive','Corporate Executive',false),(25,'courier','Courier',false),(26,'diplomat','Diplomat',false),
 (31,'drifter','Drifter',false),(32,'educator','Educator',false),(33,'entertainer','Entertainer',false),(34,'financier','Financier',false),(35,'fugitive','Fugitive',false),(36,'hijacker','Hijacker',false),
 (41,'hunter','Hunter',false),(42,'marine','Marine',false),(43,'mercenary','Mercenary',false),(44,'merchant','Merchant',false),(45,'navy','Navy',false),(46,'noble','Noble',false),
 (51,'physician','Physician',false),(52,'pirate','Pirate',false),(53,'politician','Politician',false),(54,'rogue','Rogue',false),(55,'scientist','Scientist',false),(56,'scout','Scout',false),
 (61,'smuggler','Smuggler',false),(62,'system-defense-officer','System Defense Officer',false),(63,'technician','Technician',false),(64,'terrorist','Terrorist',false),(65,'tourist','Tourist',false),(66,'referee-choice','Referee''s Choice',true);

CREATE TABLE rule_rumor_content_roll(
 d66_result smallint PRIMARY KEY CHECK(d66_result BETWEEN 11 AND 66 AND d66_result/10 BETWEEN 1 AND 6 AND d66_result%10 BETWEEN 1 AND 6),
 content_code text NOT NULL CHECK(btrim(content_code)<>''),content_name text NOT NULL CHECK(btrim(content_name)<>''),referee_choice boolean NOT NULL,
 CHECK(referee_choice=(d66_result=66))
);
INSERT INTO rule_rumor_content_roll VALUES
 (11,'background-information','Background information',false),(12,'background-information','Background information',false),(13,'broad-background-information','Broad background information',false),(14,'broad-background-information','Broad background information',false),(15,'broad-background-information','Broad background information',false),(16,'completely-false-information','Completely false information',false),
 (21,'general-location-data','General location data',false),(22,'general-location-data','General location data',false),(23,'general-location-data','General location data',false),(24,'helpful-data','Helpful data',false),(25,'important-fact','Important fact',false),(26,'information-leading-to-trap','Information leading to trap',false),
 (31,'library-data-reference','Library data reference',false),(32,'library-data-reference-general','Library data reference (general information)',false),(33,'library-data-reference-general','Library data reference (general information)',false),(34,'major-fact','Major fact',false),(35,'major-fact','Major fact',false),(36,'minor-fact','Minor fact',false),
 (41,'minor-fact','Minor fact',false),(42,'misleading-background-data','Misleading background data',false),(43,'misleading-background-data','Misleading background data',false),(44,'misleading-background-information','Misleading background information',false),(45,'misleading-background-information','Misleading background information',false),(46,'misleading-background-information','Misleading background information',false),
 (51,'misleading-clue','Misleading clue',false),(52,'obvious-clue','Obvious clue',false),(53,'partial-potentially-misleading-fact','Partial (potentially misleading) fact',false),(54,'reliable-recommendation-to-action','Reliable recommendation to action',false),(55,'specific-background-data','Specific background data',false),(56,'specific-background-data','Specific background data',false),
 (61,'specific-location-data','Specific location data',false),(62,'specific-location-data','Specific location data',false),(63,'terminology','Terminology',false),(64,'veiled-clue','Veiled clue',false),(65,'veiled-clue','Veiled clue',false),(66,'referee-choice','Referee''s Choice',true);

CREATE TABLE src_patron_role_roll_provenance(d66_result smallint NOT NULL REFERENCES rule_patron_role_roll,source_locator_id bigint NOT NULL REFERENCES src_locator,provenance_class text NOT NULL CHECK(provenance_class IN('direct','corroborating')),is_primary_citation boolean NOT NULL,PRIMARY KEY(d66_result,source_locator_id,provenance_class));
INSERT INTO src_patron_role_roll_provenance SELECT r.d66_result,l.source_locator_id,CASE w.work_code WHEN 'cepheus-engine.ogn' THEN 'direct' ELSE 'corroborating' END,w.work_code='cepheus-engine.ogn' FROM rule_patron_role_roll r CROSS JOIN src_locator l JOIN src_work w USING(source_work_id) WHERE l.heading_path='Social Encounters > Patron Encounters' AND w.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1');
CREATE TABLE src_rumor_content_roll_provenance(d66_result smallint NOT NULL REFERENCES rule_rumor_content_roll,source_locator_id bigint NOT NULL REFERENCES src_locator,provenance_class text NOT NULL CHECK(provenance_class IN('direct','corroborating')),is_primary_citation boolean NOT NULL,PRIMARY KEY(d66_result,source_locator_id,provenance_class));
INSERT INTO src_rumor_content_roll_provenance SELECT r.d66_result,l.source_locator_id,CASE w.work_code WHEN 'cepheus-engine.ogn' THEN 'direct' ELSE 'corroborating' END,w.work_code='cepheus-engine.ogn' FROM rule_rumor_content_roll r CROSS JOIN src_locator l JOIN src_work w USING(source_work_id) WHERE l.heading_path='Social Encounters > Random Rumor Content' AND w.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1');
INSERT INTO src_record_provenance(rule_id,content_package_id,source_locator_id,provenance_class,is_primary_citation)
SELECT r.rule_id,r.content_package_id,l.source_locator_id,CASE w.work_code WHEN 'cepheus-engine.ogn' THEN 'direct' ELSE 'corroborating' END,w.work_code='cepheus-engine.ogn'
FROM rule_rule r JOIN src_locator l ON l.heading_path='Social Encounters > '||CASE r.rule_code WHEN 'encounter.patron-role-table' THEN 'Patron Encounters' ELSE 'Random Rumor Content' END JOIN src_work w USING(source_work_id)
WHERE r.rule_code IN('encounter.patron-role-table','encounter.rumor-content-table') AND w.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1');
