ALTER TABLE vehicle_class_component
    ADD COLUMN published_cost_minor bigint NOT NULL DEFAULT 0 CHECK (
        published_cost_minor>=0
    ),
    ADD COLUMN calculation_status text NOT NULL
        DEFAULT 'matches' CHECK (
            calculation_status IN (
                'matches','formula','published_override'
            )
        ),
    ADD COLUMN tech_level_status text NOT NULL
        DEFAULT 'matches' CHECK (
            tech_level_status IN (
                'matches','published_override'
            )
        ),
    ADD COLUMN source_locator_id bigint REFERENCES
        src_locator(source_locator_id),
    ADD CONSTRAINT vehicle_class_component_unique
        UNIQUE (vehicle_class_rule_id,component_rule_id);

CREATE OR REPLACE FUNCTION vehicle_validate_component_allocation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    class_tech smallint;
    design_capacity numeric;
    already_allocated numeric;
    component_tech smallint;
    unit_spaces numeric;
    unit_cost bigint;
    formula rule_vehicle_component_formula%ROWTYPE;
    increments numeric;
    expected_spaces numeric;
    expected_cost numeric;
BEGIN
    SELECT minimum_tech_level,allocated_spaces
    INTO class_tech,design_capacity
    FROM vehicle_class
    WHERE vehicle_class_rule_id=NEW.vehicle_class_rule_id
    FOR UPDATE;
    SELECT definition.minimum_tech_level,
           definition.unit_spaces,definition.unit_cost_minor
    INTO component_tech,unit_spaces,unit_cost
    FROM vehicle_component_definition definition
    WHERE definition.component_rule_id=NEW.component_rule_id;
    SELECT coalesce(sum(allocated_spaces),0)
    INTO already_allocated
    FROM vehicle_class_component
    WHERE vehicle_class_rule_id=NEW.vehicle_class_rule_id
      AND vehicle_class_component_id<>
          coalesce(NEW.vehicle_class_component_id,0);
    IF already_allocated+NEW.allocated_spaces>design_capacity
       OR (
           component_tech IS NOT NULL
           AND class_tech<component_tech
           AND NEW.tech_level_status='matches'
       )
       OR (
           component_tech IS NOT NULL
           AND class_tech>=component_tech
           AND NEW.tech_level_status='published_override'
       ) THEN
        RAISE EXCEPTION
            'Vehicle component exceeds class capacity or tech level'
            USING ERRCODE='23514';
    END IF;
    IF NEW.calculation_status='matches'
       AND (
           NEW.allocated_spaces<>unit_spaces*NEW.quantity
           OR NEW.published_cost_minor<>unit_cost*NEW.quantity
       ) THEN
        RAISE EXCEPTION
            'Vehicle component does not match fixed catalogue values'
            USING ERRCODE='23514';
    ELSIF NEW.calculation_status='formula' THEN
        SELECT * INTO formula
        FROM rule_vehicle_component_formula
        WHERE component_rule_id=NEW.component_rule_id;
        IF NOT FOUND OR NEW.rating IS NULL THEN
            RAISE EXCEPTION
                'Formula component requires a rating and formula'
                USING ERRCODE='23514';
        END IF;
        increments=CASE formula.increment_rounding
            WHEN 'ceiling' THEN ceil(
                NEW.rating/formula.basis_units_per_increment
            )
            WHEN 'floor' THEN floor(
                NEW.rating/formula.basis_units_per_increment
            )
            ELSE NEW.rating/formula.basis_units_per_increment
        END;
        expected_spaces=(
            formula.base_spaces+
            formula.spaces_per_increment*increments
        )*NEW.quantity;
        expected_cost=(
            formula.base_cost_minor+
            formula.cost_per_basis_unit_minor*NEW.rating+
            formula.cost_per_allocated_space_minor*expected_spaces+
            formula.cost_per_increment_minor*increments
        )*NEW.quantity;
        IF NEW.allocated_spaces<>expected_spaces
           OR NEW.published_cost_minor<>expected_cost THEN
            RAISE EXCEPTION
                'Vehicle formula component calculation is inconsistent'
                USING ERRCODE='23514';
        END IF;
    ELSIF NEW.calculation_status='published_override'
          AND NEW.allocated_spaces=unit_spaces*NEW.quantity
          AND NEW.published_cost_minor=unit_cost*NEW.quantity THEN
        RAISE EXCEPTION
            'Published override must differ from fixed catalogue values'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TABLE vehicle_class_configuration_option (
    vehicle_class_rule_id bigint NOT NULL REFERENCES
        vehicle_class(vehicle_class_rule_id),
    option_rule_id bigint NOT NULL REFERENCES
        rule_vehicle_configuration_option(option_rule_id),
    allocated_spaces numeric NOT NULL CHECK (allocated_spaces>=0),
    published_cost_minor bigint NOT NULL CHECK (
        published_cost_minor>=0
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    PRIMARY KEY (vehicle_class_rule_id,option_rule_id)
);

CREATE TABLE vehicle_class_drive_option (
    vehicle_class_rule_id bigint NOT NULL REFERENCES
        vehicle_class(vehicle_class_rule_id),
    option_rule_id bigint NOT NULL REFERENCES
        rule_vehicle_drive_option(option_rule_id),
    option_steps smallint NOT NULL DEFAULT 1 CHECK (
        option_steps>0
    ),
    published_cost_minor bigint NOT NULL CHECK (
        published_cost_minor>=0
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    PRIMARY KEY (vehicle_class_rule_id,option_rule_id)
);

CREATE TABLE vehicle_class_autopilot (
    vehicle_class_rule_id bigint PRIMARY KEY REFERENCES
        vehicle_class(vehicle_class_rule_id),
    vehicle_category text NOT NULL REFERENCES
        rule_vehicle_autopilot_introduction(vehicle_category),
    skill_rule_id bigint NOT NULL REFERENCES rule_skill(rule_id),
    skill_level smallint NOT NULL CHECK (
        skill_level BETWEEN 0 AND 3
    ),
    published_cost_minor bigint NOT NULL CHECK (
        published_cost_minor>=0
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

CREATE OR REPLACE FUNCTION vehicle_validate_class_autopilot()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    class_tech smallint;
    introduction_tech smallint;
    formula rule_vehicle_autopilot_formula%ROWTYPE;
    expected_level smallint;
    expected_cost bigint;
BEGIN
    SELECT minimum_tech_level INTO class_tech
    FROM vehicle_class
    WHERE vehicle_class_rule_id=NEW.vehicle_class_rule_id;
    SELECT minimum_tech_level INTO introduction_tech
    FROM rule_vehicle_autopilot_introduction introduction
    WHERE introduction.vehicle_category=NEW.vehicle_category;
    SELECT definition.* INTO formula
    FROM rule_vehicle_autopilot_introduction introduction
    JOIN rule_vehicle_autopilot_formula definition
      USING (formula_code)
    WHERE introduction.vehicle_category=NEW.vehicle_category;
    expected_level=least(
        formula.maximum_skill_level,
        formula.base_skill_level+
        floor(
            (class_tech-introduction_tech)/
            formula.tech_levels_per_skill_level
        )
    );
    expected_cost=formula.base_price_minor+
        formula.price_per_skill_level_minor*expected_level;
    IF class_tech<introduction_tech
       OR NEW.skill_level<>expected_level
       OR NEW.published_cost_minor<>expected_cost THEN
        RAISE EXCEPTION
            'Vehicle autopilot conflicts with introduction formula'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER vehicle_class_autopilot_valid
BEFORE INSERT OR UPDATE ON vehicle_class_autopilot
FOR EACH ROW EXECUTE FUNCTION vehicle_validate_class_autopilot();

CREATE TABLE vehicle_class_computer_option (
    vehicle_class_rule_id bigint NOT NULL REFERENCES
        vehicle_class(vehicle_class_rule_id),
    option_code text NOT NULL REFERENCES
        rule_vehicle_computer_option(option_code),
    published_incremental_cost_minor bigint NOT NULL CHECK (
        published_incremental_cost_minor>=0
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    PRIMARY KEY (vehicle_class_rule_id,option_code)
);

CREATE TABLE vehicle_class_fuel_tank (
    vehicle_class_rule_id bigint PRIMARY KEY REFERENCES
        vehicle_class(vehicle_class_rule_id),
    power_plant_code text NOT NULL,
    fuel_kind text NOT NULL,
    capacity_kilolitres numeric NOT NULL CHECK (
        capacity_kilolitres>0
    ),
    endurance_hours numeric NOT NULL CHECK (endurance_hours>0),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    FOREIGN KEY (power_plant_code,fuel_kind)
        REFERENCES rule_vehicle_power_plant_fuel(
            power_plant_code,fuel_kind
        )
);

CREATE OR REPLACE FUNCTION vehicle_validate_class_fuel_tank()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    selected_plant text;
BEGIN
    SELECT coalesce(regular.power_plant_code,ship.power_plant_code)
    INTO selected_plant
    FROM vehicle_class class
    LEFT JOIN vehicle_class_power_plant regular
      USING (vehicle_class_rule_id)
    LEFT JOIN vehicle_class_ship_scale_power_plant ship
      USING (vehicle_class_rule_id)
    WHERE class.vehicle_class_rule_id=NEW.vehicle_class_rule_id;
    IF selected_plant<>NEW.power_plant_code THEN
        RAISE EXCEPTION
            'Vehicle fuel tank conflicts with selected power plant'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER vehicle_class_fuel_tank_valid
BEFORE INSERT OR UPDATE ON vehicle_class_fuel_tank
FOR EACH ROW EXECUTE FUNCTION vehicle_validate_class_fuel_tank();

WITH source(
    class_code,component_code,quantity,rating,allocated_spaces,
    published_cost,calculation_status,tech_level_status,display_order
) AS (
    VALUES
        ('destroyer-watercraft','control.advanced',1::smallint,
         NULL::numeric,2::numeric,10000::bigint,
         'matches','matches',1::smallint),
        ('destroyer-watercraft','communication.class-4',1,
         NULL,0.10,4000,'matches','matches',2),
        ('destroyer-watercraft','sensor.basic-civilian',1,
         NULL,6,10000,'matches','matches',3),
        ('destroyer-watercraft','computer.model-1',1,
         NULL,0.01,500,'matches','matches',4),
        ('destroyer-watercraft',
         'accommodation.control-cabin-standard',1,
         30,324,90000,'published_override','matches',5),
        ('destroyer-watercraft',
         'accommodation.stateroom-standard',29,
         NULL,1392,14500000,'matches','matches',6),
        ('motor-boat','control.basic',1,NULL,1,0,
         'matches','matches',1),
        ('motor-boat','communication.class-2',1,NULL,0.02,1000,
         'matches','matches',2),
        ('motor-boat','accommodation.control-cabin-standard',1,
         NULL,72,20000,'matches','matches',3),
        ('motor-boat','accommodation.stateroom-standard',5,
         NULL,240,2500000,'matches','matches',4),
        ('steamship','control.basic',1,NULL,1,0,
         'matches','matches',1),
        ('steamship','accommodation.control-cabin-standard',1,
         5,216,30000,'published_override','matches',2),
        ('steamship','accommodation.stateroom-standard',8,
         NULL,384,4000000,'matches','matches',3),
        ('steamship','additional.galley-full',1,15,24,9500,
         'formula','matches',4),
        ('submersible','control.basic',1,NULL,1,0,
         'matches','matches',1),
        ('submersible','communication.class-3',1,NULL,0.05,2000,
         'matches','matches',2),
        ('submersible','accommodation.control-cabin-standard',1,
         NULL,72,20000,'matches','matches',3),
        ('submersible','accommodation.control-cabin-extended',2,
         NULL,36,10000,'matches','matches',4),
        ('submersible','accommodation.stateroom-standard',8,
         NULL,384,4000000,'matches','matches',5),
        ('submersible','life-support.extended',3,
         NULL,9,157500,'matches','published_override',6),
        ('submersible','additional.galley-full',1,15,24,9500,
         'formula','matches',7),
        ('submersible','additional.airlock',1,NULL,12,200000,
         'matches','matches',8)
)
INSERT INTO vehicle_class_component (
    vehicle_class_rule_id,component_rule_id,quantity,rating,
    allocated_spaces,display_order,published_cost_minor,
    calculation_status,tech_level_status,source_locator_id
)
SELECT class.vehicle_class_rule_id,component.component_rule_id,
       source.quantity,source.rating,source.allocated_spaces,
       source.display_order,source.published_cost,
       source.calculation_status,source.tech_level_status,
       class.source_locator_id
FROM source
JOIN vehicle_class class USING (class_code)
JOIN vehicle_component_definition component USING (component_code);

INSERT INTO vehicle_class_configuration_option (
    vehicle_class_rule_id,option_rule_id,allocated_spaces,
    published_cost_minor,source_locator_id
)
SELECT class.vehicle_class_rule_id,option.option_rule_id,
       source.spaces,source.cost_minor,class.source_locator_id
FROM (
    VALUES
        ('motor-boat','streamlined',0::numeric,0::bigint),
        ('submersible','submersible',0,15000000),
        ('submersible','hostile-environmental-protection',3,0),
        ('submersible','vacuum-environmental-protection',3,12000000)
) source(class_code,option_code,spaces,cost_minor)
JOIN vehicle_class class USING (class_code)
JOIN rule_vehicle_configuration_option option USING (option_code);

INSERT INTO vehicle_class_drive_option (
    vehicle_class_rule_id,option_rule_id,option_steps,
    published_cost_minor,source_locator_id
)
SELECT class.vehicle_class_rule_id,option.option_rule_id,
       1,10000000,class.source_locator_id
FROM vehicle_class class
JOIN rule_vehicle_drive_option option
  ON option.option_code='increased-agility'
WHERE class.class_code='destroyer-watercraft';

INSERT INTO vehicle_class_autopilot (
    vehicle_class_rule_id,vehicle_category,skill_rule_id,
    skill_level,published_cost_minor,source_locator_id
)
SELECT class.vehicle_class_rule_id,'sea_vessel',
       skill.rule_id,source.skill_level,source.cost_minor,
       class.source_locator_id
FROM (
    VALUES
        ('destroyer-watercraft','skill.ocean-ships',
         2::smallint,12000::bigint),
        ('submersible','skill.submarine',0,2000)
) source(class_code,skill_code,skill_level,cost_minor)
JOIN vehicle_class class USING (class_code)
JOIN rule_rule skill
  ON skill.rule_code=source.skill_code;

INSERT INTO vehicle_class_computer_option (
    vehicle_class_rule_id,option_code,
    published_incremental_cost_minor,source_locator_id
)
SELECT vehicle_class_rule_id,'hardened',250,source_locator_id
FROM vehicle_class
WHERE class_code='destroyer-watercraft';

INSERT INTO vehicle_class_fuel_tank (
    vehicle_class_rule_id,power_plant_code,fuel_kind,
    capacity_kilolitres,endurance_hours,source_locator_id
)
SELECT class.vehicle_class_rule_id,source.power_plant_code,
       source.fuel_kind,source.capacity,source.endurance,
       class.source_locator_id
FROM (
    VALUES
        ('destroyer-watercraft','early-fusion','hydrogen',
         496::numeric,672::numeric),
        ('motor-boat','internal-combustion','hydrocarbons',
         1.29,10),
        ('steamship','external-combustion','coal',200,240),
        ('submersible','fission','radioactives',7.68,2016)
) source(
    class_code,power_plant_code,fuel_kind,capacity,endurance
)
JOIN vehicle_class class USING (class_code);

INSERT INTO src_issue (
    issue_code,domain_code,issue_type,review_priority,
    subject_code,title,problem_statement,
    published_value,calculated_value,
    reviewer_question,requested_evidence,engine_disposition
)
VALUES (
    'vehicle.class.submersible-life-support-tech-level',
    'vehicle.catalogue','tech_level_conflict','medium',
    'submersible',
    'TL6 Submersible installs TL7 Extended Life Support',
    'The common Submersible is published at TL6 but its itemized design installs Extended Life Support, whose governing vehicle component entry has minimum TL7.',
    'TL6 class with TL7 component',
    'Published component retained as an explicit tech-level override',
    'Should the Submersible be TL7, use Basic Life Support, or retain an exceptional early Extended Life Support installation?',
    'A corrected printing, publisher errata, or another authorized Submersible profile resolving the tech-level mismatch.',
    'preserve_published'
);

INSERT INTO src_issue_locator (
    source_issue_id,source_locator_id,evidence_role
)
SELECT issue.source_issue_id,locator.source_locator_id,'primary'
FROM src_issue issue
JOIN src_locator locator
  ON locator.heading_path=
     'Common Watercraft > TL6 Submersible'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1'
WHERE issue.issue_code=
      'vehicle.class.submersible-life-support-tech-level';
