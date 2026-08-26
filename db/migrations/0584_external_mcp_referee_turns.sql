INSERT INTO cmd_command_type VALUES
 ('submit_external_referee_turn','Queue player action for external MCP referee'),
 ('complete_external_referee_turn','Record external MCP referee narration')
ON CONFLICT(command_type) DO NOTHING;

INSERT INTO cmd_domain_event_type VALUES
 ('external_referee_turn_submitted','Player action queued for external MCP referee'),
 ('external_referee_turn_completed','External MCP referee narration recorded')
ON CONFLICT(event_type) DO NOTHING;

CREATE TABLE cmd_external_referee_completion_receipt(
 command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
 campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
 referee_turn_id bigint NOT NULL UNIQUE REFERENCES camp_referee_turn(referee_turn_id)
);
