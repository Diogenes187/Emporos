INSERT INTO cmd_command_type(command_type,description) VALUES
 ('initialize_campaign_setting','Initialize campaign setting')
ON CONFLICT (command_type) DO NOTHING;

INSERT INTO cmd_domain_event_type(event_type,description) VALUES
 ('campaign_setting_initialized','Campaign setting initialized')
ON CONFLICT (event_type) DO NOTHING;

CREATE TABLE setting_package (
 setting_package_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 content_package_id bigint NOT NULL UNIQUE REFERENCES sys_content_package(content_package_id),
 setting_code text NOT NULL,
 setting_version text NOT NULL,
 setting_name text NOT NULL CHECK (btrim(setting_name)<>''),
 provenance_class text NOT NULL CHECK (provenance_class IN ('emporos_original','user_supplied','generated_original','unknown')),
 rights_class text NOT NULL CHECK (rights_class IN ('emporos_original','private_non_exportable','unknown_rights')),
 export_permitted boolean NOT NULL DEFAULT false,
 UNIQUE(setting_code,setting_version)
);

CREATE TABLE setting_sector_template (
 setting_sector_template_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 setting_package_id bigint NOT NULL REFERENCES setting_package(setting_package_id),
 sector_code text NOT NULL,
 sector_name text NOT NULL CHECK (btrim(sector_name)<>''),
 sector_x integer NOT NULL DEFAULT 0,
 sector_y integer NOT NULL DEFAULT 0,
 UNIQUE(setting_package_id,sector_code)
);

CREATE TABLE setting_system_template (
 setting_sector_template_id bigint NOT NULL REFERENCES setting_sector_template(setting_sector_template_id),
 row_order smallint NOT NULL CHECK(row_order>0),
 system_name text NOT NULL CHECK(btrim(system_name)<>''),
 hex_code text NOT NULL CHECK(hex_code~'^[0-9]{4}$'),
 uwp text NOT NULL CHECK(uwp~'^[A-HX][0-9A-Z]{6}-[0-9A-Z]$'),
 PRIMARY KEY(setting_sector_template_id,row_order),
 UNIQUE(setting_sector_template_id,hex_code)
);

CREATE TABLE camp_campaign_setting (
 campaign_id bigint PRIMARY KEY REFERENCES camp_campaign(campaign_id),
 startup_choice text NOT NULL CHECK(startup_choice IN ('ledger_reach','generate_original','import_own','uncharted')),
 setting_package_id bigint REFERENCES setting_package(setting_package_id),
 sector_location_id bigint REFERENCES loc_location(location_id),
 provenance_class text NOT NULL CHECK(provenance_class IN ('emporos_original','user_supplied','generated_original','unknown')),
 rights_class text NOT NULL CHECK(rights_class IN ('emporos_original','private_non_exportable','unknown_rights')),
 export_permitted boolean NOT NULL DEFAULT false,
 initialized_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE cmd_campaign_setting_receipt (
 command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
 campaign_id bigint NOT NULL UNIQUE REFERENCES camp_campaign(campaign_id),
 startup_choice text NOT NULL,
 setting_package_id bigint REFERENCES setting_package(setting_package_id),
 sector_import_command_id bigint REFERENCES cmd_sector_import_receipt(command_id)
);

ALTER TABLE cmd_sector_import_receipt
 ADD COLUMN provenance_class text NOT NULL DEFAULT 'user_supplied'
  CHECK(provenance_class IN ('emporos_original','user_supplied','generated_original','unknown')),
 ADD COLUMN rights_class text NOT NULL DEFAULT 'private_non_exportable'
  CHECK(rights_class IN ('emporos_original','private_non_exportable','unknown_rights')),
 ADD COLUMN export_permitted boolean NOT NULL DEFAULT false,
 ADD COLUMN setting_package_id bigint REFERENCES setting_package(setting_package_id);

WITH package AS (
 INSERT INTO sys_content_package(package_code,package_version,display_name,package_kind,lifecycle_status,content_sha256,released_at,notes)
 VALUES('emporos.setting.ledger-reach','1.0.0','Ledger Reach','setting','released',
        'a05e19d2163f79c130526042bbd92e4c88e2c9747cf783728be8d746e3ae7675',clock_timestamp(),
        'Original Emporos setting data; safe to bundle with clean installations.')
 ON CONFLICT(package_code,package_version) DO UPDATE SET display_name=EXCLUDED.display_name
 RETURNING content_package_id
), chosen AS (
 SELECT content_package_id FROM package
 UNION ALL
 SELECT content_package_id FROM sys_content_package WHERE package_code='emporos.setting.ledger-reach' AND package_version='1.0.0'
 LIMIT 1
), setting AS (
 INSERT INTO setting_package(content_package_id,setting_code,setting_version,setting_name,provenance_class,rights_class,export_permitted)
 SELECT content_package_id,'ledger-reach','1.0.0','Ledger Reach','emporos_original','emporos_original',true FROM chosen
 ON CONFLICT(setting_code,setting_version) DO UPDATE SET setting_name=EXCLUDED.setting_name
 RETURNING setting_package_id
), selected_setting AS (
 SELECT setting_package_id FROM setting
 UNION ALL
 SELECT setting_package_id FROM setting_package WHERE setting_code='ledger-reach' AND setting_version='1.0.0'
 LIMIT 1
), sector AS (
 INSERT INTO setting_sector_template(setting_package_id,sector_code,sector_name,sector_x,sector_y)
 SELECT setting_package_id,'ledger-reach','Ledger Reach',0,0 FROM selected_setting
 ON CONFLICT(setting_package_id,sector_code) DO UPDATE SET sector_name=EXCLUDED.sector_name
 RETURNING setting_sector_template_id
), selected_sector AS (
 SELECT setting_sector_template_id FROM sector
 UNION ALL
 SELECT t.setting_sector_template_id FROM setting_sector_template t JOIN selected_setting s USING(setting_package_id) WHERE t.sector_code='ledger-reach'
 LIMIT 1
)
INSERT INTO setting_system_template(setting_sector_template_id,row_order,system_name,hex_code,uwp)
SELECT setting_sector_template_id,v.row_order,v.system_name,v.hex_code,v.uwp
FROM selected_sector CROSS JOIN (VALUES
 (1::smallint,'Ledger''s Rest','0101','A788899-C'),
 (2::smallint,'Orison','0201','B766765-A'),
 (3::smallint,'Kestrel','0302','C553654-8')
) v(row_order,system_name,hex_code,uwp)
ON CONFLICT(setting_sector_template_id,row_order) DO UPDATE
 SET system_name=EXCLUDED.system_name,hex_code=EXCLUDED.hex_code,uwp=EXCLUDED.uwp;
