ALTER TABLE rule_vehicle_component_formula
    ADD COLUMN cost_per_increment_minor numeric NOT NULL DEFAULT 0 CHECK (
        cost_per_increment_minor>=0
    );

UPDATE rule_vehicle_component_formula formula
SET cost_per_increment_minor=source.cost_per_increment_minor,
    cost_per_basis_unit_minor=0
FROM (
    VALUES
        ('additional.floats-pontoons',250::numeric),
        ('additional.folding-wings-rotors',600::numeric)
) source(component_code,cost_per_increment_minor)
JOIN vehicle_component_definition component
  ON component.component_code=source.component_code
WHERE formula.component_rule_id=component.component_rule_id;

UPDATE vehicle_component_definition
SET space_basis='fixed'
WHERE component_code='additional.holding-tank';

ALTER TABLE rule_vehicle_cargo_trailer_rule
    ADD COLUMN towing_speed_formula_code text NOT NULL DEFAULT
        'base-speed-times-chassis-space-ratio' CHECK (
            towing_speed_formula_code=
            'base-speed-times-chassis-space-ratio'
        );

CREATE TABLE rule_vehicle_fire_extinguisher_regulation (
    component_rule_id bigint PRIMARY KEY REFERENCES
        vehicle_component_definition(component_rule_id),
    minimum_tech_level smallint NOT NULL CHECK (
        minimum_tech_level>=0
    ),
    minimum_law_level smallint NOT NULL CHECK (
        minimum_law_level>=0
    ),
    civilian_vehicle_only boolean NOT NULL,
    requirement_strength text NOT NULL CHECK (
        requirement_strength IN ('may_require','required')
    )
);

INSERT INTO rule_vehicle_fire_extinguisher_regulation
SELECT component_rule_id,8,6,true,'may_require'
FROM vehicle_component_definition
WHERE component_code='additional.fire-extinguishers';

CREATE TABLE rule_vehicle_holding_tank_content (
    component_rule_id bigint NOT NULL REFERENCES
        vehicle_component_definition(component_rule_id),
    content_type_code text NOT NULL CHECK (
        content_type_code IN ('liquid','gas')
    ),
    selected_at_construction boolean NOT NULL,
    PRIMARY KEY (component_rule_id,content_type_code)
);

INSERT INTO rule_vehicle_holding_tank_content
SELECT component.component_rule_id,source.content_type_code,true
FROM (
    VALUES ('liquid'),('gas')
) source(content_type_code)
JOIN vehicle_component_definition component
  ON component.component_code='additional.holding-tank';

CREATE TABLE rule_vehicle_research_lab_bonus (
    component_rule_id bigint NOT NULL REFERENCES
        vehicle_component_definition(component_rule_id),
    skill_dm smallint NOT NULL CHECK (skill_dm BETWEEN 1 AND 3),
    spaces_per_researcher smallint NOT NULL CHECK (
        spaces_per_researcher>0
    ),
    price_per_researcher_minor bigint NOT NULL CHECK (
        price_per_researcher_minor>=0
    ),
    PRIMARY KEY (component_rule_id,skill_dm)
);

INSERT INTO rule_vehicle_research_lab_bonus
SELECT component.component_rule_id,source.skill_dm,
       source.skill_dm*3,source.skill_dm*10000
FROM generate_series(1,3) source(skill_dm)
JOIN vehicle_component_definition component
  ON component.component_code='additional.research-lab-space';

CREATE TABLE rule_vehicle_research_lab_discipline (
    component_rule_id bigint NOT NULL REFERENCES
        vehicle_component_definition(component_rule_id),
    discipline_code text NOT NULL CHECK (
        discipline_code ~
        '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
    ),
    discipline_name text NOT NULL,
    display_order smallint NOT NULL CHECK (display_order>0),
    PRIMARY KEY (component_rule_id,discipline_code),
    UNIQUE (component_rule_id,display_order)
);

INSERT INTO rule_vehicle_research_lab_discipline
SELECT component.component_rule_id,source.*
FROM (
    VALUES
        ('physics','Physics',1::smallint),
        ('chemistry','Chemistry',2),
        ('biology','Biology',3),
        ('psychology','Psychology',4),
        ('structures','Structures',5),
        ('materials','Materials',6)
) source(discipline_code,discipline_name,display_order)
JOIN vehicle_component_definition component
  ON component.component_code='additional.research-lab-space';

CREATE TABLE rule_vehicle_liquid_cannon_purpose (
    component_rule_id bigint NOT NULL REFERENCES
        rule_vehicle_liquid_cannon(component_rule_id),
    purpose_code text NOT NULL CHECK (
        purpose_code IN (
            'fire-suppression','riot-control','chemical-dispersal'
        )
    ),
    PRIMARY KEY (component_rule_id,purpose_code)
);

INSERT INTO rule_vehicle_liquid_cannon_purpose
SELECT cannon.component_rule_id,source.purpose_code
FROM rule_vehicle_liquid_cannon cannon
CROSS JOIN (
    VALUES
        ('fire-suppression'),('riot-control'),('chemical-dispersal')
) source(purpose_code);
