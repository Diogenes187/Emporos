CREATE TABLE journey_journey (
    journey_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    journey_kind text NOT NULL CHECK (
        journey_kind IN (
            'interplanetary','jump','multi_leg','commercial','other'
        )
    ),
    name text NOT NULL CHECK (btrim(name)<>''),
    conveyance_item_instance_id bigint,
    journey_status text NOT NULL DEFAULT 'planning' CHECK (
        journey_status IN (
            'planning','ready','underway','completed',
            'cancelled','failed'
        )
    ),
    current_leg_order smallint CHECK (current_leg_order>0),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    started_at timestamptz,
    ended_at timestamptz,
    source_command_id bigint REFERENCES cmd_command(command_id),
    concurrency_version bigint NOT NULL DEFAULT 1 CHECK (
        concurrency_version>0
    ),
    UNIQUE (journey_id,campaign_id),
    FOREIGN KEY (conveyance_item_instance_id,campaign_id)
        REFERENCES inv_item_instance(item_instance_id,campaign_id),
    CHECK (
        (journey_status IN ('planning','ready') AND started_at IS NULL
         AND ended_at IS NULL)
        OR (journey_status='underway' AND started_at IS NOT NULL
            AND ended_at IS NULL)
        OR (journey_status IN ('completed','cancelled','failed')
            AND ended_at IS NOT NULL)
    )
);

CREATE TABLE journey_leg (
    journey_leg_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    journey_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    leg_order smallint NOT NULL CHECK (leg_order>0),
    origin_location_id bigint NOT NULL,
    destination_location_id bigint NOT NULL,
    travel_mode text NOT NULL CHECK (
        travel_mode IN (
            'surface','interplanetary','jump','docking','other'
        )
    ),
    distance_value numeric CHECK (distance_value>0),
    distance_unit text CHECK (
        distance_unit IS NULL OR distance_unit IN (
            'kilometre','astronomical_unit','parsec'
        )
    ),
    planned_duration_seconds bigint CHECK (
        planned_duration_seconds>0
    ),
    leg_status text NOT NULL DEFAULT 'planned' CHECK (
        leg_status IN (
            'planned','committed','underway','completed',
            'skipped','failed'
        )
    ),
    started_at timestamptz,
    ended_at timestamptz,
    FOREIGN KEY (journey_id,campaign_id)
        REFERENCES journey_journey(journey_id,campaign_id),
    FOREIGN KEY (origin_location_id,campaign_id)
        REFERENCES loc_location(location_id,campaign_id),
    FOREIGN KEY (destination_location_id,campaign_id)
        REFERENCES loc_location(location_id,campaign_id),
    UNIQUE (journey_id,leg_order),
    UNIQUE (journey_leg_id,campaign_id),
    CHECK (origin_location_id<>destination_location_id),
    CHECK (
        (distance_value IS NULL)=(distance_unit IS NULL)
    ),
    CHECK (
        (leg_status IN ('planned','committed')
         AND started_at IS NULL AND ended_at IS NULL)
        OR (leg_status='underway' AND started_at IS NOT NULL
            AND ended_at IS NULL)
        OR (leg_status IN ('completed','skipped','failed')
            AND ended_at IS NOT NULL)
    )
);

CREATE OR REPLACE FUNCTION journey_validate_leg_continuity()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    previous_destination bigint;
BEGIN
    IF NEW.leg_order>1 THEN
        SELECT destination_location_id INTO previous_destination
        FROM journey_leg
        WHERE journey_id=NEW.journey_id
          AND leg_order=NEW.leg_order-1;
        IF previous_destination IS NULL
           OR previous_destination<>NEW.origin_location_id THEN
            RAISE EXCEPTION
                'Journey leg origin must continue from previous destination'
                USING ERRCODE='23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER journey_leg_continuity
BEFORE INSERT OR UPDATE OF leg_order,origin_location_id
ON journey_leg
FOR EACH ROW EXECUTE FUNCTION journey_validate_leg_continuity();

