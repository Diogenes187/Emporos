CREATE TABLE ship_class_hangar_option (
    ship_class_rule_id bigint NOT NULL REFERENCES
        ship_class(ship_class_rule_id),
    hangar_identifier text NOT NULL CHECK (
        btrim(hangar_identifier)<>''
    ),
    hangar_option_code text NOT NULL REFERENCES
        rule_ship_hangar_option(hangar_option_code),
    installation_count smallint NOT NULL DEFAULT 1 CHECK (
        installation_count>0
    ),
    basis_quantity numeric NOT NULL DEFAULT 1 CHECK (
        basis_quantity>0
    ),
    allocated_tons numeric NOT NULL CHECK (allocated_tons>0),
    installation_cost_minor bigint NOT NULL CHECK (
        installation_cost_minor>=0
    ),
    PRIMARY KEY (ship_class_rule_id,hangar_identifier)
);

CREATE OR REPLACE FUNCTION ship_validate_class_component_design()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    class_tl smallint;
    hull_capacity numeric;
    component_tl smallint;
    basis text;
    unit_tons_value numeric;
    factor numeric;
    expected_tons numeric;
    allocated_elsewhere numeric;
BEGIN
    SELECT minimum_tech_level,hull_tons
    INTO class_tl,hull_capacity
    FROM ship_class
    WHERE ship_class_rule_id=NEW.ship_class_rule_id;

    SELECT minimum_tech_level,tonnage_basis,unit_tons,
           tonnage_factor
    INTO component_tl,basis,unit_tons_value,factor
    FROM ship_component_definition
    WHERE component_rule_id=NEW.component_rule_id;

    expected_tons:=CASE basis
        WHEN 'fixed' THEN unit_tons_value*NEW.quantity
        WHEN 'per_component_ton' THEN unit_tons_value*NEW.quantity
        WHEN 'per_person' THEN
            unit_tons_value*NEW.quantity*NEW.rating
        WHEN 'largest_craft_multiplier' THEN
            factor*NEW.quantity*NEW.rating
        WHEN 'hull_percent' THEN
            hull_capacity*factor*NEW.quantity
        WHEN 'included' THEN 0
        ELSE NULL
    END;

    SELECT coalesce(sum(allocated_tons),0)
    INTO allocated_elsewhere
    FROM ship_class_component
    WHERE ship_class_rule_id=NEW.ship_class_rule_id
      AND (
          TG_OP='INSERT'
          OR ship_class_component_id<>
             NEW.ship_class_component_id
      );

    IF (component_tl IS NOT NULL AND class_tl<component_tl)
       OR (
           basis IN ('per_person','largest_craft_multiplier')
           AND NEW.rating IS NULL
       )
       OR (
           expected_tons IS NOT NULL
           AND NEW.allocated_tons<>expected_tons
       )
       OR allocated_elsewhere+NEW.allocated_tons>hull_capacity THEN
        RAISE EXCEPTION
            'Ship component conflicts with formula, tech, or hull capacity'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER ship_class_component_design_valid
BEFORE INSERT OR UPDATE ON ship_class_component
FOR EACH ROW EXECUTE FUNCTION ship_validate_class_component_design();

CREATE OR REPLACE FUNCTION ship_validate_class_hangar()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    hull_capacity numeric;
    fixed_tons numeric;
    person_tons numeric;
    hull_percent_value numeric;
    fixed_cost bigint;
    cost_per_ton bigint;
    expected_tons numeric;
    expected_cost numeric;
BEGIN
    SELECT hull_tons INTO hull_capacity
    FROM ship_class
    WHERE ship_class_rule_id=NEW.ship_class_rule_id;

    SELECT installed_tons,tons_per_person,hull_percent,
           installation_cost_minor,cost_minor_per_ton
    INTO fixed_tons,person_tons,hull_percent_value,
         fixed_cost,cost_per_ton
    FROM rule_ship_hangar_option
    WHERE hangar_option_code=NEW.hangar_option_code;

    expected_tons:=coalesce(
        fixed_tons*NEW.installation_count,
        person_tons*NEW.basis_quantity*NEW.installation_count,
        hull_capacity*hull_percent_value*NEW.installation_count
    );
    expected_cost:=coalesce(
        fixed_cost*NEW.installation_count,
        cost_per_ton*expected_tons
    );

    IF NEW.allocated_tons<>expected_tons
       OR NEW.installation_cost_minor<>expected_cost THEN
        RAISE EXCEPTION
            'Ship hangar allocation conflicts with published formula'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER ship_class_hangar_valid
BEFORE INSERT OR UPDATE ON ship_class_hangar_option
FOR EACH ROW EXECUTE FUNCTION ship_validate_class_hangar();
