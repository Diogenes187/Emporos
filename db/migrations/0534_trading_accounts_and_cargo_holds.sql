INSERT INTO cmd_command_type VALUES ('prepare_trading','Prepare trading');
INSERT INTO cmd_domain_event_type VALUES ('trading_prepared','Trading prepared');
CREATE TABLE cmd_trading_preparation_receipt(
 command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
 actor_id bigint NOT NULL,ship_id bigint NOT NULL,trader_account_id bigint NOT NULL UNIQUE,campaign_equity_account_id bigint NOT NULL,
 cargo_container_id bigint NOT NULL UNIQUE,opening_balance_minor bigint NOT NULL CHECK(opening_balance_minor>=0),
 opening_transaction_id bigint UNIQUE REFERENCES fin_transaction(transaction_id),
 FOREIGN KEY(actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id),FOREIGN KEY(ship_id,campaign_id) REFERENCES ship_ship(ship_id,campaign_id),
 FOREIGN KEY(trader_account_id,campaign_id) REFERENCES fin_account(account_id,campaign_id),FOREIGN KEY(campaign_equity_account_id,campaign_id) REFERENCES fin_account(account_id,campaign_id),
 FOREIGN KEY(cargo_container_id,campaign_id) REFERENCES inv_container(container_id,campaign_id),
 CHECK((opening_balance_minor=0 AND opening_transaction_id IS NULL) OR (opening_balance_minor>0 AND opening_transaction_id IS NOT NULL))
);
