CREATE TABLE journey_postal_contract (
    postal_contract_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    campaign_id bigint NOT NULL,
    journey_id bigint NOT NULL,
    journey_leg_id bigint NOT NULL,
    ship_id bigint NOT NULL,
    cargo_reservation_id bigint NOT NULL UNIQUE,
    gunner_crew_assignment_id bigint NOT NULL,
    actual_mail_natural_roll smallint NOT NULL CHECK (actual_mail_natural_roll BETWEEN 1 AND 6),
    actual_mail_tons smallint NOT NULL CHECK (actual_mail_tons BETWEEN 0 AND 5),
    reserved_mail_tons smallint NOT NULL CHECK (reserved_mail_tons=5),
    promised_payment_credits integer NOT NULL CHECK (promised_payment_credits=25000),
    accepted_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    source_command_id bigint REFERENCES cmd_command(command_id),
    FOREIGN KEY (journey_id,campaign_id) REFERENCES journey_journey(journey_id,campaign_id),
    FOREIGN KEY (journey_leg_id,campaign_id) REFERENCES journey_leg(journey_leg_id,campaign_id),
    FOREIGN KEY (ship_id,campaign_id) REFERENCES ship_ship(ship_id,campaign_id),
    FOREIGN KEY (cargo_reservation_id,ship_id,campaign_id)
        REFERENCES ship_cargo_reservation(cargo_reservation_id,ship_id,campaign_id),
    FOREIGN KEY (gunner_crew_assignment_id,ship_id,campaign_id)
        REFERENCES ship_crew_assignment(crew_assignment_id,ship_id,campaign_id),
    UNIQUE (postal_contract_id,campaign_id),
    CHECK (actual_mail_tons=actual_mail_natural_roll-1)
);

CREATE FUNCTION journey_validate_postal_contract()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE journey_ship bigint; leg_journey bigint; reservation ship_cargo_reservation%ROWTYPE;
        gunner_status text; gunner_position text; ship_class_id bigint;
        rules rule_ship_revenue_system%ROWTYPE;
BEGIN
    SELECT * INTO STRICT rules FROM rule_ship_revenue_system;
    SELECT ship_id INTO STRICT journey_ship FROM journey_journey
    WHERE journey_id=NEW.journey_id AND campaign_id=NEW.campaign_id;
    SELECT journey_id INTO STRICT leg_journey FROM journey_leg
    WHERE journey_leg_id=NEW.journey_leg_id AND campaign_id=NEW.campaign_id;
    SELECT * INTO STRICT reservation FROM ship_cargo_reservation
    WHERE cargo_reservation_id=NEW.cargo_reservation_id FOR UPDATE;
    SELECT assignment.duty_status,definition.position_code
    INTO STRICT gunner_status,gunner_position
    FROM ship_crew_assignment assignment
    JOIN ship_crew_position position USING (ship_crew_position_id,ship_id,campaign_id)
    JOIN ship_crew_position_definition definition USING (crew_position_rule_id)
    WHERE assignment.crew_assignment_id=NEW.gunner_crew_assignment_id
      AND assignment.ship_id=NEW.ship_id AND assignment.campaign_id=NEW.campaign_id;
    SELECT ship_class_rule_id INTO STRICT ship_class_id FROM ship_ship
    WHERE ship_id=NEW.ship_id AND campaign_id=NEW.campaign_id;
    IF journey_ship<>NEW.ship_id OR leg_journey<>NEW.journey_id
       OR reservation.ship_id<>NEW.ship_id OR reservation.campaign_id<>NEW.campaign_id
       OR reservation.journey_id<>NEW.journey_id OR reservation.reservation_kind<>'postal-duty'
       OR reservation.reservation_status<>'reserved'
       OR reservation.reserved_tons<>rules.postal_reserved_tons
       OR NEW.reserved_mail_tons<>rules.postal_reserved_tons
       OR NEW.promised_payment_credits<>rules.postal_payment_credits
       OR NEW.actual_mail_tons<>NEW.actual_mail_natural_roll+rules.postal_actual_modifier
       OR gunner_status<>'active' OR gunner_position<>'gunner'
       OR NOT EXISTS (
          SELECT 1 FROM ship_class_weapon
          WHERE ship_class_rule_id=ship_class_id AND quantity>0
       ) THEN
        RAISE EXCEPTION 'Postal contract requires the published capacity, armed ship, active gunner, roll, and journey' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER journey_postal_contract_valid
