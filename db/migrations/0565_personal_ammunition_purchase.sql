INSERT INTO cmd_command_type VALUES
    ('purchase_personal_ammunition','Purchase one source-defined ammunition reload unit');

INSERT INTO cmd_domain_event_type VALUES
    ('personal_ammunition_purchased','Personal ammunition purchased');

CREATE TABLE cmd_personal_ammunition_purchase_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    actor_id bigint NOT NULL,
    weapon_rule_id bigint NOT NULL REFERENCES inv_weapon_definition(item_rule_id),
    ammunition_rule_id bigint NOT NULL REFERENCES inv_ammunition_definition(ammunition_rule_id),
    payer_account_id bigint NOT NULL REFERENCES fin_account(account_id),
    reload_units_purchased smallint NOT NULL CHECK (reload_units_purchased>0),
    unit_price_minor bigint NOT NULL CHECK (unit_price_minor>=0),
    total_price_minor bigint NOT NULL CHECK (total_price_minor=unit_price_minor*reload_units_purchased),
    financial_transaction_id bigint REFERENCES fin_transaction(transaction_id),
    supply_after smallint NOT NULL CHECK (supply_after>=0),
    FOREIGN KEY (actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id),
    CHECK ((total_price_minor=0)=(financial_transaction_id IS NULL))
);
