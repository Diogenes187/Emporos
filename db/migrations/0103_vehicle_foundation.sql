CREATE TABLE rule_vehicle_chassis (
    chassis_code text PRIMARY KEY CHECK (
        chassis_code ~ '^[0-9A-HJ-NP-Q]$'
    ),
    displacement_tons numeric NOT NULL CHECK (displacement_tons>0),
    spaces smallint NOT NULL UNIQUE CHECK (spaces>0),
    base_price_minor bigint NOT NULL CHECK (base_price_minor>0),
    construction_hours integer NOT NULL CHECK (construction_hours>0),
    size_description text,
    example_description text,
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    CHECK (
        size_description IS NULL OR btrim(size_description)<>''
    ),
    CHECK (
        example_description IS NULL OR btrim(example_description)<>''
    )
);

INSERT INTO rule_vehicle_chassis (
    chassis_code,displacement_tons,spaces,base_price_minor,
    construction_hours,size_description,example_description,
    source_locator_id
)
SELECT source.*,locator.source_locator_id
FROM (
    VALUES
        ('1',0.1,1,1450,1,NULL::text,'8 Standard Moving Boxes'),
        ('2',0.25,3,1600,2,NULL,'Motorcycle'),
        ('3',0.5,6,1850,5,NULL,NULL),
        ('4',0.75,9,2100,7,NULL,'Compact Car'),
        ('5',1,12,2400,9,NULL,'Mid-Size Car'),
        ('6',2,24,3550,18,NULL,'Passenger Van'),
        ('7',3,36,4850,27,'20-ft','Standard Freight Shipping Container (1CC)'),
        ('8',4,48,6250,36,NULL,'Air/Raft'),
        ('9',5,60,7800,45,NULL,'Military Tank'),
        ('A',6,72,9550,54,NULL,'Speeder'),
        ('B',7,84,11350,63,NULL,NULL),
        ('C',8,96,13350,72,NULL,'Semi Trailer'),
        ('D',9,108,15450,81,NULL,NULL),
        ('E',10,120,17750,90,NULL,'ATV'),
        ('F',11,132,20150,99,NULL,NULL),
        ('G',12,144,22650,108,NULL,NULL),
        ('H',13,156,23350,117,NULL,NULL),
        ('J',14,168,28150,126,NULL,NULL),
        ('K',15,180,31100,135,NULL,NULL),
        ('L',16,192,34200,144,NULL,NULL),
        ('M',17,204,37400,153,NULL,NULL),
        ('N',18,216,40750,162,NULL,NULL),
        ('P',19,228,44250,171,NULL,NULL),
        ('Q',20,240,47900,180,NULL,NULL)
) source(
    chassis_code,displacement_tons,spaces,base_price_minor,
    construction_hours,size_description,example_description
)
JOIN src_locator locator
  ON locator.heading_path='Vehicle Design > Vehicle Chassis';