BEFORE INSERT OR UPDATE ON journey_postal_contract
FOR EACH ROW EXECUTE FUNCTION journey_validate_postal_contract();

CREATE TABLE journey_postal_delivery_receipt (
    postal_contract_id bigint PRIMARY KEY,
    campaign_id bigint NOT NULL,
    delivered_location_id bigint NOT NULL,
    actual_mail_tons smallint NOT NULL CHECK (actual_mail_tons BETWEEN 0 AND 5),
    paid_credits integer NOT NULL CHECK (paid_credits=25000),
    financial_transaction_id bigint NOT NULL UNIQUE,
    delivered_day bigint NOT NULL,
    delivered_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    source_command_id bigint REFERENCES cmd_command(command_id),
    FOREIGN KEY (postal_contract_id,campaign_id)
        REFERENCES journey_postal_contract(postal_contract_id,campaign_id),
    FOREIGN KEY (delivered_location_id,campaign_id)
        REFERENCES loc_location(location_id,campaign_id),
    FOREIGN KEY (financial_transaction_id,campaign_id)
        REFERENCES fin_transaction(transaction_id,campaign_id)
);

CREATE TABLE journey_postal_cancellation_receipt (
    postal_contract_id bigint PRIMARY KEY,
    campaign_id bigint NOT NULL,
    cancellation_reason text NOT NULL CHECK (btrim(cancellation_reason)<>''),
    cancelled_day bigint NOT NULL,
    cancelled_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    source_command_id bigint REFERENCES cmd_command(command_id),
    FOREIGN KEY (postal_contract_id,campaign_id)
        REFERENCES journey_postal_contract(postal_contract_id,campaign_id)
);

CREATE FUNCTION journey_validate_postal_closure()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE contract journey_postal_contract%ROWTYPE; destination bigint; tx_status text;
BEGIN
    SELECT * INTO STRICT contract FROM journey_postal_contract
    WHERE postal_contract_id=NEW.postal_contract_id AND campaign_id=NEW.campaign_id FOR UPDATE;
    IF TG_TABLE_NAME='journey_postal_delivery_receipt' THEN
        IF EXISTS (SELECT 1 FROM journey_postal_cancellation_receipt WHERE postal_contract_id=NEW.postal_contract_id) THEN
            RAISE EXCEPTION 'Cancelled postal duty cannot be delivered' USING ERRCODE='23514';
        END IF;
        SELECT destination_location_id INTO STRICT destination FROM journey_leg
        WHERE journey_leg_id=contract.journey_leg_id;
        SELECT transaction_status INTO STRICT tx_status FROM fin_transaction
        WHERE transaction_id=NEW.financial_transaction_id AND campaign_id=NEW.campaign_id;
        IF NEW.delivered_location_id<>destination OR NEW.actual_mail_tons<>contract.actual_mail_tons
           OR NEW.paid_credits<>contract.promised_payment_credits OR tx_status<>'posted' THEN
            RAISE EXCEPTION 'Postal delivery does not match destination, mail tonnage, payment, or posted transaction' USING ERRCODE='23514';
        END IF;
        UPDATE ship_cargo_reservation SET reservation_status='fulfilled',ended_at=clock_timestamp(),
            concurrency_version=concurrency_version+1
        WHERE cargo_reservation_id=contract.cargo_reservation_id;
    ELSE
        IF EXISTS (SELECT 1 FROM journey_postal_delivery_receipt WHERE postal_contract_id=NEW.postal_contract_id) THEN
            RAISE EXCEPTION 'Delivered postal duty cannot be cancelled' USING ERRCODE='23514';
        END IF;
        UPDATE ship_cargo_reservation SET reservation_status='cancelled',ended_at=clock_timestamp(),
            concurrency_version=concurrency_version+1
        WHERE cargo_reservation_id=contract.cargo_reservation_id;
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER journey_postal_delivery_valid
BEFORE INSERT ON journey_postal_delivery_receipt
FOR EACH ROW EXECUTE FUNCTION journey_validate_postal_closure();
CREATE TRIGGER journey_postal_cancellation_valid
BEFORE INSERT ON journey_postal_cancellation_receipt
FOR EACH ROW EXECUTE FUNCTION journey_validate_postal_closure();

