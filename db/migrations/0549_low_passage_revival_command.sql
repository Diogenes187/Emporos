INSERT INTO cmd_command_type VALUES('revive_low_passenger','Revive low-passage passenger');
INSERT INTO cmd_domain_event_type VALUES('low_passenger_revival_resolved','Low passenger revival resolved');
CREATE TABLE cmd_low_passage_revival_receipt(
 command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
 journey_passage_id bigint NOT NULL UNIQUE,passenger_actor_id bigint NOT NULL,passenger_task_command_id bigint NOT NULL UNIQUE,
 passenger_succeeded boolean NOT NULL,passage_status_after text NOT NULL CHECK(passage_status_after IN('completed','failed_revival')),
 FOREIGN KEY(journey_passage_id,campaign_id) REFERENCES journey_passage(journey_passage_id,campaign_id),
 FOREIGN KEY(passenger_actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id),
 FOREIGN KEY(passenger_task_command_id) REFERENCES cmd_actor_task_receipt(command_id),
 CHECK(passenger_succeeded=(passage_status_after='completed'))
);
