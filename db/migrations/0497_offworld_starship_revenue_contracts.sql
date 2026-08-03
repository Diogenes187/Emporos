CREATE TABLE ship_cargo_reservation (
    cargo_reservation_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    ship_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    journey_id bigint NOT NULL,
    reservation_kind text NOT NULL CHECK (reservation_kind IN ('bulk-freight','postal-duty')),
    reserved_tons numeric NOT NULL CHECK (reserved_tons>0),
    reservation_status text NOT NULL DEFAULT 'reserved'
        CHECK (reservation_status IN ('reserved','fulfilled','cancelled')),
    concurrency_version bigint NOT NULL DEFAULT 1 CHECK (concurrency_version>0),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    ended_at timestamptz,
    FOREIGN KEY (ship_id,campaign_id) REFERENCES ship_ship(ship_id,campaign_id),
    FOREIGN KEY (journey_id,campaign_id) REFERENCES journey_journey(journey_id,campaign_id),
    UNIQUE (cargo_reservation_id,ship_id,campaign_id),
    CHECK ((reservation_status='reserved')=(ended_at IS NULL))
);

CREATE FUNCTION ship_validate_revenue_cargo_capacity()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE capacity numeric; loaded numeric; reserved numeric;
BEGIN
    PERFORM 1 FROM ship_ship
    WHERE ship_id=NEW.ship_id AND campaign_id=NEW.campaign_id FOR UPDATE;
    SELECT class.cargo_capacity_tons INTO STRICT capacity
    FROM ship_ship ship JOIN ship_class class USING (ship_class_rule_id)
    WHERE ship.ship_id=NEW.ship_id AND ship.campaign_id=NEW.campaign_id;
    SELECT coalesce(sum(current_quantity_tons),0) INTO loaded
    FROM ship_cargo_lot WHERE ship_id=NEW.ship_id AND custody_status='aboard';
    SELECT coalesce(sum(reserved_tons),0) INTO reserved
    FROM ship_cargo_reservation
    WHERE ship_id=NEW.ship_id AND reservation_status='reserved'
      AND cargo_reservation_id<>coalesce(NEW.cargo_reservation_id,0);
    IF NEW.reservation_status='reserved' THEN reserved:=reserved+NEW.reserved_tons; END IF;
    IF loaded+reserved>capacity THEN
        RAISE EXCEPTION 'Cargo plus revenue reservations exceeds authoritative hold capacity' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER ship_revenue_cargo_capacity_valid
BEFORE INSERT OR UPDATE ON ship_cargo_reservation
FOR EACH ROW EXECUTE FUNCTION ship_validate_revenue_cargo_capacity();

CREATE OR REPLACE FUNCTION ship_validate_cargo_capacity()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE capacity numeric; loaded numeric; reserved numeric;
BEGIN
    PERFORM 1 FROM ship_ship
    WHERE ship_id=NEW.ship_id AND campaign_id=NEW.campaign_id FOR UPDATE;
    SELECT class.cargo_capacity_tons INTO STRICT capacity
    FROM ship_ship ship JOIN ship_class class USING(ship_class_rule_id)
    WHERE ship.ship_id=NEW.ship_id AND ship.campaign_id=NEW.campaign_id;
    SELECT coalesce(sum(current_quantity_tons),0) INTO loaded
    FROM ship_cargo_lot
    WHERE ship_id=NEW.ship_id AND custody_status='aboard'
      AND ship_cargo_lot_id<>coalesce(NEW.ship_cargo_lot_id,0);
    IF NEW.custody_status='aboard' THEN loaded:=loaded+NEW.current_quantity_tons; END IF;
    SELECT coalesce(sum(reserved_tons),0) INTO reserved
    FROM ship_cargo_reservation
    WHERE ship_id=NEW.ship_id AND reservation_status='reserved';
    IF loaded+reserved>capacity THEN
        RAISE EXCEPTION 'Ship cargo plus reservations exceeds authoritative hold capacity' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;

