CREATE TABLE rule_trade_good (
    trade_good_rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    good_code text NOT NULL UNIQUE CHECK (
        good_code ~ '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
    ),
    d66_result smallint UNIQUE CHECK (
        d66_result IS NULL
        OR (
            d66_result BETWEEN 11 AND 66
            AND d66_result/10 BETWEEN 1 AND 6
            AND d66_result%10 BETWEEN 1 AND 6
        )
    ),
    good_kind text NOT NULL CHECK (
        good_kind IN ('common','trade','unusual')
    ),
    base_price_credits bigint CHECK (base_price_credits>0),
    availability_dice_count smallint CHECK (
        availability_dice_count>0
    ),
    availability_die_sides smallint CHECK (
        availability_die_sides>1
    ),
    availability_multiplier smallint CHECK (
        availability_multiplier>0
    ),
    black_market_only boolean NOT NULL,
    CHECK (
        (good_kind='unusual' AND base_price_credits IS NULL
         AND availability_dice_count IS NULL
         AND availability_die_sides IS NULL
         AND availability_multiplier IS NULL)
        OR (good_kind<>'unusual' AND base_price_credits IS NOT NULL
            AND availability_dice_count IS NOT NULL
            AND availability_die_sides IS NOT NULL
            AND availability_multiplier IS NOT NULL)
    )
);

CREATE TABLE rule_trade_good_modifier (
    trade_good_rule_id bigint NOT NULL REFERENCES
        rule_trade_good(trade_good_rule_id),
    trade_code_rule_id bigint NOT NULL REFERENCES
        loc_trade_code(trade_code_rule_id),
    transaction_side text NOT NULL CHECK (
        transaction_side IN ('purchase','sale')
    ),
    dice_modifier smallint NOT NULL,
    PRIMARY KEY (
        trade_good_rule_id,trade_code_rule_id,transaction_side
    )
);

CREATE TABLE rule_modified_price_band (
    modified_price_band_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    minimum_result smallint,
    maximum_result smallint,
    purchase_percent smallint NOT NULL CHECK (purchase_percent>0),
    sale_percent smallint NOT NULL CHECK (sale_percent>0),
    CHECK (
        minimum_result IS NULL OR maximum_result IS NULL
        OR minimum_result<=maximum_result
    )
);

CREATE UNIQUE INDEX rule_modified_price_band_range_unique
    ON rule_modified_price_band(
        COALESCE(minimum_result,-32768),
        COALESCE(maximum_result,32767)
    );

INSERT INTO rule_modified_price_band(
    minimum_result,maximum_result,purchase_percent,sale_percent
) VALUES
    (NULL,2,200,40),(3,3,180,50),(4,4,160,60),
    (5,5,140,70),(6,6,120,80),(7,7,110,90),
    (8,8,100,100),(9,9,90,110),(10,10,80,120),
    (11,11,70,140),(12,12,60,160),(13,13,50,180),
    (14,14,40,200),(15,15,30,300),(16,NULL,20,400);

CREATE TABLE rule_local_broker (
    skill_level smallint PRIMARY KEY CHECK (skill_level BETWEEN 1 AND 4),
    commission_percent smallint NOT NULL CHECK (
        commission_percent BETWEEN 0 AND 100
    ),
    maximum_starport_code text NOT NULL REFERENCES
        rule_starport_class(starport_code)
);

INSERT INTO rule_local_broker VALUES
    (1,5,'E'),(2,10,'C'),(3,15,'B'),(4,20,'A');

CREATE TABLE mkt_market (
    market_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    location_id bigint NOT NULL,
    name text NOT NULL CHECK (btrim(name)<>''),
    market_kind text NOT NULL CHECK (
        market_kind IN ('legal','black','mixed','private')
    ),
    settlement_account_id bigint,
    market_status text NOT NULL DEFAULT 'active' CHECK (
        market_status IN ('active','closed','destroyed')
    ),
    FOREIGN KEY (location_id,campaign_id)
        REFERENCES loc_location(location_id,campaign_id),
    FOREIGN KEY (settlement_account_id,campaign_id)
        REFERENCES fin_account(account_id,campaign_id),
    UNIQUE (market_id,campaign_id),
    UNIQUE (campaign_id,location_id,name)
);

