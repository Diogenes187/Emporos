ALTER TABLE journey_journey
    ADD COLUMN ship_id bigint,
    ADD CONSTRAINT journey_ship_campaign_fkey
        FOREIGN KEY (ship_id,campaign_id)
        REFERENCES ship_ship(ship_id,campaign_id);

CREATE UNIQUE INDEX journey_ship_one_active_journey
    ON journey_journey(ship_id)
    WHERE ship_id IS NOT NULL
      AND journey_status IN ('ready','underway');

CREATE OR REPLACE FUNCTION journey_validate_ship_conveyance()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    ship_item bigint;
    ship_status text;
    ship_location bigint;
    first_origin bigint;
BEGIN
    IF NEW.ship_id IS NULL THEN
        RETURN NEW;
    END IF;

    SELECT inventory_item_instance_id,lifecycle_status,current_location_id
    INTO ship_item,ship_status,ship_location
    FROM ship_ship
    WHERE ship_id=NEW.ship_id AND campaign_id=NEW.campaign_id;

    IF NEW.conveyance_item_instance_id IS NULL THEN
        NEW.conveyance_item_instance_id=ship_item;
    ELSIF NEW.conveyance_item_instance_id<>ship_item THEN
        RAISE EXCEPTION 'Journey conveyance does not identify its ship'
            USING ERRCODE='23514';
    END IF;

    IF NEW.journey_status IN ('ready','underway') THEN
        SELECT origin_location_id INTO first_origin
        FROM journey_leg
        WHERE journey_id=NEW.journey_id AND leg_order=1;
        IF ship_status<>'active' OR ship_location IS DISTINCT FROM first_origin THEN
            RAISE EXCEPTION
                'Active journey requires an active ship at its origin'
                USING ERRCODE='23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER journey_ship_conveyance_valid
BEFORE INSERT OR UPDATE OF ship_id,campaign_id,
    conveyance_item_instance_id,journey_status
ON journey_journey
FOR EACH ROW EXECUTE FUNCTION journey_validate_ship_conveyance();

ALTER TABLE journey_participant
    ADD CONSTRAINT journey_participant_campaign_key
        UNIQUE (journey_participant_id,journey_id,campaign_id);

ALTER TABLE ship_crew_assignment
    ADD CONSTRAINT ship_crew_assignment_campaign_key
        UNIQUE (crew_assignment_id,ship_id,campaign_id);

CREATE TABLE journey_ship_crew_commitment (
    journey_participant_id bigint NOT NULL,
    journey_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    ship_id bigint NOT NULL,
    crew_assignment_id bigint NOT NULL,
    commitment_status text NOT NULL DEFAULT 'assigned' CHECK (
        commitment_status IN (
            'assigned','served','relieved','failed_to_report'
        )
    ),
    committed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    ended_at timestamptz,
    PRIMARY KEY (journey_id,crew_assignment_id),
    FOREIGN KEY (journey_participant_id,journey_id,campaign_id)
        REFERENCES journey_participant(
            journey_participant_id,journey_id,campaign_id
        ),
    FOREIGN KEY (crew_assignment_id,ship_id,campaign_id)
        REFERENCES ship_crew_assignment(
            crew_assignment_id,ship_id,campaign_id
        ),
    FOREIGN KEY (journey_id,campaign_id)
        REFERENCES journey_journey(journey_id,campaign_id),
    CHECK (
        (commitment_status='assigned' AND ended_at IS NULL)
        OR (commitment_status<>'assigned' AND ended_at IS NOT NULL)
    )
);

CREATE OR REPLACE FUNCTION journey_validate_ship_crew_commitment()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    participant_actor bigint;
    assigned_actor bigint;
    journey_ship bigint;
    assignment_status text;
BEGIN
    SELECT actor_id INTO participant_actor
    FROM journey_participant
    WHERE journey_participant_id=NEW.journey_participant_id
      AND journey_id=NEW.journey_id
      AND campaign_id=NEW.campaign_id;
    SELECT actor_id,duty_status INTO assigned_actor,assignment_status
    FROM ship_crew_assignment
    WHERE crew_assignment_id=NEW.crew_assignment_id
      AND ship_id=NEW.ship_id
      AND campaign_id=NEW.campaign_id;
    SELECT ship_id INTO journey_ship
    FROM journey_journey
    WHERE journey_id=NEW.journey_id
      AND campaign_id=NEW.campaign_id;

    IF participant_actor<>assigned_actor
       OR journey_ship<>NEW.ship_id
       OR assignment_status<>'active' THEN
        RAISE EXCEPTION 'Journey crew commitment links are inconsistent'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER journey_ship_crew_commitment_valid
BEFORE INSERT OR UPDATE ON journey_ship_crew_commitment
FOR EACH ROW EXECUTE FUNCTION
    journey_validate_ship_crew_commitment();

