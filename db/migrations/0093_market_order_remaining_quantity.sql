ALTER TABLE mkt_order
    DROP CONSTRAINT mkt_order_quantity_tons_check,
    ADD CONSTRAINT mkt_order_remaining_quantity_check CHECK (
        quantity_tons>=0
    );

CREATE OR REPLACE FUNCTION mkt_require_positive_new_order()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.quantity_tons<=0 THEN
        RAISE EXCEPTION 'New market order quantity must be positive'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER mkt_order_positive_on_insert
BEFORE INSERT ON mkt_order
FOR EACH ROW EXECUTE FUNCTION mkt_require_positive_new_order();
