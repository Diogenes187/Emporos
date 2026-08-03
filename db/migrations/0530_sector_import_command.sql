INSERT INTO cmd_command_type VALUES ('import_sector','Import sector');
INSERT INTO cmd_domain_event_type VALUES ('sector_imported','Sector imported');

WITH package AS (SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine')
INSERT INTO rule_rule(content_package_id,rule_code,name,rule_category,rule_status,description)
SELECT content_package_id,code,name,'world','approved',description FROM package CROSS JOIN (VALUES
 ('location.type.sector','Sector','A 32 by 40 hex region of charted space.'),
 ('location.type.star-system','Star System','A mapped stellar system occupying a sector hex.'),
 ('location.type.main-world','Main World','The principal profiled world of a mapped system.')
) entry(code,name,description);

INSERT INTO rule_location_type(location_type_rule_id,location_type_code,permits_containment,permits_actor_position)
SELECT rule_id,replace(rule_code,'location.type.',''),true,
       rule_code IN ('location.type.star-system','location.type.main-world')
  FROM rule_rule WHERE rule_code LIKE 'location.type.%';

INSERT INTO src_record_provenance(rule_id,content_package_id,source_locator_id,provenance_class,is_primary_citation)
SELECT rule.rule_id,rule.content_package_id,locator.source_locator_id,
       CASE work.work_code WHEN 'cepheus-engine.ogn' THEN 'direct' ELSE 'corroborating' END,
       work.work_code='cepheus-engine.ogn'
  FROM rule_rule rule
  JOIN src_locator locator ON locator.heading_path='Worlds > Star Mapping'
  JOIN src_work work USING(source_work_id)
 WHERE rule.rule_code LIKE 'location.type.%'
   AND work.work_code IN ('cepheus-engine.ogn','cepheus-engine.github-v9.1')
ON CONFLICT DO NOTHING;

CREATE TABLE cmd_sector_import_receipt(
 command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
 campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
 sector_location_id bigint NOT NULL,
 source_filename text NOT NULL CHECK(btrim(source_filename)<>''),
 source_sha256 text NOT NULL CHECK(source_sha256~'^[0-9a-f]{64}$'),
 source_byte_count bigint NOT NULL CHECK(source_byte_count>0),
 imported_system_count smallint NOT NULL CHECK(imported_system_count>0),
 FOREIGN KEY(sector_location_id,campaign_id) REFERENCES loc_sector(location_id,campaign_id)
);

CREATE TABLE cmd_sector_import_system(
 command_id bigint NOT NULL REFERENCES cmd_sector_import_receipt(command_id),
 row_order smallint NOT NULL CHECK(row_order>0),
 system_location_id bigint NOT NULL,
 world_location_id bigint NOT NULL,
 source_line_number integer NOT NULL CHECK(source_line_number>0),
 source_hex text NOT NULL CHECK(source_hex~'^[0-9]{4}$'),
 source_uwp text NOT NULL CHECK(source_uwp~'^[A-HX][0-9A-Z]{6}-[0-9A-Z]$'),
 PRIMARY KEY(command_id,row_order),
 UNIQUE(command_id,system_location_id),
 FOREIGN KEY(system_location_id) REFERENCES loc_star_system(location_id),
 FOREIGN KEY(world_location_id) REFERENCES loc_celestial_body(location_id)
);
