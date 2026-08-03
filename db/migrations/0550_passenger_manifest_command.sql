INSERT INTO cmd_command_type VALUES('finalize_passenger_manifest','Finalize passenger manifest');
INSERT INTO cmd_domain_event_type VALUES('passenger_manifest_finalized','Passenger manifest finalized');
CREATE TABLE cmd_passenger_manifest_receipt(
 command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
 journey_id bigint NOT NULL UNIQUE,ship_id bigint NOT NULL,passenger_count integer NOT NULL CHECK(passenger_count>0),
 stateroom_units_used integer NOT NULL CHECK(stateroom_units_used>=0),low_berths_used integer NOT NULL CHECK(low_berths_used>=0),
 steward_level_quanta integer NOT NULL CHECK(steward_level_quanta>=0),steward_quanta_required integer NOT NULL CHECK(steward_quanta_required>=0),
 FOREIGN KEY(journey_id,campaign_id) REFERENCES journey_journey(journey_id,campaign_id),FOREIGN KEY(ship_id,campaign_id) REFERENCES ship_ship(ship_id,campaign_id)
);
