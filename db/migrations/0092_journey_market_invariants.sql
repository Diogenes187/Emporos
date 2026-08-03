ALTER TABLE mkt_supplier
    ADD CONSTRAINT mkt_supplier_campaign_key
        UNIQUE (supplier_id,campaign_id);

ALTER TABLE mkt_stock
    ADD CONSTRAINT mkt_stock_supplier_scope_fkey
        FOREIGN KEY (supplier_id,campaign_id)
        REFERENCES mkt_supplier(supplier_id,campaign_id);

CREATE OR REPLACE FUNCTION journey_validate_activation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.journey_status IN ('ready','underway')
       AND OLD.journey_status NOT IN ('ready','underway') THEN
        IF NOT EXISTS (
            SELECT 1 FROM journey_leg
            WHERE journey_id=NEW.journey_id AND leg_order=1
        ) THEN
            RAISE EXCEPTION 'Active journey requires a first leg'
                USING ERRCODE='23514';
        END IF;
        IF EXISTS (
            SELECT 1
            FROM journey_participant participant
            JOIN journey_participant other
              ON other.actor_id=participant.actor_id
             AND other.journey_id<>participant.journey_id
             AND other.commitment_status='committed'
            JOIN journey_journey other_journey
              ON other_journey.journey_id=other.journey_id
             AND other_journey.journey_status IN ('ready','underway')
            WHERE participant.journey_id=NEW.journey_id
              AND participant.commitment_status='committed'
        ) THEN
            RAISE EXCEPTION
                'Journey participant is committed to another active journey'
                USING ERRCODE='23505';
        END IF;
        IF EXISTS (
            SELECT 1
            FROM journey_participant participant
            JOIN journey_leg first_leg
              ON first_leg.journey_id=participant.journey_id
             AND first_leg.leg_order=1
            LEFT JOIN loc_actor_position position
              ON position.actor_id=participant.actor_id
             AND position.ended_at IS NULL
            WHERE participant.journey_id=NEW.journey_id
              AND participant.commitment_status='committed'
              AND position.location_id IS DISTINCT FROM
                  first_leg.origin_location_id
        ) THEN
            RAISE EXCEPTION
                'Journey participant is not at the first leg origin'
                USING ERRCODE='23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER journey_activation_invariants
BEFORE UPDATE OF journey_status ON journey_journey
FOR EACH ROW EXECUTE FUNCTION journey_validate_activation();

CREATE OR REPLACE FUNCTION mkt_validate_execution()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    available numeric;
    order_record mkt_order%ROWTYPE;
    quote_record mkt_quote%ROWTYPE;
BEGIN
    SELECT * INTO order_record
    FROM mkt_order
    WHERE order_id=NEW.order_id
      AND campaign_id=NEW.campaign_id
    FOR UPDATE;
    SELECT * INTO quote_record
    FROM mkt_quote
    WHERE quote_id=NEW.quote_id
      AND campaign_id=NEW.campaign_id
    FOR UPDATE;
    IF order_record.market_session_id<>NEW.market_session_id
       OR quote_record.market_session_id<>NEW.market_session_id
       OR order_record.trade_good_rule_id<>
          quote_record.trade_good_rule_id
       OR quote_record.stock_id<>NEW.stock_id
       OR quote_record.quote_status<>'open'
       OR order_record.order_status NOT IN ('open','partially_filled')
       OR order_record.order_side=(
          CASE quote_record.quote_side
              WHEN 'buy' THEN 'buy' ELSE 'sell'
          END
       ) THEN
        RAISE EXCEPTION 'Market execution links are inconsistent'
            USING ERRCODE='23514';
    END IF;
    IF quote_record.unit_price_minor<>NEW.unit_price_minor
       OR (
           order_record.limit_price_minor IS NOT NULL
           AND (
               (order_record.order_side='buy'
                AND NEW.unit_price_minor>order_record.limit_price_minor)
               OR (order_record.order_side='sell'
                   AND NEW.unit_price_minor<
                       order_record.limit_price_minor)
           )
       ) THEN
        RAISE EXCEPTION 'Market execution violates quoted or limit price'
            USING ERRCODE='23514';
    END IF;

    SELECT quantity_tons INTO available
    FROM mkt_stock
    WHERE stock_id=NEW.stock_id
      AND campaign_id=NEW.campaign_id
      AND market_session_id=NEW.market_session_id
      AND trade_good_rule_id=order_record.trade_good_rule_id
      AND stock_status='available'
    FOR UPDATE;
    IF available IS NULL OR available<NEW.quantity_tons
       OR NEW.quantity_tons>order_record.quantity_tons
       OR (
           quote_record.maximum_quantity_tons IS NOT NULL
           AND NEW.quantity_tons>quote_record.maximum_quantity_tons
       ) THEN
        RAISE EXCEPTION 'Market execution exceeds available quantity'
            USING ERRCODE='23514';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM inv_transfer
        WHERE transfer_id=NEW.inventory_transfer_id
          AND campaign_id=NEW.campaign_id
          AND transfer_status='completed'
    ) THEN
        RAISE EXCEPTION
            'Market execution requires completed inventory transfer'
            USING ERRCODE='23514';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM fin_transaction
        WHERE transaction_id=NEW.financial_transaction_id
          AND campaign_id=NEW.campaign_id
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

    UPDATE mkt_order
    SET quantity_tons=quantity_tons-NEW.quantity_tons,
        order_status=CASE
            WHEN quantity_tons-NEW.quantity_tons=0 THEN 'filled'
            ELSE 'partially_filled'
        END
    WHERE order_id=NEW.order_id;
    UPDATE mkt_quote SET quote_status='accepted'
    WHERE quote_id=NEW.quote_id;
    RETURN NEW;
END;
$$;
