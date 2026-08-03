INSERT INTO cmd_command_type VALUES('pay_ship_operating_expense','Pay ship operating expense');
INSERT INTO cmd_domain_event_type VALUES('ship_operating_expense_paid','Ship operating expense paid');

CREATE TABLE cmd_ship_operating_expense_receipt(
 command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
 campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
 actor_id bigint NOT NULL,
 ship_id bigint NOT NULL,
 operating_cost_code text NOT NULL REFERENCES rule_ship_operating_cost(operating_cost_code),
 quantity numeric NOT NULL CHECK(quantity>0),
 amount_minor bigint NOT NULL CHECK(amount_minor>0),
 operating_expense_id bigint NOT NULL UNIQUE REFERENCES ship_operating_expense(operating_expense_id),
 maintenance_cycle_id bigint UNIQUE,
 financial_transaction_id bigint NOT NULL UNIQUE,
 FOREIGN KEY(actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id),
 FOREIGN KEY(ship_id,campaign_id) REFERENCES ship_ship(ship_id,campaign_id),
 FOREIGN KEY(maintenance_cycle_id,ship_id,campaign_id) REFERENCES ship_maintenance_cycle(maintenance_cycle_id,ship_id,campaign_id),
 FOREIGN KEY(financial_transaction_id,campaign_id) REFERENCES fin_transaction(transaction_id,campaign_id)
);
