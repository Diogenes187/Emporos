DROP VIEW fin_obligation_balance;

CREATE VIEW fin_obligation_balance AS
SELECT
    obligation.obligation_id,
    obligation.campaign_id,
    obligation.currency_code,
    obligation.principal_minor,
    COALESCE(
        sum(payment.amount_minor) FILTER (
            WHERE transaction.transaction_status='posted'
        ),
        0
    )::bigint AS paid_minor,
    (
        obligation.principal_minor
        -COALESCE(
            sum(payment.amount_minor) FILTER (
                WHERE transaction.transaction_status='posted'
            ),
            0
        )
    )::bigint AS outstanding_minor
FROM fin_obligation obligation
LEFT JOIN fin_obligation_payment payment
  ON payment.obligation_id=obligation.obligation_id
LEFT JOIN fin_transaction transaction
  ON transaction.transaction_id=payment.transaction_id
GROUP BY
    obligation.obligation_id,
    obligation.campaign_id,
    obligation.currency_code,
    obligation.principal_minor;

CREATE OR REPLACE FUNCTION inv_require_open_container_and_active_item()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM inv_container
        WHERE container_id=NEW.container_id
          AND campaign_id=NEW.campaign_id
          AND container_status='active'
    ) THEN
        RAISE EXCEPTION 'Items may only enter an active container'
            USING ERRCODE='23514';
    END IF;
    IF TG_TABLE_NAME='inv_container_item' AND NOT EXISTS (
        SELECT 1
        FROM inv_item_instance
        WHERE item_instance_id=NEW.item_instance_id
          AND campaign_id=NEW.campaign_id
          AND item_status='active'
    ) THEN
        RAISE EXCEPTION 'Only active items may enter a container'
            USING ERRCODE='23514';
    END IF;
    IF TG_TABLE_NAME='inv_container_lot' AND NOT EXISTS (
        SELECT 1
        FROM inv_lot
        WHERE lot_id=NEW.lot_id
          AND campaign_id=NEW.campaign_id
          AND lot_status='active'
    ) THEN
        RAISE EXCEPTION 'Only active lots may enter a container'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER inv_container_item_active_state
BEFORE INSERT OR UPDATE ON inv_container_item
FOR EACH ROW EXECUTE FUNCTION
    inv_require_open_container_and_active_item();

CREATE TRIGGER inv_container_lot_active_state
BEFORE INSERT OR UPDATE ON inv_container_lot
FOR EACH ROW EXECUTE FUNCTION
    inv_require_open_container_and_active_item();

CREATE OR REPLACE FUNCTION inv_validate_container_capacity_change()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    known_mass numeric;
    unknown_count bigint;
BEGIN
    IF NEW.capacity_mass_grams IS NULL
       OR NEW.capacity_mass_grams IS NOT DISTINCT FROM
          OLD.capacity_mass_grams THEN
        RETURN NEW;
    END IF;

    SELECT
        COALESCE((
            SELECT sum(definition.mass_grams)
            FROM inv_container_item placement
            JOIN inv_item_instance item
              ON item.item_instance_id=placement.item_instance_id
            JOIN inv_item_definition definition
              ON definition.rule_id=item.item_rule_id
            WHERE placement.container_id=NEW.container_id
        ),0)
        +COALESCE((
            SELECT sum(definition.mass_grams*placement.quantity)
            FROM inv_container_lot placement
            JOIN inv_lot lot ON lot.lot_id=placement.lot_id
            JOIN inv_item_definition definition
              ON definition.rule_id=lot.item_rule_id
            WHERE placement.container_id=NEW.container_id
        ),0),
        (
            SELECT count(*)
            FROM inv_container_item placement
            JOIN inv_item_instance item
              ON item.item_instance_id=placement.item_instance_id
            JOIN inv_item_definition definition
              ON definition.rule_id=item.item_rule_id
            WHERE placement.container_id=NEW.container_id
              AND definition.mass_grams IS NULL
        )
        +(
            SELECT count(*)
            FROM inv_container_lot placement
            JOIN inv_lot lot ON lot.lot_id=placement.lot_id
            JOIN inv_item_definition definition
              ON definition.rule_id=lot.item_rule_id
            WHERE placement.container_id=NEW.container_id
              AND definition.mass_grams IS NULL
        )
    INTO known_mass,unknown_count;

    IF unknown_count>0 THEN
        RAISE EXCEPTION
            'Capacity-limited container requires known item mass'
            USING ERRCODE='23514';
    END IF;
    IF known_mass>NEW.capacity_mass_grams THEN
        RAISE EXCEPTION 'Container mass capacity exceeded'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER inv_container_capacity_change
BEFORE UPDATE OF capacity_mass_grams ON inv_container
FOR EACH ROW EXECUTE FUNCTION inv_validate_container_capacity_change();

CREATE OR REPLACE FUNCTION inv_require_active_equipped_item()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.unequipped_at IS NULL AND NOT EXISTS (
        SELECT 1
        FROM inv_item_instance
        WHERE item_instance_id=NEW.item_instance_id
          AND campaign_id=NEW.campaign_id
          AND item_status='active'
    ) THEN
        RAISE EXCEPTION 'Only active items may be equipped'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER inv_equipped_item_active_state
BEFORE INSERT OR UPDATE ON inv_equipped_item
FOR EACH ROW EXECUTE FUNCTION inv_require_active_equipped_item();