CREATE TABLE mkt_session (
    market_session_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    market_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    opened_day bigint NOT NULL,
    opened_second integer NOT NULL CHECK (
        opened_second BETWEEN 0 AND 86399
    ),
    expires_day bigint NOT NULL,
    expires_second integer NOT NULL CHECK (
        expires_second BETWEEN 0 AND 86399
    ),
    session_status text NOT NULL DEFAULT 'open' CHECK (
        session_status IN ('open','closed','expired','cancelled')
    ),
    source_command_id bigint REFERENCES cmd_command(command_id),
    FOREIGN KEY (market_id,campaign_id)
        REFERENCES mkt_market(market_id,campaign_id),
    UNIQUE (market_session_id,campaign_id),
    UNIQUE (market_id,opened_day,opened_second),
    CHECK (
        (expires_day,expires_second)>(opened_day,opened_second)
    )
);

CREATE TABLE mkt_supplier (
    supplier_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    market_session_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    actor_id bigint,
    faction_id bigint,
    supplier_kind text NOT NULL CHECK (
        supplier_kind IN ('supplier','buyer','broker')
    ),
    broker_skill_level smallint CHECK (broker_skill_level>=0),
    FOREIGN KEY (market_session_id,campaign_id)
        REFERENCES mkt_session(market_session_id,campaign_id),
    FOREIGN KEY (actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    FOREIGN KEY (faction_id,campaign_id)
        REFERENCES actor_faction(faction_id,campaign_id),
    CHECK (
        (actor_id IS NOT NULL)::integer
        +(faction_id IS NOT NULL)::integer=1
    )
);

CREATE TABLE mkt_stock (
    stock_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    market_session_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    supplier_id bigint,
    trade_good_rule_id bigint NOT NULL REFERENCES
        rule_trade_good(trade_good_rule_id),
    lot_id bigint,
    quantity_tons numeric NOT NULL CHECK (quantity_tons>=0),
    stock_status text NOT NULL DEFAULT 'available' CHECK (
        stock_status IN ('available','reserved','sold','withdrawn')
    ),
    concurrency_version bigint NOT NULL DEFAULT 1 CHECK (
        concurrency_version>0
    ),
    FOREIGN KEY (market_session_id,campaign_id)
        REFERENCES mkt_session(market_session_id,campaign_id),
    FOREIGN KEY (lot_id,campaign_id)
        REFERENCES inv_lot(lot_id,campaign_id),
    UNIQUE (stock_id,campaign_id),
    UNIQUE NULLS NOT DISTINCT (
        market_session_id,supplier_id,trade_good_rule_id,lot_id
    )
);

CREATE TABLE mkt_quote (
    quote_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    market_session_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    stock_id bigint,
    trade_good_rule_id bigint NOT NULL REFERENCES
        rule_trade_good(trade_good_rule_id),
    quote_side text NOT NULL CHECK (quote_side IN ('buy','sell')),
    quoted_actor_id bigint,
    quoted_faction_id bigint,
    unit_price_minor bigint NOT NULL CHECK (unit_price_minor>0),
    maximum_quantity_tons numeric CHECK (maximum_quantity_tons>0),
    price_result smallint,
    price_percent smallint CHECK (price_percent>0),
    quote_status text NOT NULL DEFAULT 'open' CHECK (
        quote_status IN ('open','accepted','rejected','expired','withdrawn')
    ),
    expires_day bigint,
    expires_second integer CHECK (
        expires_second IS NULL OR expires_second BETWEEN 0 AND 86399
    ),
    source_command_id bigint REFERENCES cmd_command(command_id),
    FOREIGN KEY (market_session_id,campaign_id)
        REFERENCES mkt_session(market_session_id,campaign_id),
    FOREIGN KEY (stock_id,campaign_id)
        REFERENCES mkt_stock(stock_id,campaign_id),
    FOREIGN KEY (quoted_actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    FOREIGN KEY (quoted_faction_id,campaign_id)
        REFERENCES actor_faction(faction_id,campaign_id),
    UNIQUE (quote_id,campaign_id),
    CHECK (
        (quoted_actor_id IS NOT NULL)::integer
        +(quoted_faction_id IS NOT NULL)::integer<=1
    ),
    CHECK ((expires_day IS NULL)=(expires_second IS NULL))
);

CREATE UNIQUE INDEX mkt_one_open_scoped_quote
    ON mkt_quote(
        market_session_id,trade_good_rule_id,quote_side,
        COALESCE(quoted_actor_id,0),COALESCE(quoted_faction_id,0)
    )
    WHERE quote_status='open';

CREATE TABLE mkt_quote_modifier (
    quote_modifier_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    quote_id bigint NOT NULL REFERENCES mkt_quote(quote_id),
    modifier_kind text NOT NULL CHECK (
        modifier_kind IN (
            'skill','characteristic','purchase_trade_code',
            'sale_trade_code','counterparty_broker','other'
        )
    ),
    trade_code_rule_id bigint REFERENCES
        loc_trade_code(trade_code_rule_id),
    modifier_value smallint NOT NULL,
    explanation text NOT NULL CHECK (btrim(explanation)<>'')
);

CREATE TABLE mkt_order (
    order_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    market_session_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    actor_id bigint,
    faction_id bigint,
    settlement_account_id bigint NOT NULL,
    trade_good_rule_id bigint NOT NULL REFERENCES
        rule_trade_good(trade_good_rule_id),
    order_side text NOT NULL CHECK (order_side IN ('buy','sell')),
    quantity_tons numeric NOT NULL CHECK (quantity_tons>0),
    limit_price_minor bigint CHECK (limit_price_minor>0),
    order_status text NOT NULL DEFAULT 'open' CHECK (
        order_status IN (
            'open','partially_filled','filled','cancelled','rejected'
        )
    ),
    source_command_id bigint REFERENCES cmd_command(command_id),
    FOREIGN KEY (market_session_id,campaign_id)
        REFERENCES mkt_session(market_session_id,campaign_id),
    FOREIGN KEY (actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    FOREIGN KEY (faction_id,campaign_id)
        REFERENCES actor_faction(faction_id,campaign_id),
    FOREIGN KEY (settlement_account_id,campaign_id)
        REFERENCES fin_account(account_id,campaign_id),
    UNIQUE (order_id,campaign_id),
    CHECK (
        (actor_id IS NOT NULL)::integer
        +(faction_id IS NOT NULL)::integer=1
    )
);

CREATE TABLE mkt_execution (
    execution_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    market_session_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    order_id bigint NOT NULL,
    quote_id bigint NOT NULL,
    stock_id bigint NOT NULL,
    quantity_tons numeric NOT NULL CHECK (quantity_tons>0),
    unit_price_minor bigint NOT NULL CHECK (unit_price_minor>0),
    total_price_minor numeric GENERATED ALWAYS AS (
        quantity_tons*unit_price_minor
    ) STORED,
    inventory_transfer_id bigint NOT NULL,
    financial_transaction_id bigint NOT NULL,
    executed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    source_command_id bigint REFERENCES cmd_command(command_id),
    FOREIGN KEY (market_session_id,campaign_id)
        REFERENCES mkt_session(market_session_id,campaign_id),
    FOREIGN KEY (order_id,campaign_id)
        REFERENCES mkt_order(order_id,campaign_id),
    FOREIGN KEY (quote_id,campaign_id)
        REFERENCES mkt_quote(quote_id,campaign_id),
    FOREIGN KEY (stock_id,campaign_id)
        REFERENCES mkt_stock(stock_id,campaign_id),
    FOREIGN KEY (inventory_transfer_id,campaign_id)
        REFERENCES inv_transfer(transfer_id,campaign_id),
    FOREIGN KEY (financial_transaction_id,campaign_id)
        REFERENCES fin_transaction(transaction_id,campaign_id)
);

CREATE OR REPLACE FUNCTION mkt_validate_execution()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    available numeric;
BEGIN
    SELECT quantity_tons INTO available
    FROM mkt_stock
    WHERE stock_id=NEW.stock_id
      AND campaign_id=NEW.campaign_id
      AND stock_status='available'
    FOR UPDATE;
    IF available IS NULL OR available<NEW.quantity_tons THEN
        RAISE EXCEPTION 'Market execution exceeds available stock'
            USING ERRCODE='23514';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM inv_transfer
        WHERE transfer_id=NEW.inventory_transfer_id
          AND transfer_status='completed'
    ) THEN
        RAISE EXCEPTION
            'Market execution requires completed inventory transfer'
            USING ERRCODE='23514';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM fin_transaction
        WHERE transaction_id=NEW.financial_transaction_id
          AND transaction_status='posted'
    ) THEN
        RAISE EXCEPTION
            'Market execution requires posted financial transaction'
            USING ERRCODE='23514';
    END IF;
    UPDATE mkt_stock
    SET quantity_tons=quantity_tons-NEW.quantity_tons,
        stock_status=CASE
            WHEN quantity_tons-NEW.quantity_tons=0 THEN 'sold'
            ELSE stock_status
        END,
        concurrency_version=concurrency_version+1
    WHERE stock_id=NEW.stock_id;
    RETURN NEW;
END;
$$;

CREATE TRIGGER mkt_execution_atomic_links
BEFORE INSERT ON mkt_execution
FOR EACH ROW EXECUTE FUNCTION mkt_validate_execution();
