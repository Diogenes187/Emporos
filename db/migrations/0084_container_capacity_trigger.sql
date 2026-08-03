CREATE OR REPLACE FUNCTION inv_validate_container_capacity()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    target_container bigint;
    maximum_mass bigint;
    used_mass numeric;
    added_mass numeric;
BEGIN
    target_container := NEW.container_id;
    SELECT capacity_mass_grams INTO maximum_mass
    FROM inv_container
    WHERE container_id=target_container
    FOR UPDATE;
    IF maximum_mass IS NULL THEN
        RETURN NEW;
    END IF;

    IF TG_TABLE_NAME='inv_container_item' THEN
        SELECT
            COALESCE((
                SELECT sum(definition.mass_grams)
                FROM inv_container_item placement
                JOIN inv_item_instance item
                  ON item.item_instance_id=placement.item_instance_id
                JOIN inv_item_definition definition
                  ON definition.rule_id=item.item_rule_id
                WHERE placement.container_id=target_container
                  AND placement.item_instance_id IS DISTINCT FROM
                      NEW.item_instance_id
            ),0)
            + COALESCE((
                SELECT sum(definition.mass_grams*placement.quantity)
                FROM inv_container_lot placement
                JOIN inv_lot lot ON lot.lot_id=placement.lot_id
                JOIN inv_item_definition definition
                  ON definition.rule_id=lot.item_rule_id
                WHERE placement.container_id=target_container
            ),0)
        INTO used_mass
        ;

        SELECT definition.mass_grams INTO added_mass
        FROM inv_item_instance item
        JOIN inv_item_definition definition
          ON definition.rule_id=item.item_rule_id
        WHERE item.item_instance_id=NEW.item_instance_id;
    ELSE
        SELECT
            COALESCE((
                SELECT sum(definition.mass_grams)
                FROM inv_container_item placement
                JOIN inv_item_instance item
                  ON item.item_instance_id=placement.item_instance_id
                JOIN inv_item_definition definition
                  ON definition.rule_id=item.item_rule_id
                WHERE placement.container_id=target_container
            ),0)
            + COALESCE((
                SELECT sum(definition.mass_grams*placement.quantity)
                FROM inv_container_lot placement
                JOIN inv_lot lot ON lot.lot_id=placement.lot_id
                JOIN inv_item_definition definition
                  ON definition.rule_id=lot.item_rule_id
                WHERE placement.container_id=target_container
                  AND placement.container_lot_id IS DISTINCT FROM
                      NEW.container_lot_id
            ),0)
        INTO used_mass
        ;

        SELECT definition.mass_grams*NEW.quantity INTO added_mass
        FROM inv_lot lot
        JOIN inv_item_definition definition
          ON definition.rule_id=lot.item_rule_id
        WHERE lot.lot_id=NEW.lot_id;
    END IF;

    IF added_mass IS NULL THEN
        RAISE EXCEPTION
            'Capacity-limited container requires known item mass'
            USING ERRCODE='23514';
    END IF;
    IF used_mass+added_mass > maximum_mass THEN
        RAISE EXCEPTION 'Container mass capacity exceeded'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;
