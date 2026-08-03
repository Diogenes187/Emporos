INSERT INTO cmd_command_type VALUES
    ('acquire_ship','Acquire ship');

INSERT INTO cmd_domain_event_type VALUES
    ('ship_acquired','Ship acquired');

ALTER TABLE inv_item_definition
    DROP CONSTRAINT inv_item_definition_item_kind_check,
    ADD CONSTRAINT inv_item_definition_item_kind_check CHECK (
        item_kind IN ('weapon','armor','equipment','ship')
    );

INSERT INTO inv_item_definition
    (rule_id,item_kind,minimum_tech_level,cost_credits,mass_grams)
SELECT ship_class_rule_id,'ship',minimum_tech_level,NULL,NULL
  FROM ship_class
ON CONFLICT (rule_id) DO NOTHING;

CREATE TABLE cmd_ship_acquisition_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    ship_id bigint NOT NULL UNIQUE,
    owner_actor_id bigint NOT NULL,
    inventory_item_instance_id bigint NOT NULL UNIQUE,
    ship_class_rule_id bigint NOT NULL REFERENCES ship_class(ship_class_rule_id),
    ship_name text NOT NULL CHECK (btrim(ship_name)<>''),
    registration_identifier text,
    component_count smallint NOT NULL CHECK (component_count>=0),
    crew_position_count smallint NOT NULL CHECK (crew_position_count>=0),
    resource_count smallint NOT NULL CHECK (resource_count>=0),
    ship_version_after bigint NOT NULL CHECK (ship_version_after=1),
    FOREIGN KEY (ship_id,campaign_id) REFERENCES ship_ship(ship_id,campaign_id),
    FOREIGN KEY (owner_actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    FOREIGN KEY (inventory_item_instance_id,campaign_id)
        REFERENCES inv_item_instance(item_instance_id,campaign_id)
);

COMMENT ON TABLE cmd_ship_acquisition_receipt IS
    'Audited, atomic creation of an inventory-backed vessel and its initial operational state.';
