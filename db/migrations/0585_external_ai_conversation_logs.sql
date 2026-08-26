INSERT INTO cmd_command_type VALUES
 ('append_external_conversation_entry','Append desktop AI conversation log entry')
ON CONFLICT(command_type) DO NOTHING;
INSERT INTO cmd_domain_event_type VALUES
 ('external_conversation_entry_appended','Desktop AI conversation entry appended')
ON CONFLICT(event_type) DO NOTHING;

CREATE TABLE camp_external_conversation_log(
 external_conversation_log_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
 campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
 log_reference text NOT NULL CHECK(btrim(log_reference)<>''),
 title text NOT NULL CHECK(btrim(title)<>''),
 client_name text NOT NULL CHECK(btrim(client_name)<>''),
 opened_day bigint NOT NULL,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(campaign_id,log_reference),
 UNIQUE(external_conversation_log_id,campaign_id)
);

CREATE TABLE camp_external_conversation_entry(
 external_conversation_entry_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
 external_conversation_log_id bigint NOT NULL,
 campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
 entry_order integer NOT NULL CHECK(entry_order>0),
 speaker_kind text NOT NULL CHECK(speaker_kind IN('user','assistant','system','tool')),
 message_text text NOT NULL CHECK(btrim(message_text)<>''),
 campaign_day bigint NOT NULL,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(external_conversation_log_id,entry_order),
 FOREIGN KEY(external_conversation_log_id,campaign_id)
   REFERENCES camp_external_conversation_log(external_conversation_log_id,campaign_id)
);

CREATE TABLE cmd_external_conversation_entry_receipt(
 command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
 campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
 external_conversation_log_id bigint NOT NULL REFERENCES camp_external_conversation_log(external_conversation_log_id),
 external_conversation_entry_id bigint NOT NULL UNIQUE REFERENCES camp_external_conversation_entry(external_conversation_entry_id)
);
