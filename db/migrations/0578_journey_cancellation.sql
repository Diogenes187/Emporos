INSERT INTO cmd_command_type VALUES ('cancel_jump_journey','Cancel jump journey');
INSERT INTO cmd_domain_event_type VALUES ('jump_journey_cancelled','Jump journey cancelled');

CREATE TABLE cmd_jump_journey_cancellation_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    campaign_id bigint NOT NULL,
    journey_id bigint NOT NULL,
    ship_id bigint NOT NULL,
    previous_journey_status text NOT NULL CHECK (
        previous_journey_status='planning'
    ),
    released_resource_plans smallint NOT NULL CHECK (
        released_resource_plans>=0
    ),
    relieved_crew_commitments smallint NOT NULL CHECK (
        relieved_crew_commitments>=0
    ),
    FOREIGN KEY (journey_id,campaign_id)
        REFERENCES journey_journey(journey_id,campaign_id),
    FOREIGN KEY (ship_id,campaign_id)
        REFERENCES ship_ship(ship_id,campaign_id)
);

COMMENT ON TABLE cmd_jump_journey_cancellation_receipt IS
    'Standing down a drafted jump order before the drive is resolved. '
    'Reservations are released; nothing mechanical is undone because '
    'nothing mechanical had happened yet.';
