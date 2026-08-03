INSERT INTO cmd_command_type VALUES('pay_ship_crew','Pay ship crew');
INSERT INTO cmd_domain_event_type VALUES('ship_crew_paid','Ship crew paid');

INSERT INTO rule_ship_operating_cost(operating_cost_code,cost_kind,amount_minor,rate_basis,billing_period,source_locator_id)
SELECT 'salary-'||definition.position_code,'salary',definition.standard_monthly_salary_minor,'ship','month',definition.source_locator_id
FROM ship_crew_position_definition definition WHERE definition.standard_monthly_salary_minor IS NOT NULL
ON CONFLICT(operating_cost_code) DO NOTHING;

CREATE TABLE cmd_ship_crew_payroll_receipt(
 command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
 ship_id bigint NOT NULL,payer_actor_id bigint NOT NULL,payroll_day bigint NOT NULL,total_amount_minor bigint NOT NULL CHECK(total_amount_minor>0),
 FOREIGN KEY(ship_id,campaign_id) REFERENCES ship_ship(ship_id,campaign_id),FOREIGN KEY(payer_actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id)
);
CREATE TABLE cmd_ship_crew_payroll_line(
 command_id bigint NOT NULL REFERENCES cmd_ship_crew_payroll_receipt(command_id),line_order smallint NOT NULL CHECK(line_order>0),
 campaign_id bigint NOT NULL,crew_assignment_id bigint NOT NULL REFERENCES ship_crew_assignment(crew_assignment_id),payee_actor_id bigint NOT NULL,
 operating_cost_code text NOT NULL REFERENCES rule_ship_operating_cost(operating_cost_code),amount_minor bigint NOT NULL CHECK(amount_minor>0),
 payee_account_id bigint NOT NULL,financial_transaction_id bigint NOT NULL UNIQUE,operating_expense_id bigint NOT NULL UNIQUE,
 PRIMARY KEY(command_id,line_order),FOREIGN KEY(payee_actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id),
 FOREIGN KEY(payee_account_id,campaign_id) REFERENCES fin_account(account_id,campaign_id),
 FOREIGN KEY(financial_transaction_id,campaign_id) REFERENCES fin_transaction(transaction_id,campaign_id),
 FOREIGN KEY(operating_expense_id) REFERENCES ship_operating_expense(operating_expense_id)
);
