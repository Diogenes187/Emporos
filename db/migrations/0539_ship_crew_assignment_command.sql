INSERT INTO cmd_command_type VALUES('assign_ship_crew','Assign ship crew');
INSERT INTO cmd_domain_event_type VALUES('ship_crew_assigned','Ship crew assigned');
CREATE TABLE cmd_ship_crew_assignment_receipt(
 command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
 actor_id bigint NOT NULL,ship_id bigint NOT NULL,ship_crew_position_id bigint NOT NULL,
 crew_assignment_id bigint NOT NULL UNIQUE REFERENCES ship_crew_assignment(crew_assignment_id),
 FOREIGN KEY(actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id),
 FOREIGN KEY(ship_crew_position_id,ship_id,campaign_id) REFERENCES ship_crew_position(ship_crew_position_id,ship_id,campaign_id)
);
