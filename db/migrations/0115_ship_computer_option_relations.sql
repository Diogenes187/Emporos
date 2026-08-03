CREATE TABLE ship_class_computer_option (
    ship_class_rule_id bigint NOT NULL REFERENCES
        ship_class_computer(ship_class_rule_id),
    computer_option_code text NOT NULL REFERENCES
        rule_ship_computer_option(computer_option_code),
    PRIMARY KEY (ship_class_rule_id,computer_option_code)
);

INSERT INTO ship_class_computer_option
SELECT ship_class_rule_id,'bis'
FROM ship_class_computer
WHERE jump_control_specialization
UNION ALL
SELECT ship_class_rule_id,'fib'
FROM ship_class_computer
WHERE hardened_systems;

ALTER TABLE ship_class_computer
    DROP COLUMN jump_control_specialization,
    DROP COLUMN hardened_systems;

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
           EXISTS (
               SELECT 1
               FROM ship_class_computer_option option
               WHERE option.ship_class_rule_id=
                     selected.ship_class_rule_id
                 AND option.computer_option_code='bis'
           )
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

CREATE OR REPLACE FUNCTION ship_validate_computer_option_removal()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    computer_rating smallint;
    allocated_rating integer;
BEGIN
    IF OLD.computer_option_code='bis' THEN
        SELECT computer.rating
        INTO computer_rating
        FROM ship_class_computer selected
        JOIN rule_ship_computer computer
          ON computer.computer_code=selected.computer_code
        WHERE selected.ship_class_rule_id=OLD.ship_class_rule_id;

        SELECT coalesce(sum(software.allocated_rating),0)
        INTO allocated_rating
        FROM ship_class_software software
        WHERE software.ship_class_rule_id=OLD.ship_class_rule_id;

        IF allocated_rating>computer_rating THEN
            RAISE EXCEPTION
                'Cannot remove bis while software uses bonus rating'
                USING ERRCODE='23514';
        END IF;
    END IF;
    RETURN OLD;
END;
$$;

CREATE TRIGGER ship_computer_option_removal_valid
BEFORE DELETE ON ship_class_computer_option
FOR EACH ROW EXECUTE FUNCTION ship_validate_computer_option_removal();
