ALTER TABLE venc_damage_location_hit
    ADD COLUMN rolled_vehicle_system_state_id bigint REFERENCES
        vehicle_system_state(vehicle_system_state_id);

CREATE OR REPLACE FUNCTION venc_validate_damage_hit_targets()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    damage_hit record;
    rolled_kind text;
    resolved_kind text;
    rolled_system record;
    resolved_system record;
    maximum_hits smallint;
BEGIN
    IF OLD.finalized OR NOT NEW.finalized THEN
        RETURN NEW;
    END IF;

    FOR damage_hit IN
        SELECT *
        FROM venc_damage_location_hit
        WHERE vehicle_damage_application_id=
              OLD.vehicle_damage_application_id
        ORDER BY hit_order
    LOOP
        SELECT location_kind,maximum_staged_hits
        INTO rolled_kind,maximum_hits
        FROM rule_vehicle_hit_location
        WHERE location_code=damage_hit.rolled_location_code;
        SELECT location_kind INTO resolved_kind
        FROM rule_vehicle_hit_location
        WHERE location_code=damage_hit.location_code;

        IF rolled_kind='system' THEN
            SELECT * INTO rolled_system
            FROM vehicle_system_state
            WHERE vehicle_system_state_id=
                  damage_hit.rolled_vehicle_system_state_id
              AND vehicle_id=OLD.target_vehicle_instance_id
              AND campaign_id=OLD.campaign_id;
            IF NOT FOUND
               OR rolled_system.location_code<>
                  damage_hit.rolled_location_code THEN
                RAISE EXCEPTION
                    'Rolled vehicle system target is inconsistent'
                    USING ERRCODE='23514';
            END IF;
            IF damage_hit.resolution_kind='overflow'
               AND rolled_system.current_hits<maximum_hits THEN
                RAISE EXCEPTION
                    'Vehicle system cannot overflow before final stage'
                    USING ERRCODE='23514';
            END IF;
        ELSIF damage_hit.rolled_vehicle_system_state_id
              IS NOT NULL THEN
            RAISE EXCEPTION
                'Non-system roll names a vehicle system'
                USING ERRCODE='23514';
        END IF;

        IF resolved_kind='system' THEN
            SELECT * INTO resolved_system
            FROM vehicle_system_state
            WHERE vehicle_system_state_id=
                  damage_hit.vehicle_system_state_id
              AND vehicle_id=OLD.target_vehicle_instance_id
              AND campaign_id=OLD.campaign_id;
            IF NOT FOUND
               OR resolved_system.location_code<>
                  damage_hit.location_code THEN
                RAISE EXCEPTION
                    'Resolved vehicle system target is inconsistent'
                    USING ERRCODE='23514';
            END IF;
            IF damage_hit.resolution_kind='direct'
               AND damage_hit.vehicle_system_state_id<>
                   damage_hit.rolled_vehicle_system_state_id THEN
                RAISE EXCEPTION
                    'Direct hit changed vehicle system identity'
                    USING ERRCODE='23514';
            END IF;
        ELSIF damage_hit.vehicle_system_state_id IS NOT NULL THEN
            RAISE EXCEPTION
                'Non-system damage names a vehicle system'
                USING ERRCODE='23514';
        END IF;
    END LOOP;
    RETURN NEW;
END;
$$;

CREATE TRIGGER venc_damage_application_damage_targets_valid
BEFORE UPDATE ON venc_damage_application
FOR EACH ROW EXECUTE FUNCTION
    venc_validate_damage_hit_targets();
