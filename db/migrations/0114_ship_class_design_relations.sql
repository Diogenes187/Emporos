CREATE TABLE ship_class_design_hull (
    ship_class_rule_id bigint PRIMARY KEY REFERENCES
        ship_class(ship_class_rule_id),
    hull_code text NOT NULL REFERENCES
        rule_ship_hull_design(hull_code),
    configuration_code text NOT NULL REFERENCES
        rule_ship_configuration(configuration_code),
    armor_code text REFERENCES rule_ship_armor_design(armor_code),
    armor_increments smallint NOT NULL DEFAULT 0 CHECK (
        armor_increments>=0
    ),
    CHECK (
        (armor_code IS NULL AND armor_increments=0)
        OR
        (armor_code IS NOT NULL AND armor_increments>0)
    )
);

CREATE TABLE ship_class_armor_option (
    ship_class_rule_id bigint NOT NULL REFERENCES
        ship_class_design_hull(ship_class_rule_id),
    armor_option_code text NOT NULL REFERENCES
        rule_ship_armor_option(armor_option_code),
    installation_count smallint NOT NULL DEFAULT 1 CHECK (
        installation_count>0
    ),
    PRIMARY KEY (ship_class_rule_id,armor_option_code)
);

CREATE TABLE ship_class_drive (
    ship_class_rule_id bigint NOT NULL REFERENCES
        ship_class_design_hull(ship_class_rule_id),
    drive_kind text NOT NULL CHECK (
        drive_kind IN ('jump','maneuver','power_plant')
    ),
    craft_scale text NOT NULL CHECK (
        craft_scale IN ('starship','small_craft')
    ),
    drive_code text NOT NULL,
    performance smallint NOT NULL CHECK (performance BETWEEN 1 AND 6),
    PRIMARY KEY (ship_class_rule_id,drive_kind),
    FOREIGN KEY (craft_scale,drive_code)
        REFERENCES rule_ship_drive_design(craft_scale,drive_code),
    CHECK (drive_kind<>'jump' OR craft_scale='starship')
);

CREATE TABLE ship_class_computer (
    ship_class_rule_id bigint PRIMARY KEY REFERENCES
        ship_class(ship_class_rule_id),
    computer_code text NOT NULL REFERENCES
        rule_ship_computer(computer_code),
    jump_control_specialization boolean NOT NULL DEFAULT false,
    hardened_systems boolean NOT NULL DEFAULT false
);

CREATE TABLE ship_class_software (
    ship_class_rule_id bigint NOT NULL REFERENCES
        ship_class_computer(ship_class_rule_id),
    software_code text NOT NULL REFERENCES
        rule_ship_software(software_code),
    software_level smallint NOT NULL CHECK (software_level>0),
    allocated_rating smallint NOT NULL CHECK (allocated_rating>0),
    PRIMARY KEY (ship_class_rule_id,software_code)
);

CREATE TABLE ship_class_electronics (
    ship_class_rule_id bigint PRIMARY KEY REFERENCES
        ship_class(ship_class_rule_id),
    electronics_code text NOT NULL REFERENCES
        rule_ship_electronics_suite(electronics_code)
);

