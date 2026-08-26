INSERT INTO cmd_command_type VALUES
 ('record_human_referee_turn','Record human referee narration'),
 ('request_gm_assistance','Request private AI assistance for a human referee')
ON CONFLICT(command_type) DO NOTHING;

INSERT INTO cmd_domain_event_type VALUES
 ('human_referee_turn_recorded','Human referee narration recorded'),
 ('gm_assistance_completed','Private GM assistance completed')
ON CONFLICT(event_type) DO NOTHING;

ALTER TABLE ai_model_invocation DROP CONSTRAINT ai_model_invocation_purpose_code_check;
ALTER TABLE ai_model_invocation ADD CONSTRAINT ai_model_invocation_purpose_code_check CHECK(
 purpose_code IN('source_text_review','source_visual_review','source_intro','referee_narration','gm_assistance'));

CREATE TABLE camp_gm_assistance(
 gm_assistance_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
 campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
 prompt_text text NOT NULL CHECK(btrim(prompt_text)<>''),
 suggestion_text text NOT NULL CHECK(btrim(suggestion_text)<>''),
 model_invocation_id bigint NOT NULL UNIQUE REFERENCES ai_model_invocation(model_invocation_id),
 source_command_id bigint NOT NULL UNIQUE REFERENCES cmd_command(command_id),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE cmd_gm_assistance_receipt(
 command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
 campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
 gm_assistance_id bigint NOT NULL UNIQUE REFERENCES camp_gm_assistance(gm_assistance_id)
);