CREATE TABLE rule_vehicle_armor (
    armor_code text PRIMARY KEY CHECK (
        armor_code ~ '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
    ),
    armor_name text NOT NULL UNIQUE CHECK (btrim(armor_name)<>''),
    minimum_tech_level smallint NOT NULL CHECK (minimum_tech_level>=0),
    base_armor smallint NOT NULL CHECK (base_armor>=0),
    additional_protection smallint NOT NULL CHECK (
        additional_protection>0
    ),
    allocation_percent smallint NOT NULL CHECK (
        allocation_percent BETWEEN 1 AND 100
    ),
    price_percent smallint NOT NULL CHECK (price_percent>0),
    maximum_armor smallint NOT NULL CHECK (maximum_armor>=base_armor),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_vehicle_armor
SELECT source.*,locator.source_locator_id
FROM (
    VALUES
        ('wood','Wood',1,1,1,5,10,5),
        ('iron','Iron',4,2,2,5,10,10),
        ('titanium-steel','Titanium Steel',7,3,3,5,10,15),
        ('crystaliron','Crystaliron',10,4,4,5,20,20),
        ('superdense','Superdense',12,5,5,5,20,25),
        ('bonded-superdense','Bonded Superdense',14,6,6,5,50,30),
        ('coherent-superdense','Coherent Superdense',17,8,8,5,50,40)
) source(
    armor_code,armor_name,minimum_tech_level,base_armor,
    additional_protection,allocation_percent,price_percent,
    maximum_armor
)
JOIN src_locator locator
  ON locator.heading_path='Vehicle Design > Vehicle Armor';

CREATE TABLE rule_vehicle_power_plant_type (
    power_plant_code text PRIMARY KEY CHECK (
        power_plant_code ~
        '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
    ),
    power_plant_name text NOT NULL UNIQUE CHECK (
        btrim(power_plant_name)<>''
    ),
    minimum_tech_level smallint NOT NULL CHECK (minimum_tech_level>=0),
    space_multiplier numeric NOT NULL CHECK (space_multiplier>0),
    price_multiplier numeric NOT NULL CHECK (price_multiplier>0),
    fuel_kind text NOT NULL CHECK (btrim(fuel_kind)<>''),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_vehicle_power_plant_type
SELECT source.*,locator.source_locator_id
FROM (
    VALUES
        ('external-combustion','External Combustion',3,15,0.20,'coal_or_wood'),
        ('internal-combustion','Internal Combustion',5,6,0.05,'hydrocarbons'),
        ('fission','Fission',6,2,2,'radioactives'),
        ('fuel-cell-closed','Fuel Cell (Closed)',7,1,1,'hydrogen'),
        ('fuel-cell-open','Fuel Cell (Open)',7,2,0.25,'hydrogen'),
        ('gas-turbine','Gas Turbine',7,1,1,'hydrocarbons'),
        ('early-fusion','Early Fusion',9,1,1,'hydrogen'),
        ('fusion','Fusion',12,0.75,1,'hydrogen'),
        ('advanced-fusion','Advanced Fusion',15,0.5,2,'hydrogen'),
        ('antimatter','Antimatter',17,1,1,'hydrogen')
) source(
    power_plant_code,power_plant_name,minimum_tech_level,
    space_multiplier,price_multiplier,fuel_kind
)
JOIN src_locator locator
  ON locator.heading_path='Vehicle Design > Vehicle Drives';

CREATE TABLE vehicle_class (
    vehicle_class_rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    class_code text NOT NULL UNIQUE CHECK (
        class_code ~ '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
    ),
    chassis_code text NOT NULL REFERENCES
        rule_vehicle_chassis(chassis_code),
    minimum_tech_level smallint NOT NULL CHECK (
        minimum_tech_level>=0
    ),
    configuration text NOT NULL CHECK (
        configuration IN ('open','closed')
    ),
    standard_design boolean NOT NULL DEFAULT false,
    armor_code text REFERENCES rule_vehicle_armor(armor_code),
    armor_rating smallint NOT NULL DEFAULT 0 CHECK (armor_rating>=0),
    hull_points smallint NOT NULL CHECK (hull_points>=0),
    structure_points smallint NOT NULL CHECK (structure_points>0),
    allocated_spaces smallint NOT NULL CHECK (allocated_spaces>=0),
    cargo_spaces smallint NOT NULL DEFAULT 0 CHECK (cargo_spaces>=0),
    construction_cost_minor bigint NOT NULL CHECK (
        construction_cost_minor>0
    ),
    construction_hours integer NOT NULL CHECK (construction_hours>0),
    source_locator_id bigint REFERENCES src_locator(source_locator_id)
);

CREATE TABLE vehicle_component_definition (
    component_rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    component_code text NOT NULL UNIQUE CHECK (
        component_code ~ '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
    ),
    component_kind text NOT NULL CHECK (
        component_kind IN (
            'power_plant','propulsion','fuel','controls',
            'communications','sensors','computer','crew_space',
            'passenger_space','cargo','weapon_mount',
            'environmental_protection','other'
        )
    ),
    minimum_tech_level smallint CHECK (minimum_tech_level>=0),
    unit_spaces numeric NOT NULL CHECK (unit_spaces>=0),
    unit_cost_minor bigint NOT NULL CHECK (unit_cost_minor>=0),
    source_locator_id bigint REFERENCES src_locator(source_locator_id)
);

CREATE TABLE vehicle_class_component (
    vehicle_class_component_id bigint
        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    vehicle_class_rule_id bigint NOT NULL REFERENCES
        vehicle_class(vehicle_class_rule_id),
    component_rule_id bigint NOT NULL REFERENCES
        vehicle_component_definition(component_rule_id),
    quantity smallint NOT NULL CHECK (quantity>0),
    rating numeric CHECK (rating>=0),
    allocated_spaces numeric NOT NULL CHECK (allocated_spaces>=0),
    display_order smallint NOT NULL CHECK (display_order>0),
    UNIQUE (vehicle_class_rule_id,display_order)
);

CREATE TABLE vehicle_vehicle (
    vehicle_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    vehicle_class_rule_id bigint NOT NULL REFERENCES
        vehicle_class(vehicle_class_rule_id),
    inventory_item_instance_id bigint NOT NULL UNIQUE,
    name text NOT NULL CHECK (btrim(name)<>''),
    registration_identifier text CHECK (
        registration_identifier IS NULL
        OR btrim(registration_identifier)<>''
    ),
    current_location_id bigint,
    lifecycle_status text NOT NULL DEFAULT 'active' CHECK (
        lifecycle_status IN (
            'building','active','disabled','destroyed','scrapped'
        )
    ),
    hull_current smallint NOT NULL CHECK (hull_current>=0),
    structure_current smallint NOT NULL CHECK (structure_current>=0),
    commissioned_at timestamptz,
    ended_at timestamptz,
    concurrency_version bigint NOT NULL DEFAULT 1 CHECK (
        concurrency_version>0
    ),
    UNIQUE (vehicle_id,campaign_id),
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

CREATE UNIQUE INDEX vehicle_registration_per_campaign
    ON vehicle_vehicle(campaign_id,registration_identifier)
    WHERE registration_identifier IS NOT NULL;

CREATE TABLE vehicle_component (
    vehicle_component_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    vehicle_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    class_component_id bigint REFERENCES
        vehicle_class_component(vehicle_class_component_id),
    component_rule_id bigint NOT NULL REFERENCES
        vehicle_component_definition(component_rule_id),
    component_identifier text NOT NULL CHECK (
        btrim(component_identifier)<>''
    ),
    operational_status text NOT NULL DEFAULT 'operational' CHECK (
        operational_status IN (
            'operational','degraded','disabled','destroyed','removed'
        )
    ),
    installed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    removed_at timestamptz,
    FOREIGN KEY (vehicle_id,campaign_id)
        REFERENCES vehicle_vehicle(vehicle_id,campaign_id),
    UNIQUE (vehicle_component_id,vehicle_id,campaign_id),
    UNIQUE (vehicle_id,component_identifier),
    CHECK (
        (operational_status='removed' AND removed_at IS NOT NULL)
        OR (operational_status<>'removed' AND removed_at IS NULL)
    )
);

CREATE TABLE vehicle_crew_station (
    crew_station_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    vehicle_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    station_identifier text NOT NULL CHECK (
        btrim(station_identifier)<>''
    ),
    station_kind text NOT NULL CHECK (
        station_kind IN (
            'driver','pilot','commander','gunner',
            'engineer','operator','other'
        )
    ),
    station_status text NOT NULL DEFAULT 'available' CHECK (
        station_status IN ('available','disabled','removed')
    ),
    FOREIGN KEY (vehicle_id,campaign_id)
        REFERENCES vehicle_vehicle(vehicle_id,campaign_id),
    UNIQUE (crew_station_id,vehicle_id,campaign_id),
    UNIQUE (vehicle_id,station_identifier)
);

CREATE TABLE vehicle_crew_assignment (
    crew_assignment_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    crew_station_id bigint NOT NULL,
    vehicle_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    actor_id bigint NOT NULL,
    duty_status text NOT NULL DEFAULT 'active' CHECK (
        duty_status IN ('active','relieved','absent','ended')
    ),
    effective_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    ended_at timestamptz,
    source_command_id bigint REFERENCES cmd_command(command_id),
    FOREIGN KEY (crew_station_id,vehicle_id,campaign_id)
        REFERENCES vehicle_crew_station(
            crew_station_id,vehicle_id,campaign_id
        ),
    FOREIGN KEY (actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    CHECK (
        (duty_status='active' AND ended_at IS NULL)
        OR (duty_status<>'active' AND ended_at IS NOT NULL)
    )
);

CREATE UNIQUE INDEX vehicle_one_active_actor_per_station
    ON vehicle_crew_assignment(crew_station_id)
    WHERE duty_status='active';

CREATE UNIQUE INDEX vehicle_actor_one_active_station
    ON vehicle_crew_assignment(actor_id,vehicle_id)
    WHERE duty_status='active';

CREATE TABLE vehicle_resource (
    vehicle_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    resource_kind text NOT NULL CHECK (
        resource_kind IN (
            'fuel','power','life_support','ammunition','other'
        )
    ),
    resource_identifier text NOT NULL CHECK (
        btrim(resource_identifier)<>''
    ),
    current_quantity numeric NOT NULL CHECK (current_quantity>=0),
    capacity_quantity numeric NOT NULL CHECK (capacity_quantity>=0),
    quantity_unit text NOT NULL CHECK (
        quantity_unit IN (
            'litre','kilogram','energy_point',
            'person_hour','round','unit'
        )
    ),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (vehicle_id,resource_identifier),
    FOREIGN KEY (vehicle_id,campaign_id)
        REFERENCES vehicle_vehicle(vehicle_id,campaign_id),
    CHECK (current_quantity<=capacity_quantity)
);

CREATE TABLE vehicle_damage (
    vehicle_damage_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    vehicle_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    target_kind text NOT NULL CHECK (
        target_kind IN ('hull','structure','component','crew_station')
    ),
    vehicle_component_id bigint,
    crew_station_id bigint,
    damage_points smallint NOT NULL CHECK (damage_points>0),
    damage_status text NOT NULL DEFAULT 'unrepaired' CHECK (
        damage_status IN ('unrepaired','temporarily_restored','repaired')
    ),
    description text NOT NULL CHECK (btrim(description)<>''),
    source_command_id bigint REFERENCES cmd_command(command_id),
    incurred_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    repaired_at timestamptz,
    FOREIGN KEY (vehicle_id,campaign_id)
        REFERENCES vehicle_vehicle(vehicle_id,campaign_id),
    FOREIGN KEY (vehicle_component_id,vehicle_id,campaign_id)
        REFERENCES vehicle_component(
            vehicle_component_id,vehicle_id,campaign_id
        ),
    FOREIGN KEY (crew_station_id,vehicle_id,campaign_id)
        REFERENCES vehicle_crew_station(
            crew_station_id,vehicle_id,campaign_id
        ),
    CHECK (
        (target_kind='component'
         AND vehicle_component_id IS NOT NULL
         AND crew_station_id IS NULL)
        OR
        (target_kind='crew_station'
         AND vehicle_component_id IS NULL
         AND crew_station_id IS NOT NULL)
        OR
        (target_kind IN ('hull','structure')
         AND vehicle_component_id IS NULL
         AND crew_station_id IS NULL)
    ),
    CHECK (
        (damage_status='repaired' AND repaired_at IS NOT NULL)
        OR (damage_status<>'repaired' AND repaired_at IS NULL)
    )
);

CREATE TABLE vehicle_operational_control (
    operational_control_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    vehicle_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    actor_id bigint,
    faction_id bigint,
    control_basis text NOT NULL CHECK (
        control_basis IN (
            'owner','assigned','lease','requisition',
            'seizure','theft','other'
        )
    ),
    effective_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    ended_at timestamptz,
    source_command_id bigint REFERENCES cmd_command(command_id),
    FOREIGN KEY (vehicle_id,campaign_id)
        REFERENCES vehicle_vehicle(vehicle_id,campaign_id),
    FOREIGN KEY (actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    FOREIGN KEY (faction_id,campaign_id)
        REFERENCES actor_faction(faction_id,campaign_id),
    CHECK (num_nonnulls(actor_id,faction_id)=1),
    CHECK (ended_at IS NULL OR ended_at>=effective_at)
);

CREATE UNIQUE INDEX vehicle_one_active_operational_controller
    ON vehicle_operational_control(vehicle_id)
    WHERE ended_at IS NULL;

CREATE OR REPLACE FUNCTION vehicle_validate_instance_state()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    class_hull smallint;
    class_structure smallint;
BEGIN
    SELECT hull_points,structure_points
    INTO class_hull,class_structure
    FROM vehicle_class
    WHERE vehicle_class_rule_id=NEW.vehicle_class_rule_id;
    IF NEW.hull_current>class_hull
       OR NEW.structure_current>class_structure THEN
        RAISE EXCEPTION 'Vehicle state exceeds class maxima'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER vehicle_instance_state_within_class
BEFORE INSERT OR UPDATE OF vehicle_class_rule_id,
    hull_current,structure_current
ON vehicle_vehicle
FOR EACH ROW EXECUTE FUNCTION vehicle_validate_instance_state();

CREATE OR REPLACE FUNCTION vehicle_validate_class_capacity()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    chassis_spaces smallint;
    armor_maximum smallint;
BEGIN
    SELECT spaces INTO chassis_spaces
    FROM rule_vehicle_chassis
    WHERE chassis_code=NEW.chassis_code;
    IF NEW.allocated_spaces+NEW.cargo_spaces>chassis_spaces THEN
        RAISE EXCEPTION 'Vehicle design exceeds chassis spaces'
            USING ERRCODE='23514';
    END IF;
    IF NEW.armor_code IS NOT NULL THEN
        SELECT maximum_armor INTO armor_maximum
        FROM rule_vehicle_armor
        WHERE armor_code=NEW.armor_code;
        IF NEW.armor_rating>armor_maximum THEN
            RAISE EXCEPTION 'Vehicle armor exceeds material maximum'
                USING ERRCODE='23514';
        END IF;
    ELSIF NEW.armor_rating<>0 THEN
        RAISE EXCEPTION 'Vehicle armor rating requires armor material'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER vehicle_class_capacity_valid
BEFORE INSERT OR UPDATE ON vehicle_class
FOR EACH ROW EXECUTE FUNCTION vehicle_validate_class_capacity();

CREATE OR REPLACE FUNCTION vehicle_validate_component_allocation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    design_capacity numeric;
    already_allocated numeric;
BEGIN
    PERFORM 1
    FROM vehicle_class
    WHERE vehicle_class_rule_id=NEW.vehicle_class_rule_id
    FOR UPDATE;
    SELECT allocated_spaces INTO design_capacity
    FROM vehicle_class
    WHERE vehicle_class_rule_id=NEW.vehicle_class_rule_id;
    SELECT coalesce(sum(allocated_spaces),0)
    INTO already_allocated
    FROM vehicle_class_component
    WHERE vehicle_class_rule_id=NEW.vehicle_class_rule_id
      AND vehicle_class_component_id<>
          coalesce(NEW.vehicle_class_component_id,0);
    IF already_allocated+NEW.allocated_spaces>design_capacity THEN
        RAISE EXCEPTION
            'Vehicle components exceed design allocation'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER vehicle_component_allocation_valid
BEFORE INSERT OR UPDATE ON vehicle_class_component
FOR EACH ROW EXECUTE FUNCTION
    vehicle_validate_component_allocation();

CREATE OR REPLACE FUNCTION vehicle_validate_installed_component()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    instance_class bigint;
    declared_class bigint;
    declared_component bigint;
BEGIN
    IF NEW.class_component_id IS NULL THEN
        RETURN NEW;
    END IF;
    SELECT vehicle_class_rule_id INTO instance_class
    FROM vehicle_vehicle
    WHERE vehicle_id=NEW.vehicle_id
      AND campaign_id=NEW.campaign_id;
    SELECT vehicle_class_rule_id,component_rule_id
    INTO declared_class,declared_component
    FROM vehicle_class_component
    WHERE vehicle_class_component_id=NEW.class_component_id;
    IF instance_class<>declared_class
       OR NEW.component_rule_id<>declared_component THEN
        RAISE EXCEPTION
            'Installed component disagrees with vehicle class'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER vehicle_installed_component_valid
BEFORE INSERT OR UPDATE ON vehicle_component
FOR EACH ROW EXECUTE FUNCTION
    vehicle_validate_installed_component();
