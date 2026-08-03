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

    IF TG_TABLE_NAME='inv_container_item' THEN
        IF NOT EXISTS (
            SELECT 1
            FROM inv_item_instance
            WHERE item_instance_id=NEW.item_instance_id
              AND campaign_id=NEW.campaign_id
              AND item_status='active'
        ) THEN
            RAISE EXCEPTION 'Only active items may enter a container'
                USING ERRCODE='23514';
        END IF;
    ELSE
        IF NOT EXISTS (
            SELECT 1
            FROM inv_lot
            WHERE lot_id=NEW.lot_id
              AND campaign_id=NEW.campaign_id
              AND lot_status='active'
        ) THEN
            RAISE EXCEPTION 'Only active lots may enter a container'
                USING ERRCODE='23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;
