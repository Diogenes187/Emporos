INSERT INTO cmd_command_type VALUES
    ('purchase_personal_equipment','Purchase one catalogued personal item');

INSERT INTO cmd_domain_event_type VALUES
    ('personal_equipment_purchased','Personal equipment purchased');

CREATE TABLE cmd_personal_equipment_purchase_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    actor_id bigint NOT NULL,
    item_rule_id bigint NOT NULL REFERENCES inv_item_definition(rule_id),
    item_instance_id bigint NOT NULL UNIQUE,
    container_id bigint NOT NULL,
    payer_account_id bigint NOT NULL REFERENCES fin_account(account_id),
    unit_price_minor bigint NOT NULL CHECK (unit_price_minor >= 0),
    financial_transaction_id bigint REFERENCES fin_transaction(transaction_id),
    inventory_transfer_id bigint NOT NULL REFERENCES inv_transfer(transfer_id),
    FOREIGN KEY (actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    FOREIGN KEY (item_instance_id,campaign_id)
        REFERENCES inv_item_instance(item_instance_id,campaign_id),
    FOREIGN KEY (container_id,campaign_id)
        REFERENCES inv_container(container_id,campaign_id),
    CHECK ((unit_price_minor=0)=(financial_transaction_id IS NULL))
);
