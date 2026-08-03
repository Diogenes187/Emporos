INSERT INTO cmd_command_type VALUES('submit_referee_turn','Submit player action to AI referee');
INSERT INTO cmd_domain_event_type VALUES('referee_turn_completed','AI referee turn completed');

CREATE TABLE camp_referee_turn(
 referee_turn_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
 campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
 campaign_day bigint NOT NULL,
 turn_status text NOT NULL CHECK(turn_status IN('pending','completed','failed')),
 failure_code text,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 completed_at timestamptz,
 source_command_id bigint NOT NULL UNIQUE REFERENCES cmd_command(command_id),
 CHECK((turn_status='pending' AND completed_at IS NULL) OR (turn_status<>'pending' AND completed_at IS NOT NULL))
);
CREATE TABLE camp_referee_message(
 referee_message_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 referee_turn_id bigint NOT NULL REFERENCES camp_referee_turn(referee_turn_id),
 campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
 message_order smallint NOT NULL CHECK(message_order IN(1,2)),
 speaker_kind text NOT NULL CHECK(speaker_kind IN('player','referee')),
 message_text text NOT NULL CHECK(btrim(message_text)<>''),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(referee_turn_id,message_order),
 UNIQUE(referee_turn_id,speaker_kind)
);
CREATE TABLE camp_referee_source_context(
 referee_turn_id bigint NOT NULL REFERENCES camp_referee_turn(referee_turn_id),
 source_document_id bigint NOT NULL,
 page_number integer NOT NULL,
 context_order smallint NOT NULL CHECK(context_order>0),
 PRIMARY KEY(referee_turn_id,context_order),
 UNIQUE(referee_turn_id,source_document_id,page_number),
 FOREIGN KEY(source_document_id,page_number) REFERENCES camp_source_page(source_document_id,page_number)
);
CREATE TABLE cmd_referee_turn_receipt(
 command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
 campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
 referee_turn_id bigint NOT NULL UNIQUE REFERENCES camp_referee_turn(referee_turn_id)
);
