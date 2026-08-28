INSERT INTO cmd_command_type VALUES
 ('begin_adventure_indexing','Begin complete source indexing'),
 ('read_adventure_source_page','Account for an adventure source page'),
 ('propose_adventure_location','Propose a source-grounded keyed location'),
 ('review_adventure_location_proposal','Approve or reject a keyed-location proposal')
ON CONFLICT(command_type) DO NOTHING;
INSERT INTO cmd_domain_event_type VALUES
 ('adventure_indexing_begun','Adventure indexing begun'),
 ('adventure_source_page_read','Adventure source page read'),
 ('adventure_location_proposed','Adventure location proposed'),
 ('adventure_location_proposal_reviewed','Adventure location proposal reviewed')
ON CONFLICT(event_type) DO NOTHING;

CREATE TABLE camp_adventure_index_session(
 adventure_index_session_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
 adventure_module_id bigint NOT NULL,
 campaign_id bigint NOT NULL,
 source_document_id bigint NOT NULL,
 indexing_status text NOT NULL DEFAULT 'reading' CHECK(indexing_status IN('reading','ready_for_proposals','under_review','complete')),
 started_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 source_command_id bigint NOT NULL REFERENCES cmd_command(command_id),
 UNIQUE(adventure_module_id),UNIQUE(adventure_index_session_id,campaign_id),
 FOREIGN KEY(adventure_module_id,campaign_id) REFERENCES camp_adventure_module(adventure_module_id,campaign_id),
 FOREIGN KEY(source_document_id,campaign_id) REFERENCES camp_source_document(source_document_id,campaign_id)
);
CREATE TABLE camp_adventure_index_page(
 adventure_index_session_id bigint NOT NULL REFERENCES camp_adventure_index_session(adventure_index_session_id),
 source_document_id bigint NOT NULL,
 page_number integer NOT NULL,
 page_status text NOT NULL DEFAULT 'pending' CHECK(page_status IN('pending','read')),
 read_command_id bigint REFERENCES cmd_command(command_id),
 read_at timestamptz,
 PRIMARY KEY(adventure_index_session_id,page_number),
 FOREIGN KEY(source_document_id,page_number) REFERENCES camp_source_page(source_document_id,page_number)
);
CREATE TABLE camp_adventure_location_proposal(
 adventure_location_proposal_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
 adventure_index_session_id bigint NOT NULL REFERENCES camp_adventure_index_session(adventure_index_session_id),
 campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
 source_document_id bigint NOT NULL,
 source_page_number integer NOT NULL,
 location_key text NOT NULL CHECK(btrim(location_key)<>''),
 name text NOT NULL CHECK(btrim(name)<>''),
 keyed_description text NOT NULL CHECK(btrim(keyed_description)<>''),
 source_excerpt text NOT NULL CHECK(btrim(source_excerpt)<>''),
 occupants_initial text,
 treasure_initial text,
 proposal_status text NOT NULL DEFAULT 'pending' CHECK(proposal_status IN('pending','approved','rejected')),
 review_note text,
 proposed_command_id bigint NOT NULL REFERENCES cmd_command(command_id),
 reviewed_command_id bigint REFERENCES cmd_command(command_id),
 approved_location_id bigint REFERENCES camp_adventure_location(adventure_location_id),
 proposed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 reviewed_at timestamptz,
 UNIQUE(adventure_index_session_id,location_key),
 FOREIGN KEY(source_document_id,source_page_number) REFERENCES camp_source_page(source_document_id,page_number)
);
CREATE TABLE cmd_adventure_indexing_receipt(command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),adventure_index_session_id bigint NOT NULL REFERENCES camp_adventure_index_session(adventure_index_session_id),source_page_number integer,adventure_location_proposal_id bigint REFERENCES camp_adventure_location_proposal(adventure_location_proposal_id),result_code text NOT NULL CHECK(btrim(result_code)<>''));
