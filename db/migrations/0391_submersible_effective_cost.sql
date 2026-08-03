UPDATE vehicle_class
SET construction_cost_minor=31062370
WHERE class_code='submersible';

CREATE OR REPLACE FUNCTION vehicle_protect_medium_class_adjudications()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.class_code='air-raft' AND
       (NEW.cargo_spaces<>29.68 OR NEW.allocated_spaces<>18.32 OR
        NEW.construction_cost_minor<>94160) THEN
        RAISE EXCEPTION 'CE-VDS-016 Air/Raft adjudication is immutable'
            USING ERRCODE='23514';
    END IF;
    IF OLD.class_code='biplane' AND NEW.chassis_code<>'5' THEN
        RAISE EXCEPTION 'CE-VDS-018 Biplane adjudication is immutable'
            USING ERRCODE='23514';
    END IF;
    IF OLD.class_code='steamship' AND
       (NEW.allocated_spaces<>1883.4 OR NEW.cargo_spaces<>516.6) THEN
        RAISE EXCEPTION 'CE-VDS-022 Steamship adjudication is immutable'
            USING ERRCODE='23514';
    END IF;
    IF OLD.class_code='submersible' AND
       (NEW.minimum_tech_level<>7 OR
        NEW.construction_cost_minor<>31062370) THEN
        RAISE EXCEPTION 'CE-VDS-023 Submersible adjudication is immutable'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;
