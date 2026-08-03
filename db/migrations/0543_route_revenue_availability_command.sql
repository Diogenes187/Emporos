INSERT INTO cmd_command_type VALUES('open_route_revenue','Open route revenue availability');
INSERT INTO cmd_domain_event_type VALUES('route_revenue_opened','Route revenue opened');
CREATE TABLE cmd_route_revenue_availability_receipt(
 command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
 ship_id bigint NOT NULL,revenue_availability_cycle_id bigint NOT NULL UNIQUE,origin_system_location_id bigint NOT NULL,destination_system_location_id bigint NOT NULL,
 FOREIGN KEY(ship_id,campaign_id) REFERENCES ship_ship(ship_id,campaign_id),
 FOREIGN KEY(revenue_availability_cycle_id,campaign_id) REFERENCES journey_revenue_availability_cycle(revenue_availability_cycle_id,campaign_id),
 FOREIGN KEY(origin_system_location_id,campaign_id) REFERENCES loc_location(location_id,campaign_id),
 FOREIGN KEY(destination_system_location_id,campaign_id) REFERENCES loc_location(location_id,campaign_id)
);
