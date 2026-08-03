DROP VIEW fin_account_balance;

CREATE VIEW fin_account_balance AS
SELECT
    account.account_id,
    account.campaign_id,
    account.currency_code,
    COALESCE(
        sum(entry.amount_minor) FILTER (
            WHERE transaction.transaction_status IN ('posted','reversed')
        ),
        0
    )::bigint AS balance_minor
FROM fin_account account
LEFT JOIN fin_entry entry ON entry.account_id=account.account_id
LEFT JOIN fin_transaction transaction
  ON transaction.transaction_id=entry.transaction_id
GROUP BY account.account_id,account.campaign_id,account.currency_code;

ALTER TABLE fin_transaction
    RENAME COLUMN posted_at TO finalized_at;

ALTER TABLE fin_transaction
    DROP CONSTRAINT fin_transaction_reversal_of_transaction_id_fkey,
    ADD CONSTRAINT fin_transaction_reversal_same_scope_fkey
        FOREIGN KEY (
            reversal_of_transaction_id,campaign_id,currency_code
        )
        REFERENCES fin_transaction(
            transaction_id,campaign_id,currency_code
        );

CREATE OR REPLACE FUNCTION fin_validate_transaction_posting()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    entry_count integer;
    balance numeric;
    reversal_matches boolean;
BEGIN
    IF NEW.transaction_status='posted'
       AND OLD.transaction_status IS DISTINCT FROM 'posted' THEN
        IF OLD.transaction_status<>'pending' THEN
            RAISE EXCEPTION 'Only pending transactions may be posted'
                USING ERRCODE='23514';
        END IF;
        SELECT count(*),COALESCE(sum(amount_minor),0)
        INTO entry_count,balance
        FROM fin_entry
        WHERE transaction_id=NEW.transaction_id;
        IF entry_count<2 THEN
            RAISE EXCEPTION
                'Posted transaction requires at least two entries'
                USING ERRCODE='23514';
        END IF;
        IF balance<>0 THEN
            RAISE EXCEPTION 'Posted transaction must balance to zero'
                USING ERRCODE='23514';
        END IF;

        IF NEW.reversal_of_transaction_id IS NOT NULL THEN
            SELECT NOT EXISTS (
                SELECT account_id,amount_minor
                FROM fin_entry
                WHERE transaction_id=NEW.reversal_of_transaction_id
                EXCEPT ALL
                SELECT account_id,-amount_minor
                FROM fin_entry
                WHERE transaction_id=NEW.transaction_id
            ) AND NOT EXISTS (
                SELECT account_id,-amount_minor
                FROM fin_entry
                WHERE transaction_id=NEW.transaction_id
                EXCEPT ALL
                SELECT account_id,amount_minor
                FROM fin_entry
                WHERE transaction_id=NEW.reversal_of_transaction_id
            )
            INTO reversal_matches;
            IF NOT reversal_matches THEN
                RAISE EXCEPTION
                    'Reversal entries must negate the original transaction'
                    USING ERRCODE='23514';
            END IF;
        END IF;
    END IF;

    IF NEW.transaction_status='reversed'
       AND OLD.transaction_status IS DISTINCT FROM 'reversed' THEN
        IF OLD.transaction_status<>'posted' OR NOT EXISTS (
            SELECT 1
            FROM fin_transaction reversal
            WHERE reversal.reversal_of_transaction_id=
                  NEW.transaction_id
              AND reversal.transaction_status='posted'
        ) THEN
            RAISE EXCEPTION
                'Posted reversal is required before marking original reversed'
                USING ERRCODE='23514';
        END IF;
    END IF;

    IF OLD.transaction_status IN ('posted','reversed')
       AND NEW.transaction_status<>OLD.transaction_status
       AND NOT (
           OLD.transaction_status='posted'
           AND NEW.transaction_status='reversed'
       ) THEN
        RAISE EXCEPTION 'Posted financial transaction is immutable'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION fin_post_transaction(
    target_transaction_id bigint
)
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE fin_transaction
    SET transaction_status='posted',finalized_at=clock_timestamp()
    WHERE transaction_id=target_transaction_id
      AND transaction_status='pending';
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Financial transaction is not pending'
            USING ERRCODE='23514';
    END IF;
END;
$$;

CREATE OR REPLACE FUNCTION inv_reject_container_owner_update()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION
        'Container owner associations are immutable; replace the row'
        USING ERRCODE='23514';
END;
$$;

CREATE TRIGGER inv_actor_container_owner_immutable
BEFORE UPDATE ON inv_actor_container
FOR EACH ROW EXECUTE FUNCTION inv_reject_container_owner_update();

CREATE TRIGGER inv_faction_container_owner_immutable
BEFORE UPDATE ON inv_faction_container
FOR EACH ROW EXECUTE FUNCTION inv_reject_container_owner_update();

CREATE TRIGGER inv_location_container_owner_immutable
BEFORE UPDATE ON inv_location_container
FOR EACH ROW EXECUTE FUNCTION inv_reject_container_owner_update();

CREATE TRIGGER inv_item_container_owner_immutable
BEFORE UPDATE ON inv_item_container
FOR EACH ROW EXECUTE FUNCTION inv_reject_container_owner_update();

DROP TRIGGER inv_container_item_one_position ON inv_container_item;
CREATE TRIGGER inv_container_item_one_position
BEFORE INSERT OR UPDATE ON inv_container_item
FOR EACH ROW EXECUTE FUNCTION inv_reject_multiple_item_positions();

DROP TRIGGER loc_item_position_one_position ON loc_item_position;
CREATE TRIGGER loc_item_position_one_position
BEFORE INSERT OR UPDATE ON loc_item_position
FOR EACH ROW EXECUTE FUNCTION inv_reject_multiple_item_positions();

CREATE OR REPLACE FUNCTION inv_validate_lot_quantity_reduction()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    allocated bigint;
BEGIN
    IF NEW.quantity>=OLD.quantity THEN
        RETURN NEW;
    END IF;
    SELECT COALESCE(sum(quantity),0) INTO allocated
    FROM inv_container_lot
    WHERE lot_id=NEW.lot_id;
    IF allocated>NEW.quantity THEN
        RAISE EXCEPTION
            'Lot quantity cannot be less than allocated quantity'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER inv_lot_quantity_reduction
BEFORE UPDATE OF quantity ON inv_lot
FOR EACH ROW EXECUTE FUNCTION inv_validate_lot_quantity_reduction();