CREATE TABLE journey_freight_contract (
    freight_contract_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    campaign_id bigint NOT NULL,
    revenue_availability_cycle_id bigint NOT NULL,
    journey_id bigint NOT NULL,
    journey_leg_id bigint NOT NULL,
    ship_id bigint NOT NULL,
    cargo_reservation_id bigint NOT NULL UNIQUE,
    accepted_tons numeric NOT NULL CHECK (accepted_tons>0),
    payment_per_ton_credits integer NOT NULL CHECK (payment_per_ton_credits=1000),
    promised_payment_credits bigint NOT NULL CHECK (promised_payment_credits>0),
    accepted_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    source_command_id bigint REFERENCES cmd_command(command_id),
    FOREIGN KEY (revenue_availability_cycle_id,campaign_id)
        REFERENCES journey_revenue_availability_cycle(revenue_availability_cycle_id,campaign_id),
    FOREIGN KEY (journey_id,campaign_id) REFERENCES journey_journey(journey_id,campaign_id),
    FOREIGN KEY (journey_leg_id,campaign_id) REFERENCES journey_leg(journey_leg_id,campaign_id),
    FOREIGN KEY (ship_id,campaign_id) REFERENCES ship_ship(ship_id,campaign_id),
    FOREIGN KEY (cargo_reservation_id,ship_id,campaign_id)
        REFERENCES ship_cargo_reservation(cargo_reservation_id,ship_id,campaign_id),
    UNIQUE (freight_contract_id,campaign_id),
    CHECK (promised_payment_credits=accepted_tons*payment_per_ton_credits)
);

CREATE FUNCTION journey_validate_freight_contract()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE cycle journey_revenue_availability_cycle%ROWTYPE; leg journey_leg%ROWTYPE;
        journey_ship bigint; reservation ship_cargo_reservation%ROWTYPE;
        available integer; already_accepted numeric; published_rate integer;
BEGIN
    SELECT * INTO STRICT cycle FROM journey_revenue_availability_cycle
    WHERE revenue_availability_cycle_id=NEW.revenue_availability_cycle_id
      AND campaign_id=NEW.campaign_id FOR UPDATE;
    IF cycle.cycle_status<>'finalized' THEN
        RAISE EXCEPTION 'Freight requires finalized simultaneous availability' USING ERRCODE='23514';
    END IF;
    SELECT * INTO STRICT leg FROM journey_leg
    WHERE journey_leg_id=NEW.journey_leg_id AND campaign_id=NEW.campaign_id;
    SELECT ship_id INTO STRICT journey_ship FROM journey_journey
    WHERE journey_id=NEW.journey_id AND campaign_id=NEW.campaign_id;
    SELECT * INTO STRICT reservation FROM ship_cargo_reservation
    WHERE cargo_reservation_id=NEW.cargo_reservation_id FOR UPDATE;
    SELECT available_quantity INTO STRICT available
    FROM journey_revenue_availability_draw
    WHERE revenue_availability_cycle_id=NEW.revenue_availability_cycle_id
      AND traffic_kind='freight_tons';
    SELECT coalesce(sum(accepted_tons),0) INTO already_accepted
    FROM journey_freight_contract
    WHERE revenue_availability_cycle_id=NEW.revenue_availability_cycle_id
      AND freight_contract_id<>coalesce(NEW.freight_contract_id,0);
    SELECT freight_payment_per_ton_credits INTO STRICT published_rate
    FROM rule_ship_revenue_system;
    IF leg.journey_id<>NEW.journey_id OR leg.origin_location_id<>cycle.origin_location_id
       OR leg.destination_location_id<>cycle.destination_location_id
       OR journey_ship<>NEW.ship_id OR reservation.ship_id<>NEW.ship_id
       OR reservation.campaign_id<>NEW.campaign_id OR reservation.journey_id<>NEW.journey_id
       OR reservation.reservation_kind<>'bulk-freight' OR reservation.reservation_status<>'reserved'
       OR reservation.reserved_tons<>NEW.accepted_tons
       OR already_accepted+NEW.accepted_tons>available
       OR NEW.payment_per_ton_credits<>published_rate THEN
        RAISE EXCEPTION 'Freight contract does not match availability, journey, ship, reservation, or published rate' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER journey_freight_contract_valid
BEFORE INSERT OR UPDATE ON journey_freight_contract
FOR EACH ROW EXECUTE FUNCTION journey_validate_freight_contract();

CREATE TABLE journey_freight_delivery_receipt (
    freight_contract_id bigint PRIMARY KEY,
    campaign_id bigint NOT NULL,
    delivered_location_id bigint NOT NULL,
    delivered_tons numeric NOT NULL CHECK (delivered_tons>0),
    paid_credits bigint NOT NULL CHECK (paid_credits>0),
    financial_transaction_id bigint NOT NULL UNIQUE,
    delivered_day bigint NOT NULL,
    delivered_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    source_command_id bigint REFERENCES cmd_command(command_id),
    FOREIGN KEY (freight_contract_id,campaign_id)
        REFERENCES journey_freight_contract(freight_contract_id,campaign_id),
    FOREIGN KEY (delivered_location_id,campaign_id)
        REFERENCES loc_location(location_id,campaign_id),
    FOREIGN KEY (financial_transaction_id,campaign_id)
        REFERENCES fin_transaction(transaction_id,campaign_id)
);

