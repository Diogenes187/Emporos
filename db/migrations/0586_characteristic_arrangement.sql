INSERT INTO cmd_command_type VALUES
 ('arrange_characteristics','Arrange initial characteristic rolls')
ON CONFLICT(command_type) DO NOTHING;
INSERT INTO cmd_domain_event_type VALUES
 ('characteristics_arranged','Initial characteristic rolls arranged')
ON CONFLICT(event_type) DO NOTHING;

CREATE TABLE cmd_characteristic_arrangement_receipt(
 command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
 actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
 actor_version_before bigint NOT NULL CHECK(actor_version_before>0),
 actor_version_after bigint NOT NULL CHECK(actor_version_after=actor_version_before+1)
);
CREATE TABLE cmd_characteristic_arrangement_score(
 command_id bigint NOT NULL REFERENCES cmd_characteristic_arrangement_receipt(command_id),
 target_characteristic_rule_id bigint NOT NULL REFERENCES rule_characteristic(rule_id),
 source_characteristic_rule_id bigint NOT NULL REFERENCES rule_characteristic(rule_id),
 display_order smallint NOT NULL CHECK(display_order>0),
 prior_score smallint NOT NULL CHECK(prior_score>=0),
 resulting_score smallint NOT NULL CHECK(resulting_score>=0),
 PRIMARY KEY(command_id,target_characteristic_rule_id),
 UNIQUE(command_id,source_characteristic_rule_id),
 UNIQUE(command_id,display_order)
);
