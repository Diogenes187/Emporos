CREATE TABLE ship_class (
    ship_class_rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    class_code text NOT NULL UNIQUE CHECK (
        class_code ~ '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
    ),
    hull_tons numeric NOT NULL CHECK (hull_tons>0),
    hull_points smallint NOT NULL CHECK (hull_points>0),
    structure_points smallint NOT NULL CHECK (structure_points>0),
    minimum_tech_level smallint NOT NULL CHECK (minimum_tech_level>=0),
    construction_cost_minor bigint NOT NULL CHECK (
        construction_cost_minor>0
    ),
    jump_rating smallint NOT NULL DEFAULT 0 CHECK (jump_rating>=0),
    maneuver_rating smallint NOT NULL DEFAULT 0 CHECK (
        maneuver_rating>=0
    ),
    power_rating smallint NOT NULL DEFAULT 0 CHECK (power_rating>=0),
    cargo_capacity_tons numeric NOT NULL DEFAULT 0 CHECK (
        cargo_capacity_tons>=0
    )
);

CREATE TABLE ship_class_characteristic (
    ship_class_rule_id bigint NOT NULL REFERENCES
        ship_class(ship_class_rule_id),
    characteristic_code text NOT NULL CHECK (
        characteristic_code IN (
            'armor','computer','sensors','fuel_tons',
            'staterooms','low_berths','hardpoints'
        )
    ),
    characteristic_value numeric NOT NULL CHECK (
        characteristic_value>=0
    ),
    PRIMARY KEY (ship_class_rule_id,characteristic_code)
);

CREATE TABLE ship_component_definition (
    component_rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    component_code text NOT NULL UNIQUE CHECK (
        component_code ~ '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
    ),
    component_kind text NOT NULL CHECK (
        component_kind IN (
            'bridge','computer','sensor','jump_drive','maneuver_drive',
            'power_plant','fuel_tank','stateroom','low_berth',
            'cargo_hold','weapon_mount','fuel_processor',
            'fuel_scoop','other'
        )
    ),
    minimum_tech_level smallint CHECK (minimum_tech_level>=0),
    unit_tons numeric NOT NULL CHECK (unit_tons>=0),
    unit_cost_minor bigint NOT NULL CHECK (unit_cost_minor>=0)
);

CREATE TABLE ship_class_component (
    ship_class_component_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ship_class_rule_id bigint NOT NULL REFERENCES
        ship_class(ship_class_rule_id),
    component_rule_id bigint NOT NULL REFERENCES
        ship_component_definition(component_rule_id),
    quantity smallint NOT NULL CHECK (quantity>0),
    rating numeric CHECK (rating>=0),
    allocated_tons numeric NOT NULL CHECK (allocated_tons>=0),
    display_order smallint NOT NULL CHECK (display_order>0),
    UNIQUE (ship_class_rule_id,display_order),
    UNIQUE (ship_class_rule_id,component_rule_id,display_order)
);

CREATE TABLE ship_weapon_definition (
    weapon_rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    weapon_code text NOT NULL UNIQUE CHECK (
        weapon_code ~ '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
    ),
    weapon_kind text NOT NULL CHECK (
        weapon_kind IN (
            'laser','missile','sandcaster','particle','plasma','other'
        )
    ),
    damage_dice_count smallint NOT NULL CHECK (damage_dice_count>0),
    damage_die_sides smallint NOT NULL CHECK (damage_die_sides>1),
    damage_modifier smallint NOT NULL DEFAULT 0,
    ammunition_per_attack smallint NOT NULL DEFAULT 0 CHECK (
        ammunition_per_attack>=0
    )
);

CREATE TABLE ship_class_weapon (
    ship_class_weapon_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ship_class_rule_id bigint NOT NULL REFERENCES
        ship_class(ship_class_rule_id),
    weapon_rule_id bigint NOT NULL REFERENCES
        ship_weapon_definition(weapon_rule_id),
    mount_identifier text NOT NULL CHECK (btrim(mount_identifier)<>''),
    quantity smallint NOT NULL CHECK (quantity>0),
    fire_control_tons numeric NOT NULL DEFAULT 0 CHECK (
        fire_control_tons>=0
    ),
    UNIQUE (ship_class_rule_id,mount_identifier)
);