CREATE TABLE journey_freight_cancellation_receipt (
    freight_contract_id bigint PRIMARY KEY,
    campaign_id bigint NOT NULL,
    cancellation_reason text NOT NULL CHECK (btrim(cancellation_reason)<>''),
    cancelled_day bigint NOT NULL,
    cancelled_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    source_command_id bigint REFERENCES cmd_command(command_id),
    FOREIGN KEY (freight_contract_id,campaign_id)
        REFERENCES journey_freight_contract(freight_contract_id,campaign_id)
);

CREATE FUNCTION journey_validate_freight_closure()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE contract journey_freight_contract%ROWTYPE; destination bigint; tx_status text;
BEGIN
    SELECT * INTO STRICT contract FROM journey_freight_contract
    WHERE freight_contract_id=NEW.freight_contract_id AND campaign_id=NEW.campaign_id FOR UPDATE;
    IF TG_TABLE_NAME='journey_freight_delivery_receipt' THEN
        IF EXISTS (SELECT 1 FROM journey_freight_cancellation_receipt WHERE freight_contract_id=NEW.freight_contract_id) THEN
            RAISE EXCEPTION 'Cancelled freight cannot be delivered' USING ERRCODE='23514';
        END IF;
        SELECT destination_location_id INTO STRICT destination FROM journey_leg
        WHERE journey_leg_id=contract.journey_leg_id;
        SELECT transaction_status INTO STRICT tx_status FROM fin_transaction
        WHERE transaction_id=NEW.financial_transaction_id AND campaign_id=NEW.campaign_id;
        IF NEW.delivered_location_id<>destination OR NEW.delivered_tons<>contract.accepted_tons
           OR NEW.paid_credits<>contract.promised_payment_credits OR tx_status<>'posted' THEN
            RAISE EXCEPTION 'Freight delivery does not match its destination, quantity, payment, or posted transaction' USING ERRCODE='23514';
        END IF;
        UPDATE ship_cargo_reservation SET reservation_status='fulfilled',ended_at=clock_timestamp(),
            concurrency_version=concurrency_version+1
        WHERE cargo_reservation_id=contract.cargo_reservation_id;
    ELSE
        IF EXISTS (SELECT 1 FROM journey_freight_delivery_receipt WHERE freight_contract_id=NEW.freight_contract_id) THEN
            RAISE EXCEPTION 'Delivered freight cannot be cancelled' USING ERRCODE='23514';
        END IF;
        UPDATE ship_cargo_reservation SET reservation_status='cancelled',ended_at=clock_timestamp(),
            concurrency_version=concurrency_version+1
        WHERE cargo_reservation_id=contract.cargo_reservation_id;
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER journey_freight_delivery_valid
BEFORE INSERT ON journey_freight_delivery_receipt
FOR EACH ROW EXECUTE FUNCTION journey_validate_freight_closure();
CREATE TRIGGER journey_freight_cancellation_valid
BEFORE INSERT ON journey_freight_cancellation_receipt
FOR EACH ROW EXECUTE FUNCTION journey_validate_freight_closure();

ALTER TABLE journey_passage ADD CONSTRAINT journey_passage_campaign_journey_key
    UNIQUE (journey_passage_id,campaign_id,journey_id);

CREATE TABLE journey_passage_availability_receipt (
    journey_passage_id bigint PRIMARY KEY,
    campaign_id bigint NOT NULL,
    journey_id bigint NOT NULL,
    journey_leg_id bigint NOT NULL,
    revenue_availability_cycle_id bigint NOT NULL,
    traffic_kind text NOT NULL CHECK (traffic_kind IN ('high_passengers','middle_passengers','low_passengers')),
    accepted_ordinal integer NOT NULL CHECK (accepted_ordinal>0),
    accepted_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    source_command_id bigint REFERENCES cmd_command(command_id),
    FOREIGN KEY (journey_passage_id,campaign_id,journey_id)
        REFERENCES journey_passage(journey_passage_id,campaign_id,journey_id),
    FOREIGN KEY (journey_leg_id,campaign_id) REFERENCES journey_leg(journey_leg_id,campaign_id),
    FOREIGN KEY (revenue_availability_cycle_id,campaign_id)
        REFERENCES journey_revenue_availability_cycle(revenue_availability_cycle_id,campaign_id),
    UNIQUE (revenue_availability_cycle_id,traffic_kind,accepted_ordinal)
);

