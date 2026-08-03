INSERT INTO cmd_command_type VALUES ('open_trade_market','Open trade market');
INSERT INTO cmd_domain_event_type VALUES ('trade_market_opened','Trade market opened');
CREATE TABLE cmd_trade_market_opening_receipt(
 command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
 market_id bigint NOT NULL UNIQUE,market_session_id bigint NOT NULL UNIQUE,supplier_id bigint NOT NULL UNIQUE,
 supplier_stock_generation_id bigint NOT NULL UNIQUE REFERENCES mkt_supplier_stock_generation(supplier_stock_generation_id),
 world_profile_id bigint NOT NULL REFERENCES loc_world_profile(world_profile_id),distinct_stock_count smallint NOT NULL CHECK(distinct_stock_count>0),
 total_quantity_tons numeric NOT NULL CHECK(total_quantity_tons>0),
 FOREIGN KEY(market_id,campaign_id) REFERENCES mkt_market(market_id,campaign_id),
 FOREIGN KEY(market_session_id,campaign_id) REFERENCES mkt_session(market_session_id,campaign_id),
 FOREIGN KEY(supplier_id,campaign_id) REFERENCES mkt_supplier(supplier_id,campaign_id)
);