CREATE TABLE journey_starship_charter_quote_receipt (
    charter_quote_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    campaign_id bigint NOT NULL,
    ship_id bigint NOT NULL,
    ship_class_rule_id bigint NOT NULL REFERENCES ship_class(ship_class_rule_id),
    cargo_capacity_tons_snapshot numeric NOT NULL CHECK (cargo_capacity_tons_snapshot>=0),
    high_berths_snapshot integer NOT NULL CHECK (high_berths_snapshot>=0),
    low_berths_snapshot integer NOT NULL CHECK (low_berths_snapshot>=0),
    billing_blocks integer NOT NULL CHECK (billing_blocks>0),
    cargo_rate_credits integer NOT NULL CHECK (cargo_rate_credits=900),
    high_berth_rate_credits integer NOT NULL CHECK (high_berth_rate_credits=9000),
    low_berth_rate_credits integer NOT NULL CHECK (low_berth_rate_credits=900),
    quoted_price_credits bigint NOT NULL CHECK (quoted_price_credits>=0),
    owner_pays_overhead boolean NOT NULL CHECK (owner_pays_overhead),
    owner_supplies_crew boolean NOT NULL CHECK (owner_supplies_crew),
    quoted_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    source_command_id bigint REFERENCES cmd_command(command_id),
    FOREIGN KEY (ship_id,campaign_id) REFERENCES ship_ship(ship_id,campaign_id),
    UNIQUE (charter_quote_id,campaign_id),
    CHECK (quoted_price_credits=billing_blocks*(
        cargo_capacity_tons_snapshot*cargo_rate_credits
        +high_berths_snapshot*high_berth_rate_credits
        +low_berths_snapshot*low_berth_rate_credits))
);

CREATE FUNCTION journey_validate_starship_charter_quote()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE actual_class bigint; actual_cargo numeric; actual_high integer; actual_low integer;
        rate rule_ship_charter_rate%ROWTYPE;
BEGIN
    SELECT ship.ship_class_rule_id,class.cargo_capacity_tons,
           coalesce(high.characteristic_value,0)::integer,
           coalesce(low.characteristic_value,0)::integer
    INTO STRICT actual_class,actual_cargo,actual_high,actual_low
    FROM ship_ship ship JOIN ship_class class USING (ship_class_rule_id)
    LEFT JOIN ship_class_characteristic high ON high.ship_class_rule_id=class.ship_class_rule_id
        AND high.characteristic_code='staterooms'
    LEFT JOIN ship_class_characteristic low ON low.ship_class_rule_id=class.ship_class_rule_id
        AND low.characteristic_code='low_berths'
    WHERE ship.ship_id=NEW.ship_id AND ship.campaign_id=NEW.campaign_id;
    SELECT * INTO STRICT rate FROM rule_ship_charter_rate WHERE charter_kind='starship';
    IF NEW.ship_class_rule_id<>actual_class OR NEW.cargo_capacity_tons_snapshot<>actual_cargo
       OR NEW.high_berths_snapshot<>actual_high OR NEW.low_berths_snapshot<>actual_low
       OR NEW.cargo_rate_credits<>rate.cargo_ton_rate_credits
       OR NEW.high_berth_rate_credits<>rate.high_berth_rate_credits
       OR NEW.low_berth_rate_credits<>rate.low_berth_rate_credits
       OR NEW.owner_pays_overhead<>rate.owner_pays_overhead
       OR NEW.owner_supplies_crew<>rate.owner_supplies_crew THEN
        RAISE EXCEPTION 'Starship charter quote must snapshot the ship and published two-week rates' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER journey_starship_charter_quote_valid
BEFORE INSERT OR UPDATE ON journey_starship_charter_quote_receipt
FOR EACH ROW EXECUTE FUNCTION journey_validate_starship_charter_quote();

CREATE TABLE journey_starship_charter_contract (
    charter_contract_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    campaign_id bigint NOT NULL,
    charter_quote_id bigint NOT NULL UNIQUE,
    journey_id bigint NOT NULL UNIQUE,
    ship_id bigint NOT NULL,
    promised_payment_credits bigint NOT NULL CHECK (promised_payment_credits>=0),
    accepted_day bigint NOT NULL,
    accepted_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    source_command_id bigint REFERENCES cmd_command(command_id),
    FOREIGN KEY (charter_quote_id,campaign_id)
        REFERENCES journey_starship_charter_quote_receipt(charter_quote_id,campaign_id),
    FOREIGN KEY (journey_id,campaign_id) REFERENCES journey_journey(journey_id,campaign_id),
    FOREIGN KEY (ship_id,campaign_id) REFERENCES ship_ship(ship_id,campaign_id),
    UNIQUE (charter_contract_id,campaign_id)
);

