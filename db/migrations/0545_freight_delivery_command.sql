INSERT INTO cmd_command_type VALUES('deliver_freight_contract','Deliver freight contract');
INSERT INTO cmd_domain_event_type VALUES('freight_contract_delivered','Freight contract delivered');
CREATE TABLE cmd_freight_delivery_receipt(
 command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
 freight_contract_id bigint NOT NULL UNIQUE,actor_id bigint NOT NULL,financial_transaction_id bigint NOT NULL UNIQUE,balance_after_minor bigint NOT NULL,
 FOREIGN KEY(freight_contract_id,campaign_id) REFERENCES journey_freight_contract(freight_contract_id,campaign_id),
 FOREIGN KEY(actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id),FOREIGN KEY(financial_transaction_id,campaign_id) REFERENCES fin_transaction(transaction_id,campaign_id)
);