CREATE TABLE journey_participant (
    journey_participant_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    journey_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    actor_id bigint NOT NULL,
    participant_role text NOT NULL CHECK (
        participant_role IN (
            'traveller','crew','passenger','escort','prisoner','other'
        )
    ),
    commitment_status text NOT NULL DEFAULT 'committed' CHECK (
        commitment_status IN ('planned','committed','released','completed')
    ),
    committed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    released_at timestamptz,
    FOREIGN KEY (journey_id,campaign_id)
        REFERENCES journey_journey(journey_id,campaign_id),
    FOREIGN KEY (actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    UNIQUE (journey_id,actor_id),
    CHECK (
        (commitment_status IN ('planned','committed')
         AND released_at IS NULL)
        OR (commitment_status IN ('released','completed')
            AND released_at IS NOT NULL)
    )
);

CREATE OR REPLACE FUNCTION journey_reject_actor_double_commitment()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM 1 FROM actor_actor
    WHERE actor_id=NEW.actor_id FOR UPDATE;
    IF NEW.commitment_status='committed' AND EXISTS (
        SELECT 1
        FROM journey_participant participant
        JOIN journey_journey journey
          ON journey.journey_id=participant.journey_id
        WHERE participant.actor_id=NEW.actor_id
          AND participant.journey_participant_id IS DISTINCT FROM
              NEW.journey_participant_id
          AND participant.commitment_status='committed'
          AND journey.journey_status IN ('ready','underway')
    ) THEN
        RAISE EXCEPTION 'Actor is committed to another active journey'
            USING ERRCODE='23505';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER journey_actor_one_active_commitment
BEFORE INSERT OR UPDATE ON journey_participant
FOR EACH ROW EXECUTE FUNCTION
    journey_reject_actor_double_commitment();

CREATE TABLE journey_item_commitment (
    journey_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    item_instance_id bigint NOT NULL,
    commitment_purpose text NOT NULL CHECK (
        commitment_purpose IN (
            'conveyance','cargo','equipment','mail','supplies','other'
        )
    ),
    released_at timestamptz,
    PRIMARY KEY (journey_id,item_instance_id),
    FOREIGN KEY (journey_id,campaign_id)
        REFERENCES journey_journey(journey_id,campaign_id),
    FOREIGN KEY (item_instance_id,campaign_id)
        REFERENCES inv_item_instance(item_instance_id,campaign_id)
);

CREATE TABLE journey_lot_commitment (
    journey_lot_commitment_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    journey_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    lot_id bigint NOT NULL,
    quantity bigint NOT NULL CHECK (quantity>0),
    commitment_purpose text NOT NULL CHECK (
        commitment_purpose IN ('cargo','mail','supplies','fuel','other')
    ),
    released_at timestamptz,
    FOREIGN KEY (journey_id,campaign_id)
        REFERENCES journey_journey(journey_id,campaign_id),
    FOREIGN KEY (lot_id,campaign_id)
        REFERENCES inv_lot(lot_id,campaign_id),
    UNIQUE (journey_id,lot_id,commitment_purpose)
);

CREATE TABLE journey_progress (
    journey_progress_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    journey_id bigint NOT NULL,
    journey_leg_id bigint,
    campaign_id bigint NOT NULL,
    progress_order integer NOT NULL CHECK (progress_order>0),
    progress_kind text NOT NULL CHECK (
        progress_kind IN (
            'departed','distance','arrived','delayed',
            'diverted','encounter','status'
        )
    ),
    distance_completed numeric CHECK (distance_completed>=0),
    elapsed_seconds bigint CHECK (elapsed_seconds>=0),
    location_id bigint,
    command_id bigint REFERENCES cmd_command(command_id),
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    FOREIGN KEY (journey_id,campaign_id)
        REFERENCES journey_journey(journey_id,campaign_id),
    FOREIGN KEY (journey_leg_id,campaign_id)
        REFERENCES journey_leg(journey_leg_id,campaign_id),
    FOREIGN KEY (location_id,campaign_id)
        REFERENCES loc_location(location_id,campaign_id),
    UNIQUE (journey_id,progress_order)
);

CREATE TABLE journey_jump_attempt (
    jump_attempt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    journey_leg_id bigint NOT NULL UNIQUE,
    campaign_id bigint NOT NULL,
    jump_system_code text NOT NULL REFERENCES
        rule_jump_travel_system(jump_system_code),
    jump_number smallint NOT NULL CHECK (jump_number>0),
    plotted_distance_parsecs numeric NOT NULL CHECK (
        plotted_distance_parsecs>0
    ),
    plot_age_months integer NOT NULL DEFAULT 0 CHECK (
        plot_age_months>=0
    ),
    engineering_effect smallint NOT NULL,
    drive_hits smallint NOT NULL DEFAULT 0 CHECK (drive_hits>=0),
    fuel_type_code text NOT NULL REFERENCES
        rule_fuel_type(fuel_type_code),
    within_safe_limit boolean NOT NULL,
    natural_roll smallint NOT NULL CHECK (natural_roll BETWEEN 2 AND 12),
    modifier_total smallint NOT NULL,
    final_result smallint NOT NULL,
    jump_outcome text NOT NULL CHECK (
        jump_outcome IN ('accurate','inaccurate','misjump')
    ),
    duration_hours smallint NOT NULL CHECK (duration_hours>0),
    emergence_distance_parsecs numeric,
    command_id bigint REFERENCES cmd_command(command_id),
    FOREIGN KEY (journey_leg_id,campaign_id)
        REFERENCES journey_leg(journey_leg_id,campaign_id),
    CHECK (plotted_distance_parsecs<=jump_number),
    CHECK (
        (jump_outcome='misjump' AND emergence_distance_parsecs IS NOT NULL)
        OR (jump_outcome<>'misjump'
            AND emergence_distance_parsecs IS NULL)
    )
);

CREATE TABLE journey_refuel_operation (
    refuel_operation_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    journey_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    location_id bigint NOT NULL,
    fuel_type_code text NOT NULL REFERENCES
        rule_fuel_type(fuel_type_code),
    fuel_source text NOT NULL CHECK (
        fuel_source IN ('starport','water','gas_giant','processor','other')
    ),
    tons_acquired numeric NOT NULL CHECK (tons_acquired>0),
    elapsed_seconds bigint NOT NULL CHECK (elapsed_seconds>=0),
    cost_minor bigint NOT NULL CHECK (cost_minor>=0),
    financial_transaction_id bigint,
    command_id bigint REFERENCES cmd_command(command_id),
    occurred_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    FOREIGN KEY (journey_id,campaign_id)
        REFERENCES journey_journey(journey_id,campaign_id),
    FOREIGN KEY (location_id,campaign_id)
        REFERENCES loc_location(location_id,campaign_id),
    FOREIGN KEY (financial_transaction_id,campaign_id)
        REFERENCES fin_transaction(transaction_id,campaign_id),
    CHECK (
        (cost_minor=0 AND financial_transaction_id IS NULL)
        OR (cost_minor>0 AND financial_transaction_id IS NOT NULL)
    )
);

CREATE TABLE journey_passage (
    journey_passage_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    journey_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    actor_id bigint NOT NULL,
    passage_class text NOT NULL REFERENCES
        rule_passage_class(passage_class),
    fare_minor bigint NOT NULL CHECK (fare_minor>=0),
    baggage_mass_kg integer CHECK (baggage_mass_kg>=0),
    passage_status text NOT NULL DEFAULT 'booked' CHECK (
        passage_status IN (
            'booked','boarded','completed','cancelled','failed_revival'
        )
    ),
    financial_transaction_id bigint,
    FOREIGN KEY (journey_id,campaign_id)
        REFERENCES journey_journey(journey_id,campaign_id),
    FOREIGN KEY (actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    FOREIGN KEY (financial_transaction_id,campaign_id)
        REFERENCES fin_transaction(transaction_id,campaign_id),
    UNIQUE (journey_id,actor_id)
);

CREATE OR REPLACE FUNCTION journey_completed_leg_immutable()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF OLD.leg_status='completed' AND NEW IS DISTINCT FROM OLD THEN
        RAISE EXCEPTION 'Completed journey legs are immutable'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER journey_leg_completed_immutable
BEFORE UPDATE ON journey_leg
FOR EACH ROW EXECUTE FUNCTION journey_completed_leg_immutable();