CREATE FUNCTION journey_validate_starship_charter_contract()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE quote journey_starship_charter_quote_receipt%ROWTYPE; journey_ship bigint;
BEGIN
    SELECT * INTO STRICT quote FROM journey_starship_charter_quote_receipt
    WHERE charter_quote_id=NEW.charter_quote_id AND campaign_id=NEW.campaign_id;
    SELECT ship_id INTO STRICT journey_ship FROM journey_journey
    WHERE journey_id=NEW.journey_id AND campaign_id=NEW.campaign_id;
    IF quote.ship_id<>NEW.ship_id OR journey_ship<>NEW.ship_id
       OR quote.quoted_price_credits<>NEW.promised_payment_credits THEN
        RAISE EXCEPTION 'Charter contract does not match its immutable quote and journey ship' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER journey_starship_charter_contract_valid
BEFORE INSERT OR UPDATE ON journey_starship_charter_contract
FOR EACH ROW EXECUTE FUNCTION journey_validate_starship_charter_contract();

CREATE TABLE journey_starship_charter_completion_receipt (
    charter_contract_id bigint PRIMARY KEY,
    campaign_id bigint NOT NULL,
    paid_credits bigint NOT NULL CHECK (paid_credits>=0),
    financial_transaction_id bigint NOT NULL UNIQUE,
    completed_day bigint NOT NULL,
    completed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    source_command_id bigint REFERENCES cmd_command(command_id),
    FOREIGN KEY (charter_contract_id,campaign_id)
        REFERENCES journey_starship_charter_contract(charter_contract_id,campaign_id),
    FOREIGN KEY (financial_transaction_id,campaign_id)
        REFERENCES fin_transaction(transaction_id,campaign_id)
);

CREATE FUNCTION journey_validate_starship_charter_completion()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE promised bigint; tx_status text;
BEGIN
    SELECT promised_payment_credits INTO STRICT promised
    FROM journey_starship_charter_contract
    WHERE charter_contract_id=NEW.charter_contract_id AND campaign_id=NEW.campaign_id;
    SELECT transaction_status INTO STRICT tx_status FROM fin_transaction
    WHERE transaction_id=NEW.financial_transaction_id AND campaign_id=NEW.campaign_id;
    IF NEW.paid_credits<>promised OR tx_status<>'posted' THEN
        RAISE EXCEPTION 'Charter completion requires the quoted payment and a posted transaction' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER journey_starship_charter_completion_valid
BEFORE INSERT ON journey_starship_charter_completion_receipt
FOR EACH ROW EXECUTE FUNCTION journey_validate_starship_charter_completion();

CREATE FUNCTION journey_reject_postal_charter_receipt_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
    RAISE EXCEPTION 'Postal and charter contracts and receipts are immutable';
END $$;

CREATE TRIGGER journey_postal_contract_immutable BEFORE UPDATE OR DELETE ON journey_postal_contract
FOR EACH ROW EXECUTE FUNCTION journey_reject_postal_charter_receipt_mutation();
CREATE TRIGGER journey_postal_delivery_immutable BEFORE UPDATE OR DELETE ON journey_postal_delivery_receipt
FOR EACH ROW EXECUTE FUNCTION journey_reject_postal_charter_receipt_mutation();
CREATE TRIGGER journey_postal_cancellation_immutable BEFORE UPDATE OR DELETE ON journey_postal_cancellation_receipt
FOR EACH ROW EXECUTE FUNCTION journey_reject_postal_charter_receipt_mutation();
CREATE TRIGGER journey_charter_quote_immutable BEFORE UPDATE OR DELETE ON journey_starship_charter_quote_receipt
FOR EACH ROW EXECUTE FUNCTION journey_reject_postal_charter_receipt_mutation();
CREATE TRIGGER journey_charter_contract_immutable BEFORE UPDATE OR DELETE ON journey_starship_charter_contract
FOR EACH ROW EXECUTE FUNCTION journey_reject_postal_charter_receipt_mutation();
CREATE TRIGGER journey_charter_completion_immutable BEFORE UPDATE OR DELETE ON journey_starship_charter_completion_receipt
FOR EACH ROW EXECUTE FUNCTION journey_reject_postal_charter_receipt_mutation();