CREATE TABLE journey_ship_resource_plan (
    journey_ship_resource_plan_id bigint
        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    journey_leg_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    ship_id bigint NOT NULL,
    resource_type_code text NOT NULL REFERENCES
        ship_resource_type(resource_type_code),
    planned_quantity numeric NOT NULL CHECK (planned_quantity>0),
    reserve_quantity numeric NOT NULL DEFAULT 0 CHECK (
        reserve_quantity>=0
    ),
    plan_status text NOT NULL DEFAULT 'planned' CHECK (
        plan_status IN ('planned','reserved','consumed','released')
    ),
    FOREIGN KEY (journey_leg_id,campaign_id)
        REFERENCES journey_leg(journey_leg_id,campaign_id),
    FOREIGN KEY (ship_id,resource_type_code)
        REFERENCES ship_resource(ship_id,resource_type_code),
    UNIQUE (journey_leg_id,resource_type_code),
    UNIQUE (journey_ship_resource_plan_id,ship_id,campaign_id)
);

CREATE OR REPLACE FUNCTION journey_validate_ship_resource_plan()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    planned_ship bigint;
    available numeric;
BEGIN
    SELECT journey.ship_id INTO planned_ship
    FROM journey_leg leg
    JOIN journey_journey journey
      ON journey.journey_id=leg.journey_id
     AND journey.campaign_id=leg.campaign_id
    WHERE leg.journey_leg_id=NEW.journey_leg_id
      AND leg.campaign_id=NEW.campaign_id;
    SELECT current_quantity INTO available
    FROM ship_resource
    WHERE ship_id=NEW.ship_id
      AND campaign_id=NEW.campaign_id
      AND resource_type_code=NEW.resource_type_code;

    IF planned_ship<>NEW.ship_id
       OR (
           NEW.plan_status='reserved'
           AND available<NEW.planned_quantity+NEW.reserve_quantity
       ) THEN
        RAISE EXCEPTION 'Journey resource plan is inconsistent'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER journey_ship_resource_plan_valid
BEFORE INSERT OR UPDATE ON journey_ship_resource_plan
FOR EACH ROW EXECUTE FUNCTION journey_validate_ship_resource_plan();

ALTER TABLE ship_resource_movement
    ADD CONSTRAINT ship_resource_movement_campaign_key
        UNIQUE (resource_movement_id,ship_id,campaign_id);

CREATE TABLE journey_ship_resource_use (
    journey_ship_resource_plan_id bigint NOT NULL,
    resource_movement_id bigint NOT NULL UNIQUE,
    ship_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    used_quantity numeric NOT NULL CHECK (used_quantity>0),
    PRIMARY KEY (
        journey_ship_resource_plan_id,resource_movement_id
    ),
    FOREIGN KEY (
        journey_ship_resource_plan_id,ship_id,campaign_id
    ) REFERENCES journey_ship_resource_plan(
        journey_ship_resource_plan_id,ship_id,campaign_id
    ),
    FOREIGN KEY (resource_movement_id,ship_id,campaign_id)
        REFERENCES ship_resource_movement(
            resource_movement_id,ship_id,campaign_id
        )
);

CREATE OR REPLACE FUNCTION journey_validate_resource_use()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    movement_delta numeric;
    movement_resource text;
    planned_quantity_value numeric;
    planned_resource text;
    previously_used numeric;
BEGIN
    SELECT quantity_delta,resource_type_code
    INTO movement_delta,movement_resource
    FROM ship_resource_movement
    WHERE resource_movement_id=NEW.resource_movement_id
      AND ship_id=NEW.ship_id
      AND campaign_id=NEW.campaign_id;
    SELECT planned_quantity,resource_type_code
    INTO planned_quantity_value,planned_resource
    FROM journey_ship_resource_plan
    WHERE journey_ship_resource_plan_id=
          NEW.journey_ship_resource_plan_id
      AND ship_id=NEW.ship_id
      AND campaign_id=NEW.campaign_id;
    SELECT coalesce(sum(used_quantity),0)
    INTO previously_used
    FROM journey_ship_resource_use
    WHERE journey_ship_resource_plan_id=
          NEW.journey_ship_resource_plan_id
      AND resource_movement_id<>NEW.resource_movement_id;

    IF movement_resource<>planned_resource
       OR movement_delta<>-NEW.used_quantity
       OR previously_used+NEW.used_quantity>planned_quantity_value THEN
        RAISE EXCEPTION 'Journey resource use is inconsistent'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER journey_ship_resource_use_valid
BEFORE INSERT OR UPDATE ON journey_ship_resource_use
FOR EACH ROW EXECUTE FUNCTION journey_validate_resource_use();

CREATE OR REPLACE FUNCTION journey_validate_passage_participant()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM journey_participant
        WHERE journey_id=NEW.journey_id
          AND campaign_id=NEW.campaign_id
          AND actor_id=NEW.actor_id
          AND participant_role IN ('passenger','prisoner','traveller')
    ) THEN
        RAISE EXCEPTION 'Passage requires a journey participant'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER journey_passage_participant_required
BEFORE INSERT OR UPDATE ON journey_passage
FOR EACH ROW EXECUTE FUNCTION
    journey_validate_passage_participant();
