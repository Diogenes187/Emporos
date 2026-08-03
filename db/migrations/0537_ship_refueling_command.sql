INSERT INTO cmd_command_type VALUES('refuel_ship','Refuel ship');
INSERT INTO cmd_domain_event_type VALUES('ship_refueled','Ship refueled');

CREATE TABLE cmd_ship_refueling_receipt(
 command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
 campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
 actor_id bigint NOT NULL,
 ship_id bigint NOT NULL,
 location_id bigint NOT NULL,
 fuel_type_code text NOT NULL REFERENCES rule_fuel_type(fuel_type_code),
 resource_type_code text NOT NULL CHECK(resource_type_code IN('refined_fuel','unrefined_fuel')),
 fuel_source text NOT NULL CHECK(fuel_source IN('starport','water','gas_giant','processor','other')),
 tons_acquired numeric NOT NULL CHECK(tons_acquired>0),
 unit_price_minor bigint NOT NULL CHECK(unit_price_minor>=0),
 total_price_minor bigint NOT NULL CHECK(total_price_minor=tons_acquired*unit_price_minor),
 quantity_after numeric NOT NULL CHECK(quantity_after>=0),
 financial_transaction_id bigint,
 FOREIGN KEY(actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id),
 FOREIGN KEY(ship_id,campaign_id) REFERENCES ship_ship(ship_id,campaign_id),
 FOREIGN KEY(location_id,campaign_id) REFERENCES loc_location(location_id,campaign_id),
 FOREIGN KEY(financial_transaction_id,campaign_id) REFERENCES fin_transaction(transaction_id,campaign_id),
 CHECK((total_price_minor=0 AND financial_transaction_id IS NULL) OR
       (total_price_minor>0 AND financial_transaction_id IS NOT NULL))
);
