ALTER TABLE ship_legal_interest
    ADD CONSTRAINT ship_legal_interest_campaign_key
        UNIQUE (legal_interest_id,campaign_id);

CREATE TABLE ship_mortgage (
    ship_mortgage_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ship_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    legal_interest_id bigint NOT NULL UNIQUE,
    obligation_id bigint NOT NULL UNIQUE,
    operating_cost_code text NOT NULL REFERENCES
        rule_ship_operating_cost(operating_cost_code),
    cash_price_minor bigint NOT NULL CHECK (cash_price_minor>0),
    financed_principal_minor bigint NOT NULL CHECK (
        financed_principal_minor>0
        AND financed_principal_minor<=cash_price_minor
    ),
    total_financed_minor bigint NOT NULL CHECK (
        total_financed_minor>=financed_principal_minor
    ),
    payment_amount_minor bigint NOT NULL CHECK (payment_amount_minor>0),
    term_months smallint NOT NULL CHECK (term_months>0),
    payments_made smallint NOT NULL DEFAULT 0 CHECK (
        payments_made>=0 AND payments_made<=term_months
    ),
    mortgage_status text NOT NULL DEFAULT 'current' CHECK (
        mortgage_status IN (
            'current','delinquent','defaulted',
            'satisfied','forgiven','cancelled'
        )
    ),
    opened_day bigint NOT NULL,
    next_due_day bigint,
    ended_day bigint,
    source_command_id bigint REFERENCES cmd_command(command_id),
    FOREIGN KEY (ship_id,campaign_id)
        REFERENCES ship_ship(ship_id,campaign_id),
    FOREIGN KEY (legal_interest_id,campaign_id)
        REFERENCES ship_legal_interest(legal_interest_id,campaign_id),
    FOREIGN KEY (obligation_id,campaign_id)
        REFERENCES fin_obligation(obligation_id,campaign_id),
    UNIQUE (ship_mortgage_id,campaign_id),
    CHECK (
        (mortgage_status IN ('current','delinquent','defaulted')
         AND ended_day IS NULL)
        OR
        (mortgage_status IN ('satisfied','forgiven','cancelled')
         AND ended_day IS NOT NULL)
    ),
    CHECK (next_due_day IS NULL OR next_due_day>=opened_day),
    CHECK (ended_day IS NULL OR ended_day>=opened_day)
);

CREATE OR REPLACE FUNCTION ship_validate_mortgage()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    interest_record ship_legal_interest%ROWTYPE;
    obligation_record fin_obligation%ROWTYPE;
    cost_record rule_ship_operating_cost%ROWTYPE;
BEGIN
    SELECT * INTO interest_record
    FROM ship_legal_interest
    WHERE legal_interest_id=NEW.legal_interest_id
      AND campaign_id=NEW.campaign_id;
    SELECT * INTO obligation_record
    FROM fin_obligation
    WHERE obligation_id=NEW.obligation_id
      AND campaign_id=NEW.campaign_id;
    SELECT * INTO cost_record
    FROM rule_ship_operating_cost
    WHERE operating_cost_code=NEW.operating_cost_code;

    IF interest_record.ship_id<>NEW.ship_id
       OR interest_record.interest_kind<>'mortgage'
       OR interest_record.ended_at IS NOT NULL
       OR obligation_record.obligation_kind<>'mortgage'
       OR obligation_record.principal_minor<>
          NEW.total_financed_minor
       OR cost_record.cost_kind<>'mortgage' THEN
        RAISE EXCEPTION 'Ship mortgage links are inconsistent'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER ship_mortgage_links_valid
BEFORE INSERT OR UPDATE ON ship_mortgage
FOR EACH ROW EXECUTE FUNCTION ship_validate_mortgage();

CREATE TABLE ship_maintenance_cycle (
    maintenance_cycle_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ship_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    cycle_number integer NOT NULL CHECK (cycle_number>0),
    scheduled_day bigint NOT NULL,
    completed_day bigint,
    months_skipped smallint NOT NULL DEFAULT 0 CHECK (months_skipped>=0),
    natural_roll smallint CHECK (natural_roll BETWEEN 2 AND 12),
    modifier_total smallint,
    final_result smallint,
    system_hits smallint CHECK (system_hits>0),
    maintenance_cost_minor bigint NOT NULL CHECK (
        maintenance_cost_minor>=0
    ),
    maintenance_status text NOT NULL DEFAULT 'scheduled' CHECK (
        maintenance_status IN (
            'scheduled','completed','skipped',
            'failed','waived','cancelled'
        )
    ),
    location_id bigint,
    financial_transaction_id bigint,
    source_command_id bigint REFERENCES cmd_command(command_id),
    FOREIGN KEY (ship_id,campaign_id)
        REFERENCES ship_ship(ship_id,campaign_id),
    FOREIGN KEY (location_id,campaign_id)
        REFERENCES loc_location(location_id,campaign_id),
    FOREIGN KEY (financial_transaction_id,campaign_id)
        REFERENCES fin_transaction(transaction_id,campaign_id),
    UNIQUE (ship_id,cycle_number),
    UNIQUE (maintenance_cycle_id,ship_id,campaign_id),
    CHECK (
        (maintenance_status='completed'
         AND completed_day IS NOT NULL
         AND financial_transaction_id IS NOT NULL)
        OR
        (maintenance_status<>'completed' AND completed_day IS NULL)
    ),
    CHECK (
        (natural_roll IS NULL AND modifier_total IS NULL
         AND final_result IS NULL AND system_hits IS NULL)
        OR
        (natural_roll IS NOT NULL AND modifier_total IS NOT NULL
         AND final_result=natural_roll+modifier_total)
    )
);