CREATE FUNCTION journey_validate_passage_availability()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE cycle journey_revenue_availability_cycle%ROWTYPE; leg journey_leg%ROWTYPE;
        passage_class text; available integer; accepted integer; expected_kind text;
BEGIN
    SELECT * INTO STRICT cycle FROM journey_revenue_availability_cycle
    WHERE revenue_availability_cycle_id=NEW.revenue_availability_cycle_id
      AND campaign_id=NEW.campaign_id FOR UPDATE;
    SELECT * INTO STRICT leg FROM journey_leg
    WHERE journey_leg_id=NEW.journey_leg_id AND campaign_id=NEW.campaign_id;
    SELECT passage.passage_class INTO STRICT passage_class FROM journey_passage passage
    WHERE journey_passage_id=NEW.journey_passage_id AND campaign_id=NEW.campaign_id
      AND journey_id=NEW.journey_id;
    expected_kind:=CASE passage_class WHEN 'high' THEN 'high_passengers'
        WHEN 'middle' THEN 'middle_passengers' WHEN 'low' THEN 'low_passengers' END;
    SELECT available_quantity INTO STRICT available FROM journey_revenue_availability_draw
    WHERE revenue_availability_cycle_id=NEW.revenue_availability_cycle_id
      AND traffic_kind=NEW.traffic_kind;
    SELECT count(*) INTO accepted FROM journey_passage_availability_receipt
    WHERE revenue_availability_cycle_id=NEW.revenue_availability_cycle_id
      AND traffic_kind=NEW.traffic_kind
      AND journey_passage_id<>NEW.journey_passage_id;
    IF cycle.cycle_status<>'finalized' OR leg.journey_id<>NEW.journey_id
       OR leg.origin_location_id<>cycle.origin_location_id
       OR leg.destination_location_id<>cycle.destination_location_id
       OR expected_kind IS NULL OR NEW.traffic_kind<>expected_kind
       OR accepted>=available OR NEW.accepted_ordinal<>accepted+1 THEN
        RAISE EXCEPTION 'Passage acceptance does not match simultaneous availability or journey route' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER journey_passage_availability_valid
BEFORE INSERT OR UPDATE ON journey_passage_availability_receipt
FOR EACH ROW EXECUTE FUNCTION journey_validate_passage_availability();

CREATE FUNCTION journey_guard_cargo_reservation()
RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
    IF NEW.ship_id<>OLD.ship_id OR NEW.campaign_id<>OLD.campaign_id
       OR NEW.journey_id<>OLD.journey_id OR NEW.reservation_kind<>OLD.reservation_kind
       OR NEW.reserved_tons<>OLD.reserved_tons
       OR OLD.reservation_status<>'reserved' OR NEW.reservation_status='reserved'
       OR NEW.concurrency_version<>OLD.concurrency_version+1 THEN
        RAISE EXCEPTION 'Cargo reservation permits only one versioned terminal transition' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER ship_cargo_reservation_state_guard
BEFORE UPDATE ON ship_cargo_reservation
FOR EACH ROW EXECUTE FUNCTION journey_guard_cargo_reservation();

CREATE FUNCTION journey_reject_revenue_contract_receipt_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
    RAISE EXCEPTION 'Starship revenue contracts and receipts are immutable';
END $$;

CREATE TRIGGER journey_freight_contract_immutable
BEFORE UPDATE OR DELETE ON journey_freight_contract
FOR EACH ROW EXECUTE FUNCTION journey_reject_revenue_contract_receipt_mutation();
CREATE TRIGGER journey_freight_delivery_immutable
BEFORE UPDATE OR DELETE ON journey_freight_delivery_receipt
FOR EACH ROW EXECUTE FUNCTION journey_reject_revenue_contract_receipt_mutation();
CREATE TRIGGER journey_freight_cancellation_immutable
BEFORE UPDATE OR DELETE ON journey_freight_cancellation_receipt
FOR EACH ROW EXECUTE FUNCTION journey_reject_revenue_contract_receipt_mutation();
CREATE TRIGGER journey_passage_availability_immutable
BEFORE UPDATE OR DELETE ON journey_passage_availability_receipt
FOR EACH ROW EXECUTE FUNCTION journey_reject_revenue_contract_receipt_mutation();
