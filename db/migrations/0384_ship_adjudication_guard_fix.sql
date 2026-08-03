DROP TRIGGER ship_smelter_adjudication_immutable
    ON ship_component_definition;
DROP TRIGGER ship_destroyer_drive_adjudication_immutable
    ON ship_class_drive;
DROP TRIGGER ship_research_payload_adjudication_immutable
    ON ship_class_carried_item;
DROP FUNCTION ship_protect_adjudicated_source_state();

CREATE FUNCTION ship_protect_smelter_adjudication()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.component_code='smelter'
       AND (NEW.unit_tons<>4 OR NEW.unit_cost_minor<>90000
            OR NEW.calculation_status<>'adjudicated') THEN
        RAISE EXCEPTION 'CE-SHIP-001 smelter adjudication is immutable'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE FUNCTION ship_protect_destroyer_drive_adjudication()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.ship_class_rule_id=(SELECT ship_class_rule_id FROM ship_class
                               WHERE class_code='destroyer')
       AND OLD.drive_kind IN ('jump','maneuver')
       AND (((OLD.drive_kind='jump') AND NEW.drive_code<>'H')
            OR ((OLD.drive_kind='maneuver') AND NEW.drive_code<>'N')
            OR NEW.validation_status<>'validated') THEN
        RAISE EXCEPTION 'CE-SHIP-002 drive adjudication is immutable'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE FUNCTION ship_protect_research_payload_adjudication()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.carrier_class_rule_id=(SELECT ship_class_rule_id FROM ship_class
                                  WHERE class_code='research-vessel')
       AND NEW.relationship_status<>'published_cross_tl_payload' THEN
        RAISE EXCEPTION 'CE-SHIP-003 payload adjudication is immutable'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER ship_smelter_adjudication_immutable
BEFORE UPDATE ON ship_component_definition
FOR EACH ROW EXECUTE FUNCTION ship_protect_smelter_adjudication();
CREATE TRIGGER ship_destroyer_drive_adjudication_immutable
BEFORE UPDATE ON ship_class_drive
FOR EACH ROW EXECUTE FUNCTION ship_protect_destroyer_drive_adjudication();
CREATE TRIGGER ship_research_payload_adjudication_immutable
BEFORE UPDATE ON ship_class_carried_item
FOR EACH ROW EXECUTE FUNCTION ship_protect_research_payload_adjudication();
