INSERT INTO cmd_command_type VALUES
 ('record_campaign_chronicle','Record durable campaign chronicle knowledge')
ON CONFLICT(command_type) DO NOTHING;
INSERT INTO cmd_domain_event_type VALUES
 ('campaign_chronicle_recorded','Campaign chronicle knowledge recorded')
ON CONFLICT(event_type) DO NOTHING;

CREATE TABLE camp_chronicle_entry(
 chronicle_entry_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
 campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
 entry_kind text NOT NULL CHECK(entry_kind IN('scene','person','place','discovery','promise','decision','relationship','threat','opportunity','other')),
 title text NOT NULL CHECK(btrim(title)<>''),
 summary_text text NOT NULL CHECK(btrim(summary_text)<>''),
 campaign_day bigint NOT NULL,
 importance smallint NOT NULL DEFAULT 3 CHECK(importance BETWEEN 1 AND 5),
 source_kind text NOT NULL CHECK(source_kind IN('desktop_referee','web_referee','human_referee','player_note')),
 ai_memory_enabled boolean NOT NULL DEFAULT true,
 source_command_id bigint NOT NULL UNIQUE REFERENCES cmd_command(command_id),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(chronicle_entry_id,campaign_id)
);
CREATE INDEX camp_chronicle_memory_recent ON camp_chronicle_entry(campaign_id,importance DESC,created_at DESC) WHERE ai_memory_enabled;

CREATE TABLE camp_chronicle_actor(
 chronicle_entry_id bigint NOT NULL,
 campaign_id bigint NOT NULL,
 actor_id bigint NOT NULL,
 PRIMARY KEY(chronicle_entry_id,actor_id),
 FOREIGN KEY(chronicle_entry_id,campaign_id) REFERENCES camp_chronicle_entry(chronicle_entry_id,campaign_id),
 FOREIGN KEY(actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id)
);
CREATE TABLE camp_chronicle_location(
 chronicle_entry_id bigint NOT NULL,
 campaign_id bigint NOT NULL,
 location_id bigint NOT NULL,
 PRIMARY KEY(chronicle_entry_id,location_id),
 FOREIGN KEY(chronicle_entry_id,campaign_id) REFERENCES camp_chronicle_entry(chronicle_entry_id,campaign_id),
 FOREIGN KEY(location_id,campaign_id) REFERENCES loc_location(location_id,campaign_id)
);
CREATE TABLE camp_chronicle_ship(
 chronicle_entry_id bigint NOT NULL,
 campaign_id bigint NOT NULL,
 ship_id bigint NOT NULL,
 PRIMARY KEY(chronicle_entry_id,ship_id),
 FOREIGN KEY(chronicle_entry_id,campaign_id) REFERENCES camp_chronicle_entry(chronicle_entry_id,campaign_id),
 FOREIGN KEY(ship_id,campaign_id) REFERENCES ship_ship(ship_id,campaign_id)
);
CREATE TABLE cmd_campaign_chronicle_receipt(
 command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
 campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
 chronicle_entry_id bigint NOT NULL UNIQUE,
 FOREIGN KEY(chronicle_entry_id,campaign_id) REFERENCES camp_chronicle_entry(chronicle_entry_id,campaign_id)
);
