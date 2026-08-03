INSERT INTO cmd_command_type VALUES('ingest_campaign_source','Ingest campaign source');
INSERT INTO cmd_domain_event_type VALUES('campaign_source_ingested','Campaign source ingested');
CREATE TABLE camp_source_document(
 source_document_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
 campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),title text NOT NULL CHECK(btrim(title)<>''),source_kind text NOT NULL CHECK(source_kind IN('adventure','sourcebook','handout','notes')),
 original_filename text NOT NULL CHECK(btrim(original_filename)<>''),media_type text NOT NULL CHECK(media_type IN('application/pdf','text/plain')),
 content_sha256 text NOT NULL CHECK(content_sha256~'^[0-9a-f]{64}$'),byte_count bigint NOT NULL CHECK(byte_count>0),page_count integer NOT NULL CHECK(page_count>0),
 ingestion_status text NOT NULL CHECK(ingestion_status IN('ready','needs_review','failed')),stored_relative_path text NOT NULL CHECK(btrim(stored_relative_path)<>''),uploaded_at timestamptz NOT NULL DEFAULT clock_timestamp(),source_command_id bigint NOT NULL REFERENCES cmd_command(command_id),
 UNIQUE(campaign_id,content_sha256),UNIQUE(source_document_id,campaign_id)
);
CREATE TABLE camp_source_page(
 source_document_id bigint NOT NULL,campaign_id bigint NOT NULL,page_number integer NOT NULL CHECK(page_number>0),text_content text NOT NULL,
 text_sha256 text NOT NULL CHECK(text_sha256~'^[0-9a-f]{64}$'),character_count integer NOT NULL CHECK(character_count>=0),
 extraction_status text NOT NULL CHECK(extraction_status IN('extracted','empty','failed')),visual_review_required boolean NOT NULL,
 review_status text NOT NULL DEFAULT 'pending' CHECK(review_status IN('pending','verified','rejected')),search_document tsvector GENERATED ALWAYS AS(to_tsvector('english',text_content)) STORED,
 PRIMARY KEY(source_document_id,page_number),FOREIGN KEY(source_document_id,campaign_id) REFERENCES camp_source_document(source_document_id,campaign_id)
);
CREATE INDEX camp_source_page_search ON camp_source_page USING gin(search_document);
CREATE TABLE cmd_campaign_source_ingestion_receipt(command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),source_document_id bigint NOT NULL UNIQUE,page_count integer NOT NULL CHECK(page_count>0),extracted_page_count integer NOT NULL CHECK(extracted_page_count>=0),review_page_count integer NOT NULL CHECK(review_page_count>=0),ingestion_status text NOT NULL CHECK(ingestion_status IN('ready','needs_review','failed')),FOREIGN KEY(source_document_id,campaign_id) REFERENCES camp_source_document(source_document_id,campaign_id));
