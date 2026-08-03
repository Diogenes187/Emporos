ALTER TABLE ship_class_construction_line
    ADD CONSTRAINT ship_construction_non_space_line_tons_check CHECK (
        line_kind NOT IN (
            'hull','configuration','computer_option','discount','fee'
        )
        OR allocated_tons=0
    );

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
    hull_scale text;
    armor_tl smallint;
    class_tl smallint;
    invalid_drive boolean;
BEGIN
    SELECT hull_tons,hull_configuration,construction_weeks,
           minimum_tech_level
    INTO class_hull_tons,class_configuration,class_weeks,class_tl
    FROM ship_class
    WHERE ship_class_rule_id=NEW.ship_class_rule_id;

    SELECT hull_tons,construction_weeks,craft_scale
    INTO catalog_hull_tons,catalog_weeks,hull_scale
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

    SELECT EXISTS (
        SELECT 1
        FROM ship_class_drive drive
        LEFT JOIN rule_ship_drive_performance performance
          ON performance.craft_scale=hull_scale
         AND performance.drive_code=drive.drive_code
         AND performance.hull_code=NEW.hull_code
        WHERE drive.ship_class_rule_id=NEW.ship_class_rule_id
          AND (
              drive.craft_scale<>hull_scale
              OR performance.performance IS NULL
              OR performance.performance<>drive.performance
          )
    ) INTO invalid_drive;

    IF invalid_drive THEN
        RAISE EXCEPTION
            'Ship hull change invalidates selected drives'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION ship_validate_class_computer()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    class_tl smallint;
    computer_tl smallint;
    computer_rating smallint;
    bis_enabled boolean;
    non_jump_rating integer;
    total_rating integer;
BEGIN
    SELECT minimum_tech_level INTO class_tl
    FROM ship_class
    WHERE ship_class_rule_id=NEW.ship_class_rule_id;
    SELECT minimum_tech_level,rating
    INTO computer_tl,computer_rating
    FROM rule_ship_computer
    WHERE computer_code=NEW.computer_code;
    SELECT EXISTS (
        SELECT 1
        FROM ship_class_computer_option
        WHERE ship_class_rule_id=NEW.ship_class_rule_id
          AND computer_option_code='bis'
    ) INTO bis_enabled;
    SELECT
        coalesce(sum(allocated_rating) FILTER (
            WHERE software_code<>'jump-control'
        ),0),
        coalesce(sum(allocated_rating),0)
    INTO non_jump_rating,total_rating
    FROM ship_class_software
    WHERE ship_class_rule_id=NEW.ship_class_rule_id;

    IF class_tl<computer_tl
       OR non_jump_rating>computer_rating
       OR total_rating>(
           computer_rating+
           CASE WHEN bis_enabled THEN 5 ELSE 0 END
       ) THEN
        RAISE EXCEPTION
            'Ship computer conflicts with tech or installed software'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION ship_validate_construction_line()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    hull_capacity numeric;
    already_allocated numeric;
BEGIN
    SELECT hull_tons INTO hull_capacity
    FROM ship_class
    WHERE ship_class_rule_id=NEW.ship_class_rule_id;

    SELECT coalesce(sum(allocated_tons),0)
    INTO already_allocated
    FROM ship_class_construction_line
    WHERE ship_class_rule_id=NEW.ship_class_rule_id;

    IF already_allocated+NEW.allocated_tons>hull_capacity THEN
        RAISE EXCEPTION
            'Ship construction lines exceed hull tonnage'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER ship_construction_line_capacity_valid
BEFORE INSERT ON ship_class_construction_line
FOR EACH ROW EXECUTE FUNCTION ship_validate_construction_line();
