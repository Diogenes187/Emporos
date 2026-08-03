ALTER TABLE inv_item_definition DROP CONSTRAINT inv_item_definition_item_kind_check,
 ADD CONSTRAINT inv_item_definition_item_kind_check CHECK(item_kind IN('weapon','armor','equipment','ship','trade_good'));
INSERT INTO inv_item_definition(rule_id,item_kind,minimum_tech_level,cost_credits,mass_grams)
SELECT trade_good_rule_id,'trade_good',NULL,base_price_credits,1000000 FROM rule_trade_good
WHERE good_kind<>'unusual' ON CONFLICT(rule_id) DO NOTHING;

INSERT INTO cmd_command_type VALUES('purchase_trade_goods','Purchase trade goods');
INSERT INTO cmd_domain_event_type VALUES('trade_goods_purchased','Trade goods purchased');
CREATE TABLE cmd_trade_goods_purchase_receipt(
 command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
 broker_operation_command_id bigint NOT NULL UNIQUE REFERENCES cmd_broker_operation_receipt(command_id),
 execution_id bigint NOT NULL UNIQUE,actor_id bigint NOT NULL,ship_id bigint NOT NULL,trade_good_rule_id bigint NOT NULL REFERENCES rule_trade_good(trade_good_rule_id),
 quantity_tons bigint NOT NULL CHECK(quantity_tons>0),unit_price_minor bigint NOT NULL CHECK(unit_price_minor>0),total_price_minor bigint NOT NULL CHECK(total_price_minor=quantity_tons*unit_price_minor),
 lot_id bigint NOT NULL UNIQUE,container_id bigint NOT NULL,financial_transaction_id bigint NOT NULL UNIQUE,inventory_transfer_id bigint NOT NULL UNIQUE,
 FOREIGN KEY(execution_id) REFERENCES mkt_execution(execution_id),FOREIGN KEY(actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id),
 FOREIGN KEY(ship_id,campaign_id) REFERENCES ship_ship(ship_id,campaign_id),FOREIGN KEY(lot_id,campaign_id) REFERENCES inv_lot(lot_id,campaign_id),
 FOREIGN KEY(container_id,campaign_id) REFERENCES inv_container(container_id,campaign_id),FOREIGN KEY(financial_transaction_id,campaign_id) REFERENCES fin_transaction(transaction_id,campaign_id),
 FOREIGN KEY(inventory_transfer_id,campaign_id) REFERENCES inv_transfer(transfer_id,campaign_id)
);

UPDATE inv_container container SET capacity_mass_grams=(class.cargo_capacity_tons*1000000)::bigint
FROM cmd_trading_preparation_receipt receipt JOIN ship_ship ship ON ship.ship_id=receipt.ship_id JOIN ship_class class ON class.ship_class_rule_id=ship.ship_class_rule_id
WHERE container.container_id=receipt.cargo_container_id AND container.capacity_mass_grams IS NULL;