CREATE TABLE ship_class_construction_line (
    construction_line_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ship_class_rule_id bigint NOT NULL REFERENCES
        ship_class(ship_class_rule_id),
    line_order smallint NOT NULL CHECK (line_order>0),
    line_kind text NOT NULL CHECK (
        line_kind IN (
            'hull','configuration','armor','armor_option','bridge',
            'jump_drive','maneuver_drive','power_plant','fuel',
            'computer','computer_option','software','electronics',
            'crew_space','component','weapon','screen','discount',
            'fee','other'
        )
    ),
    reference_code text NOT NULL CHECK (btrim(reference_code)<>''),
    quantity numeric NOT NULL DEFAULT 1 CHECK (quantity>0),
    allocated_tons numeric NOT NULL DEFAULT 0 CHECK (
        allocated_tons>=0
    ),
    cost_minor bigint NOT NULL,
    calculation_basis text NOT NULL CHECK (
        btrim(calculation_basis)<>''
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    UNIQUE (ship_class_rule_id,line_order)
);

CREATE VIEW ship_class_construction_total AS
SELECT class.ship_class_rule_id,
       class.hull_tons,
       coalesce(sum(line.allocated_tons),0) AS allocated_tons,
       class.hull_tons-coalesce(sum(line.allocated_tons),0)
           AS unallocated_tons,
       coalesce(sum(line.cost_minor),0)::bigint AS calculated_cost_minor,
       class.construction_cost_minor AS published_cost_minor,
       class.construction_cost_minor-
           coalesce(sum(line.cost_minor),0)::bigint AS cost_variance_minor
FROM ship_class class
LEFT JOIN ship_class_construction_line line
  ON line.ship_class_rule_id=class.ship_class_rule_id
GROUP BY class.ship_class_rule_id;

CREATE OR REPLACE FUNCTION ship_validate_design_hull()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    class_hull_tons numeric;
    class_configuration text;
    class_weeks integer;
    catalog_hull_tons numeric;
    catalog_weeks integer;
    armor_tl smallint;
    class_tl smallint;
BEGIN
    SELECT hull_tons,hull_configuration,construction_weeks,
           minimum_tech_level
    INTO class_hull_tons,class_configuration,class_weeks,class_tl
    FROM ship_class
    WHERE ship_class_rule_id=NEW.ship_class_rule_id;

    SELECT hull_tons,construction_weeks
    INTO catalog_hull_tons,catalog_weeks
    FROM rule_ship_hull_design
    WHERE hull_code=NEW.hull_code;

    IF class_hull_tons<>catalog_hull_tons
       OR (
           class_configuration IS NOT NULL
           AND class_configuration<>NEW.configuration_code
       )
       OR (
           class_weeks IS NOT NULL
           AND class_weeks<>catalog_weeks
       ) THEN
        RAISE EXCEPTION
            'Ship class hull design conflicts with published hull'
            USING ERRCODE='23514';
    END IF;

    IF NEW.armor_code IS NOT NULL THEN
        SELECT minimum_tech_level INTO armor_tl
        FROM rule_ship_armor_design
        WHERE armor_code=NEW.armor_code;
        IF class_tl<armor_tl THEN
            RAISE EXCEPTION
                'Ship class tech level is below selected armor'
                USING ERRCODE='23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER ship_design_hull_valid
BEFORE INSERT OR UPDATE ON ship_class_design_hull
FOR EACH ROW EXECUTE FUNCTION ship_validate_design_hull();

CREATE OR REPLACE FUNCTION ship_validate_armor_option()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    class_tl smallint;
    option_tl smallint;
    option_max smallint;
BEGIN
    SELECT class.minimum_tech_level
    INTO class_tl
    FROM ship_class class
    WHERE class.ship_class_rule_id=NEW.ship_class_rule_id;

    SELECT minimum_tech_level,maximum_installations
    INTO option_tl,option_max
    FROM rule_ship_armor_option
    WHERE armor_option_code=NEW.armor_option_code;

    IF class_tl<option_tl OR NEW.installation_count>option_max THEN
        RAISE EXCEPTION
            'Ship armor option exceeds tech or installation limit'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER ship_armor_option_valid
BEFORE INSERT OR UPDATE ON ship_class_armor_option
FOR EACH ROW EXECUTE FUNCTION ship_validate_armor_option();

CREATE OR REPLACE FUNCTION ship_validate_class_drive()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    selected_hull_code text;
    hull_scale text;
    published_performance smallint;
    class_performance smallint;
BEGIN
    SELECT design.hull_code,hull.craft_scale
    INTO selected_hull_code,hull_scale
    FROM ship_class_design_hull design
    JOIN rule_ship_hull_design hull
      ON hull.hull_code=design.hull_code
    WHERE design.ship_class_rule_id=NEW.ship_class_rule_id;

    SELECT performance INTO published_performance
    FROM rule_ship_drive_performance
    WHERE craft_scale=NEW.craft_scale
      AND drive_code=NEW.drive_code
      AND hull_code=selected_hull_code;

    SELECT CASE NEW.drive_kind
               WHEN 'jump' THEN jump_rating
               WHEN 'maneuver' THEN maneuver_rating
               ELSE power_rating
           END
    INTO class_performance
    FROM ship_class
    WHERE ship_class_rule_id=NEW.ship_class_rule_id;

    IF NEW.craft_scale<>hull_scale
       OR published_performance IS NULL
       OR NEW.performance<>published_performance
       OR NEW.performance<>class_performance THEN
        RAISE EXCEPTION
            'Ship class drive conflicts with hull performance matrix'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER ship_class_drive_valid
BEFORE INSERT OR UPDATE ON ship_class_drive
FOR EACH ROW EXECUTE FUNCTION ship_validate_class_drive();

CREATE OR REPLACE FUNCTION ship_validate_class_computer()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    class_tl smallint;
    computer_tl smallint;
BEGIN
    SELECT minimum_tech_level INTO class_tl
    FROM ship_class
    WHERE ship_class_rule_id=NEW.ship_class_rule_id;
    SELECT minimum_tech_level INTO computer_tl
    FROM rule_ship_computer
    WHERE computer_code=NEW.computer_code;
    IF class_tl<computer_tl THEN
        RAISE EXCEPTION
            'Ship class tech level is below selected computer'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER ship_class_computer_valid
BEFORE INSERT OR UPDATE ON ship_class_computer
FOR EACH ROW EXECUTE FUNCTION ship_validate_class_computer();

CREATE OR REPLACE FUNCTION ship_validate_class_software()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    class_tl smallint;
    software_tl smallint;
    maximum_level smallint;
    computer_rating smallint;
    bis_enabled boolean;
    non_jump_rating integer;
    total_rating integer;
BEGIN
    SELECT class.minimum_tech_level,computer.rating,
           selected.jump_control_specialization
    INTO class_tl,computer_rating,bis_enabled
    FROM ship_class_computer selected
    JOIN ship_class class
      ON class.ship_class_rule_id=selected.ship_class_rule_id
    JOIN rule_ship_computer computer
      ON computer.computer_code=selected.computer_code
    WHERE selected.ship_class_rule_id=NEW.ship_class_rule_id;

    SELECT minimum_tech_level,rule.maximum_level
    INTO software_tl,maximum_level
    FROM rule_ship_software rule
    WHERE software_code=NEW.software_code;

    SELECT
        coalesce(sum(allocated_rating) FILTER (
            WHERE software_code<>'jump-control'
        ),0),
        coalesce(sum(allocated_rating),0)
    INTO non_jump_rating,total_rating
    FROM ship_class_software
    WHERE ship_class_rule_id=NEW.ship_class_rule_id
      AND software_code<>NEW.software_code;

    non_jump_rating:=non_jump_rating+
        CASE WHEN NEW.software_code='jump-control'
             THEN 0 ELSE NEW.allocated_rating END;
    total_rating:=total_rating+NEW.allocated_rating;

    IF class_tl<software_tl
       OR (
           maximum_level IS NOT NULL
           AND NEW.software_level>maximum_level
       )
       OR non_jump_rating>computer_rating
       OR total_rating>(
          computer_rating+
          CASE WHEN bis_enabled THEN 5 ELSE 0 END
       ) THEN
        RAISE EXCEPTION
            'Ship software exceeds tech, level, or computer rating'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER ship_class_software_valid
BEFORE INSERT OR UPDATE ON ship_class_software
FOR EACH ROW EXECUTE FUNCTION ship_validate_class_software();

CREATE OR REPLACE FUNCTION ship_construction_lines_immutable()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'Ship construction calculation lines are immutable'
        USING ERRCODE='23514';
END;
$$;

CREATE TRIGGER ship_construction_line_immutable
BEFORE UPDATE OR DELETE ON ship_class_construction_line
FOR EACH ROW EXECUTE FUNCTION ship_construction_lines_immutable();
