INSERT INTO cmd_command_type VALUES('add_campaign_note','Add campaign note'),('archive_play_session','Archive play session');
INSERT INTO cmd_domain_event_type VALUES('campaign_note_added','Campaign note added'),('play_session_archived','Play session archived');

CREATE TABLE camp_journal_note(
 journal_note_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
 campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),title text NOT NULL CHECK(btrim(title)<>''),
 note_kind text NOT NULL CHECK(note_kind IN('player','referee','world','plot','rules','other')),
 note_text text NOT NULL CHECK(btrim(note_text)<>''),ai_memory_enabled boolean NOT NULL DEFAULT true,
 source_command_id bigint NOT NULL UNIQUE REFERENCES cmd_command(command_id),created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 search_document tsvector GENERATED ALWAYS AS(to_tsvector('english',title||' '||note_text)) STORED,
 UNIQUE(journal_note_id,campaign_id)
);
CREATE INDEX camp_journal_note_search ON camp_journal_note USING gin(search_document);

CREATE TABLE camp_session_archive(
 session_archive_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
 campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),title text NOT NULL CHECK(btrim(title)<>''),
 campaign_day bigint NOT NULL,transcript_text text NOT NULL CHECK(btrim(transcript_text)<>''),
 ai_memory_enabled boolean NOT NULL DEFAULT true,source_command_id bigint NOT NULL UNIQUE REFERENCES cmd_command(command_id),
 archived_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 search_document tsvector GENERATED ALWAYS AS(to_tsvector('english',title||' '||transcript_text)) STORED,
 UNIQUE(session_archive_id,campaign_id)
);
CREATE INDEX camp_session_archive_search ON camp_session_archive USING gin(search_document);

CREATE TABLE cmd_campaign_note_receipt(command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),journal_note_id bigint NOT NULL UNIQUE,FOREIGN KEY(journal_note_id,campaign_id) REFERENCES camp_journal_note(journal_note_id,campaign_id));
CREATE TABLE cmd_session_archive_receipt(command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),session_archive_id bigint NOT NULL UNIQUE,FOREIGN KEY(session_archive_id,campaign_id) REFERENCES camp_session_archive(session_archive_id,campaign_id));
