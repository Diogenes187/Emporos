INSERT INTO cmd_command_type VALUES('accept_freight_contract','Accept freight contract');
INSERT INTO cmd_domain_event_type VALUES('freight_contract_accepted','Freight contract accepted');
CREATE TABLE cmd_freight_contract_acceptance_receipt(
 command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
 freight_contract_id bigint NOT NULL UNIQUE,journey_id bigint NOT NULL,ship_id bigint NOT NULL,accepted_tons numeric NOT NULL CHECK(accepted_tons>0),promised_payment_credits bigint NOT NULL CHECK(promised_payment_credits=accepted_tons*1000),
 FOREIGN KEY(freight_contract_id,campaign_id) REFERENCES journey_freight_contract(freight_contract_id,campaign_id),
 FOREIGN KEY(journey_id,campaign_id) REFERENCES journey_journey(journey_id,campaign_id),FOREIGN KEY(ship_id,campaign_id) REFERENCES ship_ship(ship_id,campaign_id)
);
