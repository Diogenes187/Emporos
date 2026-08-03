INSERT INTO cmd_command_type VALUES
 ('place_ship','Place ship'),('plan_jump_journey','Plan jump journey');
INSERT INTO cmd_domain_event_type VALUES
 ('ship_placed','Ship placed'),('jump_journey_planned','Jump journey planned');

CREATE TABLE cmd_ship_placement_receipt(
 command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
 campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
 ship_id bigint NOT NULL,
 system_location_id bigint NOT NULL,
 previous_location_id bigint,
 ship_version_before bigint NOT NULL CHECK(ship_version_before>0),
 ship_version_after bigint NOT NULL CHECK(ship_version_after=ship_version_before+1),
 FOREIGN KEY(ship_id,campaign_id) REFERENCES ship_ship(ship_id,campaign_id),
 FOREIGN KEY(system_location_id,campaign_id) REFERENCES loc_star_system(location_id,campaign_id),
 FOREIGN KEY(previous_location_id,campaign_id) REFERENCES loc_location(location_id,campaign_id)
);

CREATE TABLE cmd_jump_journey_planning_receipt(
 command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
 campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
 journey_id bigint NOT NULL UNIQUE,
 journey_leg_id bigint NOT NULL UNIQUE,
 ship_id bigint NOT NULL,
 origin_location_id bigint NOT NULL,
 destination_location_id bigint NOT NULL,
 distance_parsecs smallint NOT NULL CHECK(distance_parsecs>0),
 jump_number smallint NOT NULL CHECK(jump_number>=distance_parsecs),
 fuel_quantity numeric NOT NULL CHECK(fuel_quantity>0),
 crew_count smallint NOT NULL CHECK(crew_count>=0),
 FOREIGN KEY(journey_id,campaign_id) REFERENCES journey_journey(journey_id,campaign_id),
 FOREIGN KEY(journey_leg_id,campaign_id) REFERENCES journey_leg(journey_leg_id,campaign_id),
 FOREIGN KEY(ship_id,campaign_id) REFERENCES ship_ship(ship_id,campaign_id),
 FOREIGN KEY(origin_location_id,campaign_id) REFERENCES loc_star_system(location_id,campaign_id),
 FOREIGN KEY(destination_location_id,campaign_id) REFERENCES loc_star_system(location_id,campaign_id)
);
