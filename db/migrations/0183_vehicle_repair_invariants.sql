CREATE OR REPLACE FUNCTION vehicle_validate_repair_resources()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    repair_rule record;
    system_rule record;
    spare record;
    donor record;
BEGIN
    IF OLD.finalized OR NOT NEW.finalized THEN
        RETURN NEW;
    END IF;
    SELECT * INTO repair_rule
    FROM rule_vehicle_repair_category
    WHERE repair_rule_id=OLD.repair_rule_id;

    IF OLD.repair_method='jury-rig' THEN
        SELECT * INTO system_rule
        FROM rule_vehicle_system_repair_state
        WHERE system_damage_state='damaged';
        IF NOT OLD.succeeded OR EXISTS (
            SELECT 1
            FROM vehicle_repair_random_die die
            WHERE die.vehicle_repair_receipt_id=
                  OLD.vehicle_repair_receipt_id
              AND die.roll_kind='operating-duration'
              AND die.die_sides<>
                  system_rule.jury_rig_duration_die_sides
        ) THEN
            RAISE EXCEPTION
                'Vehicle jury-rig outcome or dice are inconsistent'
                USING ERRCODE='23514';
        END IF;
    ELSIF repair_rule.skill_requirement<>'none'
          AND OLD.repairing_actor_id IS NULL THEN
        RAISE EXCEPTION 'Vehicle repair check requires an actor'
            USING ERRCODE='23514';
    END IF;

    FOR spare IN
        SELECT *
        FROM vehicle_repair_spare_source
        WHERE vehicle_repair_receipt_id=
              OLD.vehicle_repair_receipt_id
          AND donor_vehicle_system_state_id IS NOT NULL
    LOOP
        SELECT vehicle_id,current_hits INTO donor
        FROM vehicle_system_state
        WHERE vehicle_system_state_id=
              spare.donor_vehicle_system_state_id;
        IF donor.current_hits<spare.spare_part_hits
           OR (
               spare.source_kind='same-vehicle-system'
               AND donor.vehicle_id<>OLD.vehicle_id
           )
           OR (
               spare.source_kind='other-vehicle-system'
               AND donor.vehicle_id=OLD.vehicle_id
           ) THEN
            RAISE EXCEPTION
                'Vehicle repair donor-system source is inconsistent'
                USING ERRCODE='23514';
        END IF;
    END LOOP;
    RETURN NEW;
END;
$$;

CREATE TRIGGER vehicle_repair_resources_valid
BEFORE UPDATE ON vehicle_repair_receipt
FOR EACH ROW EXECUTE FUNCTION vehicle_validate_repair_resources();

CREATE OR REPLACE FUNCTION vehicle_sync_component_system_status()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.vehicle_component_id IS NOT NULL THEN
        UPDATE vehicle_component
        SET operational_status=CASE
            WHEN NEW.system_status='destroyed' THEN 'destroyed'
            WHEN NEW.system_status='disabled' THEN 'disabled'
            WHEN NEW.system_status='operational' THEN 'operational'
            ELSE 'degraded'
        END
        WHERE vehicle_component_id=NEW.vehicle_component_id;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER vehicle_system_component_status_synced
AFTER UPDATE OF system_status ON vehicle_system_state
FOR EACH ROW
WHEN (OLD.system_status IS DISTINCT FROM NEW.system_status)
EXECUTE FUNCTION vehicle_sync_component_system_status();