CREATE TABLE ship_crew_position_definition (
    crew_position_rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    position_code text NOT NULL UNIQUE CHECK (
        position_code ~ '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
    ),
    position_name text NOT NULL UNIQUE CHECK (btrim(position_name)<>''),
    governing_skill_rule_id bigint REFERENCES rule_skill(rule_id),
    standard_monthly_salary_minor bigint CHECK (
        standard_monthly_salary_minor>=0
    )
);

CREATE TABLE ship_class_crew_position (
    ship_class_crew_position_id bigint
        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ship_class_rule_id bigint NOT NULL REFERENCES
        ship_class(ship_class_rule_id),
    crew_position_rule_id bigint NOT NULL REFERENCES
        ship_crew_position_definition(crew_position_rule_id),
    position_count smallint NOT NULL CHECK (position_count>0),
    required boolean NOT NULL,
    UNIQUE (ship_class_rule_id,crew_position_rule_id)
);

CREATE TABLE ship_resource_type (
    resource_type_code text PRIMARY KEY CHECK (
        resource_type_code IN (
            'refined_fuel','unrefined_fuel','power',
            'life_support','missiles','sand','other'
        )
    ),
    quantity_unit text NOT NULL CHECK (
        quantity_unit IN (
            'ton','energy_point','person_hour','round','unit'
        )
    )
);

INSERT INTO ship_resource_type VALUES
    ('refined_fuel','ton'),('unrefined_fuel','ton'),
    ('power','energy_point'),('life_support','person_hour'),
    ('missiles','round'),('sand','round'),('other','unit');

CREATE TABLE ship_ship (
    ship_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    ship_class_rule_id bigint NOT NULL REFERENCES
        ship_class(ship_class_rule_id),
    inventory_item_instance_id bigint NOT NULL,
    name text NOT NULL CHECK (btrim(name)<>''),
    registration_identifier text CHECK (
        registration_identifier IS NULL
        OR btrim(registration_identifier)<>''
    ),
    lifecycle_status text NOT NULL DEFAULT 'active' CHECK (
        lifecycle_status IN (
            'building','active','laid_up','derelict',
            'destroyed','scrapped'
        )
    ),
    legal_status text NOT NULL DEFAULT 'registered' CHECK (
        legal_status IN (
            'registered','unregistered','impounded','stolen','unknown'
        )
    ),
    current_location_id bigint,
    hull_current smallint NOT NULL CHECK (hull_current>=0),
    structure_current smallint NOT NULL CHECK (structure_current>=0),
    commissioned_at timestamptz,
    ended_at timestamptz,
    concurrency_version bigint NOT NULL DEFAULT 1 CHECK (
        concurrency_version>0
    ),
    UNIQUE (ship_id,campaign_id),
    UNIQUE (inventory_item_instance_id),
    FOREIGN KEY (inventory_item_instance_id,campaign_id)
        REFERENCES inv_item_instance(item_instance_id,campaign_id),
    FOREIGN KEY (current_location_id,campaign_id)
        REFERENCES loc_location(location_id,campaign_id),
    CHECK (
        (lifecycle_status IN ('destroyed','scrapped')
         AND ended_at IS NOT NULL)
        OR (lifecycle_status NOT IN ('destroyed','scrapped')
            AND ended_at IS NULL)
    )
);

CREATE UNIQUE INDEX ship_registration_per_campaign
    ON ship_ship(campaign_id,registration_identifier)
    WHERE registration_identifier IS NOT NULL;