CREATE TABLE ship_repair_job (
    repair_job_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ship_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    ship_damage_id bigint NOT NULL,
    location_id bigint,
    repair_kind text NOT NULL CHECK (
        repair_kind IN (
            'field','starport','shipyard','depot','self_repair'
        )
    ),
    repair_status text NOT NULL DEFAULT 'planned' CHECK (
        repair_status IN (
            'planned','underway','completed','failed','cancelled'
        )
    ),
    repair_points smallint NOT NULL CHECK (repair_points>0),
    supply_tons numeric NOT NULL DEFAULT 0 CHECK (supply_tons>=0),
    labor_hours numeric NOT NULL DEFAULT 0 CHECK (labor_hours>=0),
    estimated_cost_minor bigint NOT NULL CHECK (
        estimated_cost_minor>=0
    ),
    financial_transaction_id bigint,
    started_at timestamptz,
    completed_at timestamptz,
    source_command_id bigint REFERENCES cmd_command(command_id),
    FOREIGN KEY (ship_damage_id,ship_id,campaign_id)
        REFERENCES ship_damage(ship_damage_id,ship_id,campaign_id),
    FOREIGN KEY (location_id,campaign_id)
        REFERENCES loc_location(location_id,campaign_id),
    FOREIGN KEY (financial_transaction_id,campaign_id)
        REFERENCES fin_transaction(transaction_id,campaign_id),
    UNIQUE (repair_job_id,campaign_id),
    CHECK (
        (repair_status='planned'
         AND started_at IS NULL AND completed_at IS NULL)
        OR (repair_status='underway'
            AND started_at IS NOT NULL AND completed_at IS NULL)
        OR (repair_status IN ('completed','failed')
            AND started_at IS NOT NULL AND completed_at IS NOT NULL)
        OR (repair_status='cancelled' AND completed_at IS NOT NULL)
    ),
    CHECK (
        repair_status<>'completed'
        OR financial_transaction_id IS NOT NULL
    )
);

CREATE TABLE ship_operating_expense (
    operating_expense_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ship_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    operating_cost_code text NOT NULL REFERENCES
        rule_ship_operating_cost(operating_cost_code),
    financial_transaction_id bigint NOT NULL UNIQUE,
    quantity numeric NOT NULL DEFAULT 1 CHECK (quantity>0),
    amount_minor bigint NOT NULL CHECK (amount_minor>0),
    expense_day bigint NOT NULL,
    description text NOT NULL CHECK (btrim(description)<>''),
    FOREIGN KEY (ship_id,campaign_id)
        REFERENCES ship_ship(ship_id,campaign_id),
    FOREIGN KEY (financial_transaction_id,campaign_id)
        REFERENCES fin_transaction(transaction_id,campaign_id)
);

CREATE OR REPLACE FUNCTION ship_require_posted_financial_transaction()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    transaction_status_value text;
BEGIN
    IF NEW.financial_transaction_id IS NULL THEN
        RETURN NEW;
    END IF;
    SELECT transaction_status INTO transaction_status_value
    FROM fin_transaction
    WHERE transaction_id=NEW.financial_transaction_id
      AND campaign_id=NEW.campaign_id;
    IF transaction_status_value<>'posted' THEN
        RAISE EXCEPTION 'Ship expense requires a posted transaction'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER ship_operating_expense_posted
BEFORE INSERT OR UPDATE ON ship_operating_expense
FOR EACH ROW EXECUTE FUNCTION
    ship_require_posted_financial_transaction();

CREATE TRIGGER ship_completed_maintenance_paid
BEFORE INSERT OR UPDATE ON ship_maintenance_cycle
FOR EACH ROW EXECUTE FUNCTION
    ship_require_posted_financial_transaction();

CREATE TRIGGER ship_completed_repair_paid
BEFORE INSERT OR UPDATE ON ship_repair_job
FOR EACH ROW EXECUTE FUNCTION
    ship_require_posted_financial_transaction();

CREATE OR REPLACE FUNCTION ship_apply_resource_movement()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    quantity_before numeric;
    capacity numeric;
BEGIN
    SELECT current_quantity,capacity_quantity
    INTO quantity_before,capacity
    FROM ship_resource
    WHERE ship_id=NEW.ship_id
      AND campaign_id=NEW.campaign_id
      AND resource_type_code=NEW.resource_type_code
    FOR UPDATE;

    IF quantity_before IS NULL
       OR quantity_before+NEW.quantity_delta<0
       OR quantity_before+NEW.quantity_delta>capacity THEN
        RAISE EXCEPTION 'Ship resource movement exceeds capacity or balance'
            USING ERRCODE='23514';
    END IF;

    NEW.balance_after=quantity_before+NEW.quantity_delta;
    UPDATE ship_resource
    SET current_quantity=NEW.balance_after,
        updated_at=NEW.occurred_at,
        source_command_id=NEW.source_command_id
    WHERE ship_id=NEW.ship_id
      AND resource_type_code=NEW.resource_type_code;
    RETURN NEW;
END;
$$;

CREATE TRIGGER ship_resource_movement_applies_balance
BEFORE INSERT ON ship_resource_movement
FOR EACH ROW EXECUTE FUNCTION ship_apply_resource_movement();
