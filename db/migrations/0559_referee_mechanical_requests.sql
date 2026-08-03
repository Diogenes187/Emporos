INSERT INTO cmd_command_type VALUES('confirm_referee_tool_request','Confirm an AI-proposed allowlisted engine action');
INSERT INTO cmd_domain_event_type VALUES('referee_tool_request_confirmed','AI-proposed engine action confirmed');

CREATE TABLE camp_referee_tool_request(
 referee_tool_request_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
 referee_turn_id bigint NOT NULL UNIQUE REFERENCES camp_referee_turn(referee_turn_id),
 campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
 tool_name text NOT NULL CHECK(tool_name~'^[a-z][a-z0-9_]*$'),
 request_summary text NOT NULL CHECK(btrim(request_summary)<>''),
 request_status text NOT NULL CHECK(request_status IN('proposed','executed','rejected','failed')),
 executed_command_id bigint REFERENCES cmd_command(command_id),
 failure_code text,
 proposed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 decided_at timestamptz,
 CHECK((request_status='proposed' AND decided_at IS NULL AND executed_command_id IS NULL) OR (request_status<>'proposed' AND decided_at IS NOT NULL))
);
CREATE TABLE camp_referee_tool_argument(
 referee_tool_request_id bigint NOT NULL REFERENCES camp_referee_tool_request(referee_tool_request_id),
 argument_name text NOT NULL CHECK(argument_name~'^[a-z][a-z0-9_]*$'),
 argument_value text NOT NULL,
 value_kind text NOT NULL CHECK(value_kind IN('string','integer','number','boolean','null')),
 argument_order smallint NOT NULL CHECK(argument_order>0),
 PRIMARY KEY(referee_tool_request_id,argument_name),
 UNIQUE(referee_tool_request_id,argument_order)
);
CREATE TABLE cmd_referee_tool_confirmation_receipt(
 command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
 campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
 referee_tool_request_id bigint NOT NULL UNIQUE REFERENCES camp_referee_tool_request(referee_tool_request_id),
 gameplay_command_id bigint NOT NULL UNIQUE REFERENCES cmd_command(command_id)
);