CREATE TABLE ship_component (
    ship_component_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ship_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    class_component_id bigint REFERENCES
        ship_class_component(ship_class_component_id),
    component_rule_id bigint NOT NULL REFERENCES
        ship_component_definition(component_rule_id),
    component_identifier text NOT NULL CHECK (
        btrim(component_identifier)<>''
    ),
    rating numeric CHECK (rating>=0),
    operational_status text NOT NULL DEFAULT 'operational' CHECK (
        operational_status IN (
            'operational','degraded','disabled','destroyed','removed'
        )
    ),
    permanent_damage_points smallint NOT NULL DEFAULT 0 CHECK (
        permanent_damage_points>=0
    ),
    installed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    removed_at timestamptz,
    FOREIGN KEY (ship_id,campaign_id)
        REFERENCES ship_ship(ship_id,campaign_id),
    UNIQUE (ship_component_id,campaign_id),
    UNIQUE (ship_id,component_identifier),
    CHECK (
        (operational_status='removed' AND removed_at IS NOT NULL)
        OR (operational_status<>'removed' AND removed_at IS NULL)
    )
);

CREATE TABLE ship_resource (
    ship_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    resource_type_code text NOT NULL REFERENCES
        ship_resource_type(resource_type_code),
    current_quantity numeric NOT NULL CHECK (current_quantity>=0),
    capacity_quantity numeric NOT NULL CHECK (capacity_quantity>=0),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    source_command_id bigint REFERENCES cmd_command(command_id),
    PRIMARY KEY (ship_id,resource_type_code),
    FOREIGN KEY (ship_id,campaign_id)
        REFERENCES ship_ship(ship_id,campaign_id),
    CHECK (current_quantity<=capacity_quantity)
);

CREATE TABLE ship_crew_position (
    ship_crew_position_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ship_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    crew_position_rule_id bigint NOT NULL REFERENCES
        ship_crew_position_definition(crew_position_rule_id),
    position_identifier text NOT NULL CHECK (
        btrim(position_identifier)<>''
    ),
    position_status text NOT NULL DEFAULT 'available' CHECK (
        position_status IN ('available','disabled','removed')
    ),
    FOREIGN KEY (ship_id,campaign_id)
        REFERENCES ship_ship(ship_id,campaign_id),
    UNIQUE (ship_crew_position_id,ship_id,campaign_id),
    UNIQUE (ship_id,position_identifier)
);

CREATE TABLE ship_crew_assignment (
    crew_assignment_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ship_crew_position_id bigint NOT NULL,
    ship_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    actor_id bigint NOT NULL,
    duty_status text NOT NULL DEFAULT 'active' CHECK (
        duty_status IN ('active','relieved','absent','ended')
    ),
    effective_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    ended_at timestamptz,
    source_command_id bigint REFERENCES cmd_command(command_id),
    FOREIGN KEY (ship_crew_position_id,ship_id,campaign_id)
        REFERENCES ship_crew_position(
            ship_crew_position_id,ship_id,campaign_id
        ),
    FOREIGN KEY (actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    CHECK (
        (duty_status='active' AND ended_at IS NULL)
        OR (duty_status<>'active' AND ended_at IS NOT NULL)
    )
);

CREATE UNIQUE INDEX ship_one_active_crew_per_position
    ON ship_crew_assignment(ship_crew_position_id)
    WHERE duty_status='active';

CREATE UNIQUE INDEX ship_actor_one_active_position_per_ship
    ON ship_crew_assignment(actor_id,ship_id)
    WHERE duty_status='active';

CREATE TABLE ship_deck_location (
    ship_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    location_id bigint NOT NULL,
    deck_order smallint NOT NULL CHECK (deck_order>0),
    compartment_identifier text NOT NULL CHECK (
        btrim(compartment_identifier)<>''
    ),
    PRIMARY KEY (ship_id,location_id),
    FOREIGN KEY (ship_id,campaign_id)
        REFERENCES ship_ship(ship_id,campaign_id),
    FOREIGN KEY (location_id,campaign_id)
        REFERENCES loc_location(location_id,campaign_id),
    UNIQUE (ship_id,deck_order,compartment_identifier)
);
