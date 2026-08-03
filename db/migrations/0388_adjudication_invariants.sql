CREATE FUNCTION vehicle_protect_component_adjudications()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.component_code='control.primitive'
       AND (NEW.minimum_tech_level<>1
            OR NEW.calculation_status<>'adjudicated') THEN
        RAISE EXCEPTION 'CE-VDS-003 Primitive Controls adjudication is immutable'
            USING ERRCODE='23514';
    END IF;
    IF OLD.component_code='additional.wet-bar'
       AND (NEW.unit_spaces<>1.5 OR NEW.unit_cost_minor<>2000
            OR NEW.calculation_status<>'adjudicated') THEN
        RAISE EXCEPTION 'CE-VDS-001 Wet Bar adjudication is immutable'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE FUNCTION vehicle_protect_sensor_adjudication()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.sensor_code='standard'
       AND NEW.published_range_text<>'Very Long (500 m)' THEN
        RAISE EXCEPTION 'CE-VDS-005 sensor-range adjudication is immutable'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE FUNCTION vehicle_protect_missile_adjudication()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.missile_code='nuclear-nas-guided'
       AND (NEW.radiation_hit_count<>1
            OR NEW.radiation_rule_status<>'adjudicated') THEN
        RAISE EXCEPTION 'CE-VDS-006 NAS radiation adjudication is immutable'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE FUNCTION vehicle_protect_ordnance_adjudication()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.ordnance_code='torpedo-nuclear-heavy'
       AND (NEW.range_profile_code<>'very-distant'
            OR NEW.range_status<>'adjudicated'
            OR NEW.radiation_unit_status<>'adjudicated-rads') THEN
        RAISE EXCEPTION 'CE-VDS-004 torpedo adjudication is immutable'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER vehicle_component_adjudication_immutable
BEFORE UPDATE ON vehicle_component_definition
FOR EACH ROW EXECUTE FUNCTION vehicle_protect_component_adjudications();
CREATE TRIGGER vehicle_sensor_adjudication_immutable
BEFORE UPDATE ON rule_vehicle_sensor_package
FOR EACH ROW EXECUTE FUNCTION vehicle_protect_sensor_adjudication();
CREATE TRIGGER vehicle_missile_adjudication_immutable
BEFORE UPDATE ON rule_vehicle_missile
FOR EACH ROW EXECUTE FUNCTION vehicle_protect_missile_adjudication();
CREATE TRIGGER vehicle_ordnance_adjudication_immutable
BEFORE UPDATE ON rule_vehicle_ordnance_definition
FOR EACH ROW EXECUTE FUNCTION vehicle_protect_ordnance_adjudication();

CREATE FUNCTION vehicle_protect_weapon_point_adjudications()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE class_code_value text;
BEGIN
    SELECT class_code INTO class_code_value
    FROM vehicle_class WHERE vehicle_class_rule_id=OLD.vehicle_class_rule_id;
    IF class_code_value='afv-tracked'
       AND (NEW.effective_available_weapon_points<>2
            OR NEW.adjudication_basis<>'governing-rule') THEN
        RAISE EXCEPTION 'CE-VDS-008 AFV weapon-point adjudication is immutable'
            USING ERRCODE='23514';
    END IF;
    IF class_code_value='destroyer-watercraft'
       AND (NEW.calculated_used_weapon_points<>22
            OR NEW.adjudication_basis<>'published-profile') THEN
        RAISE EXCEPTION 'CE-VDS-012 Destroyer weapon-point adjudication is immutable'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER vehicle_weapon_point_adjudication_immutable
BEFORE UPDATE ON vehicle_class_weapon_point_summary
FOR EACH ROW EXECUTE FUNCTION vehicle_protect_weapon_point_adjudications();
