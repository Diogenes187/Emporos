INSERT INTO cmd_command_type VALUES('sell_trade_goods','Sell trade goods');
INSERT INTO cmd_domain_event_type VALUES('trade_goods_sold','Trade goods sold');
CREATE TABLE cmd_trade_goods_sale_receipt(
 command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
 broker_operation_command_id bigint NOT NULL UNIQUE REFERENCES cmd_broker_operation_receipt(command_id),execution_id bigint NOT NULL UNIQUE REFERENCES mkt_execution(execution_id),
 actor_id bigint NOT NULL,ship_id bigint NOT NULL,trade_good_rule_id bigint NOT NULL REFERENCES rule_trade_good(trade_good_rule_id),lot_id bigint NOT NULL,
 quantity_tons bigint NOT NULL CHECK(quantity_tons>0),unit_price_minor bigint NOT NULL CHECK(unit_price_minor>0),total_price_minor bigint NOT NULL CHECK(total_price_minor=quantity_tons*unit_price_minor),
 financial_transaction_id bigint NOT NULL UNIQUE,inventory_transfer_id bigint NOT NULL UNIQUE,
 FOREIGN KEY(actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id),FOREIGN KEY(ship_id,campaign_id) REFERENCES ship_ship(ship_id,campaign_id),
 FOREIGN KEY(lot_id,campaign_id) REFERENCES inv_lot(lot_id,campaign_id),FOREIGN KEY(financial_transaction_id,campaign_id) REFERENCES fin_transaction(transaction_id,campaign_id),
 FOREIGN KEY(inventory_transfer_id,campaign_id) REFERENCES inv_transfer(transfer_id,campaign_id)
);
