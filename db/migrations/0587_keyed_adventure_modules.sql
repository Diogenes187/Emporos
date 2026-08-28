INSERT INTO cmd_command_type VALUES
 ('create_adventure_module','Create a keyed campaign adventure'),
 ('key_adventure_location','Add a keyed adventure location'),
 ('enter_adventure_location','Enter a keyed adventure location'),
 ('update_adventure_location_state','Update current keyed-location state'),
 ('advance_adventure_exploration','Advance the adventure exploration clock')
ON CONFLICT(command_type) DO NOTHING;
INSERT INTO cmd_domain_event_type VALUES
 ('adventure_module_created','Adventure module created'),
 ('adventure_location_keyed','Adventure location keyed'),
 ('adventure_location_entered','Adventure location entered'),
 ('adventure_location_state_updated','Adventure location state updated'),
 ('adventure_exploration_advanced','Adventure exploration advanced')
ON CONFLICT(event_type) DO NOTHING;

CREATE TABLE camp_adventure_module(
 adventure_module_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
 campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
 source_document_id bigint,
 name text NOT NULL CHECK(btrim(name)<>''),
 module_status text NOT NULL DEFAULT 'active' CHECK(module_status IN('draft','active','completed','archived')),
 current_location_id bigint,
 turn_minutes integer NOT NULL DEFAULT 10 CHECK(turn_minutes>0),
 elapsed_turns bigint NOT NULL DEFAULT 0 CHECK(elapsed_turns>=0),
 turns_since_rest integer NOT NULL DEFAULT 0 CHECK(turns_since_rest>=0),
 wander_frequency integer NOT NULL DEFAULT 6 CHECK(wander_frequency>0),
 turns_since_wander integer NOT NULL DEFAULT 0 CHECK(turns_since_wander>=0),
 global_alert smallint NOT NULL DEFAULT 0 CHECK(global_alert BETWEEN 0 AND 5),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 source_command_id bigint NOT NULL REFERENCES cmd_command(command_id),
 UNIQUE(adventure_module_id,campaign_id),
 FOREIGN KEY(source_document_id,campaign_id) REFERENCES camp_source_document(source_document_id,campaign_id)
);
CREATE UNIQUE INDEX camp_one_active_adventure_module ON camp_adventure_module(campaign_id) WHERE module_status='active';

CREATE TABLE camp_adventure_location(
 adventure_location_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
 adventure_module_id bigint NOT NULL,
 campaign_id bigint NOT NULL,
 location_key text NOT NULL CHECK(btrim(location_key)<>''),
 name text NOT NULL CHECK(btrim(name)<>''),
 keyed_description text NOT NULL CHECK(btrim(keyed_description)<>''),
 source_page_number integer,
 occupants_initial text,
 treasure_initial text,
 occupant_status text NOT NULL DEFAULT 'as_keyed' CHECK(occupant_status IN('as_keyed','absent','fled','dead','captured','allied','changed')),
 treasure_status text NOT NULL DEFAULT 'as_keyed' CHECK(treasure_status IN('as_keyed','untouched','taken','moved','destroyed','changed')),
 alert_status text NOT NULL DEFAULT 'unaware' CHECK(alert_status IN('unaware','suspicious','alerted','secured')),
 discovered boolean NOT NULL DEFAULT false,
 current_note text,
 entered_count integer NOT NULL DEFAULT 0 CHECK(entered_count>=0),
 last_entered_at timestamptz,
 source_command_id bigint NOT NULL REFERENCES cmd_command(command_id),
 UNIQUE(adventure_module_id,location_key),
 UNIQUE(adventure_location_id,campaign_id),
 FOREIGN KEY(adventure_module_id,campaign_id) REFERENCES camp_adventure_module(adventure_module_id,campaign_id),
 CHECK(source_page_number IS NULL OR source_page_number>0)
);
ALTER TABLE camp_adventure_module ADD CONSTRAINT camp_adventure_current_location_fk FOREIGN KEY(current_location_id,campaign_id) REFERENCES camp_adventure_location(adventure_location_id,campaign_id);

CREATE TABLE camp_adventure_location_connection(
 adventure_module_id bigint NOT NULL REFERENCES camp_adventure_module(adventure_module_id),
 from_location_id bigint NOT NULL REFERENCES camp_adventure_location(adventure_location_id),
 to_location_id bigint NOT NULL REFERENCES camp_adventure_location(adventure_location_id),
 connection_kind text NOT NULL DEFAULT 'passage' CHECK(connection_kind IN('passage','door','locked_door','hatch','lift','route','portal','other')),
 connection_note text,
 PRIMARY KEY(adventure_module_id,from_location_id,to_location_id),
 CHECK(from_location_id<>to_location_id)
);
CREATE TABLE camp_adventure_light_source(
 adventure_light_source_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 adventure_module_id bigint NOT NULL REFERENCES camp_adventure_module(adventure_module_id),
 name text NOT NULL CHECK(btrim(name)<>''),
 turns_remaining integer NOT NULL CHECK(turns_remaining>=0),
 active boolean NOT NULL DEFAULT true
);
CREATE TABLE camp_adventure_exploration_event(
 adventure_exploration_event_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 adventure_module_id bigint NOT NULL REFERENCES camp_adventure_module(adventure_module_id),
 campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
 event_order bigint NOT NULL,
 event_kind text NOT NULL CHECK(event_kind IN('location_entered','state_changed','turn_advanced','rest','wander_check','light_expired','note')),
 event_text text NOT NULL CHECK(btrim(event_text)<>''),
 elapsed_turns bigint NOT NULL CHECK(elapsed_turns>=0),
 source_command_id bigint NOT NULL REFERENCES cmd_command(command_id),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(adventure_module_id,event_order)
);
CREATE TABLE cmd_adventure_module_receipt(command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),adventure_module_id bigint NOT NULL REFERENCES camp_adventure_module(adventure_module_id),adventure_location_id bigint REFERENCES camp_adventure_location(adventure_location_id),result_code text NOT NULL CHECK(btrim(result_code)<>''));

CREATE VIEW camp_adventure_location_contradiction AS
SELECT location.adventure_location_id,location.public_id,location.adventure_module_id,location.campaign_id,
 trim(both ' ' from concat_ws(' ',
  CASE WHEN location.occupants_initial IS NOT NULL AND location.occupant_status<>'as_keyed' THEN 'The keyed occupants are now '||upper(location.occupant_status)||'. Do not describe them as originally present.' END,
  CASE WHEN location.treasure_initial IS NOT NULL AND location.treasure_status NOT IN('as_keyed','untouched') THEN 'The keyed valuables are now '||upper(location.treasure_status)||'. Do not restore them.' END,
  CASE WHEN location.alert_status<>'unaware' THEN 'This location is '||upper(location.alert_status)||'. Do not describe its original unaware state.' END,
  CASE WHEN location.current_note IS NOT NULL THEN 'Current state: '||location.current_note END
 )) AS warning_text
FROM camp_adventure_location location;
