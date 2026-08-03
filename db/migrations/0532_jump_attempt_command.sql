INSERT INTO cmd_command_type VALUES ('resolve_jump_attempt','Resolve jump attempt');
INSERT INTO cmd_domain_event_type VALUES ('jump_attempt_resolved','Jump attempt resolved');
INSERT INTO cmd_random_draw_group VALUES ('jump_duration','Jump duration');

ALTER TABLE journey_jump_attempt ADD COLUMN engineering_task_command_id bigint UNIQUE REFERENCES cmd_actor_task_receipt(command_id);

CREATE TABLE cmd_jump_attempt_receipt(
 command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
 campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
 journey_id bigint NOT NULL,
 journey_leg_id bigint NOT NULL UNIQUE,
 jump_attempt_id bigint NOT NULL UNIQUE REFERENCES journey_jump_attempt(jump_attempt_id),
 engineer_actor_id bigint NOT NULL,
 engineering_task_command_id bigint NOT NULL UNIQUE REFERENCES cmd_actor_task_receipt(command_id),
 navigation_solution_id bigint NOT NULL UNIQUE REFERENCES journey_navigation_solution(navigation_solution_id),
 natural_roll smallint NOT NULL CHECK(natural_roll BETWEEN 2 AND 12),
 modifier_total smallint NOT NULL,
 final_result smallint NOT NULL,
 jump_outcome text NOT NULL CHECK(jump_outcome IN('accurate','inaccurate','misjump')),
 duration_hours smallint NOT NULL CHECK(duration_hours>0),
 FOREIGN KEY(journey_id,campaign_id) REFERENCES journey_journey(journey_id,campaign_id),
 FOREIGN KEY(journey_leg_id,campaign_id) REFERENCES journey_leg(journey_leg_id,campaign_id),
 FOREIGN KEY(engineer_actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id)
);
