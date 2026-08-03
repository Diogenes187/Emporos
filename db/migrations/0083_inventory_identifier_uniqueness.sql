ALTER TABLE inv_item_instance
    DROP CONSTRAINT
        inv_item_instance_campaign_id_item_rule_id_serial_identifie_key;

CREATE UNIQUE INDEX inv_unique_defined_item_serial
    ON inv_item_instance(campaign_id,item_rule_id,serial_identifier)
    WHERE serial_identifier IS NOT NULL;

ALTER TABLE inv_lot
    DROP CONSTRAINT
        inv_lot_campaign_id_item_rule_id_lot_identifier_key;

CREATE UNIQUE INDEX inv_unique_defined_lot_identifier
    ON inv_lot(campaign_id,item_rule_id,lot_identifier)
    WHERE lot_identifier IS NOT NULL;
