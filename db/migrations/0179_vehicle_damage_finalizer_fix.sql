CREATE OR REPLACE FUNCTION venc_finalize_damage_application()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    attack_damage integer;
    expected_hits integer;
    actual_hits integer;
    packet_mismatch boolean;
    armor_state smallint:=OLD.armor_before;
    hull_state smallint:=OLD.hull_before;
    structure_state smallint:=OLD.structure_before;
    damage_hit record;
    location record;
    overflow_location text;
    stage_status text;
    system_state record;
BEGIN
    IF OLD.finalized OR NOT NEW.finalized OR NEW.applied_at IS NULL THEN
        RAISE EXCEPTION 'Finalized vehicle damage applications are immutable'
            USING ERRCODE='23514';
    END IF;

    SELECT penetrating_damage INTO attack_damage
    FROM venc_attack
    WHERE vehicle_attack_id=OLD.vehicle_attack_id
      AND finalized;
    SELECT sum(location_hit_count*packet_quantity)
    INTO expected_hits
    FROM venc_attack_damage_packet
    WHERE vehicle_attack_id=OLD.vehicle_attack_id;
    SELECT count(*) INTO actual_hits
    FROM venc_damage_location_hit
    WHERE vehicle_damage_application_id=
          OLD.vehicle_damage_application_id;
    SELECT EXISTS (
        SELECT 1
        FROM venc_attack_damage_packet packet
        CROSS JOIN LATERAL generate_series(
            1,packet.packet_quantity
        ) packet_instance
        CROSS JOIN LATERAL generate_series(
            1,packet.location_hit_count
        ) hit_within_packet
        WHERE packet.vehicle_attack_id=OLD.vehicle_attack_id
          AND NOT EXISTS (
              SELECT 1
              FROM venc_damage_location_hit receipt_hit
              WHERE receipt_hit.vehicle_damage_application_id=
                    OLD.vehicle_damage_application_id
                AND receipt_hit.packet_order=packet.packet_order
                AND receipt_hit.packet_instance=
                    packet_instance.packet_instance
                AND receipt_hit.hit_within_packet=
                    hit_within_packet.hit_within_packet
          )
    ) INTO packet_mismatch;
    IF attack_damage IS NULL OR actual_hits<>expected_hits
       OR packet_mismatch THEN
        RAISE EXCEPTION 'Vehicle damage hit plan does not reconcile'
            USING ERRCODE='23514';
    END IF;

    FOR damage_hit IN
        SELECT *
        FROM venc_damage_location_hit
        WHERE vehicle_damage_application_id=
              OLD.vehicle_damage_application_id
        ORDER BY hit_order
    LOOP
        PERFORM 1
        FROM rule_vehicle_hit_location_roll_option option
        WHERE option.target_context=damage_hit.rolled_context
          AND option.roll_total=damage_hit.roll_total
          AND option.option_order=damage_hit.rolled_option_order
          AND option.location_code=damage_hit.rolled_location_code;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'Vehicle damage roll does not match hit matrix'
                USING ERRCODE='23514';
        END IF;

        IF damage_hit.resolution_kind='direct' THEN
            IF damage_hit.location_code<>
               damage_hit.rolled_location_code
               OR damage_hit.resolved_context<>
                  damage_hit.rolled_context
               OR (
                   damage_hit.location_code='hull'
                   AND hull_state=0
               ) THEN
                RAISE EXCEPTION 'Direct vehicle damage changed location'
                    USING ERRCODE='23514';
            END IF;
        ELSE
            SELECT overflow.overflow_location_code
            INTO overflow_location
            FROM rule_vehicle_location_overflow overflow
            WHERE overflow.location_code=
                  damage_hit.rolled_location_code
              AND overflow.target_context IN (
                  damage_hit.rolled_context,'any'
              );
            IF overflow_location IS NULL
               AND damage_hit.rolled_location_code='hull'
               AND damage_hit.rolled_context='vehicle-external' THEN
                PERFORM 1
                FROM rule_vehicle_hit_location_roll_option option
                WHERE option.target_context='vehicle-internal'
                  AND option.roll_total=damage_hit.roll_total
                  AND option.option_order=
                      damage_hit.rolled_option_order
                  AND option.location_code=
                      damage_hit.location_code;
                IF NOT FOUND OR hull_state<>0
                   OR damage_hit.resolved_context<>
                      'vehicle-internal' THEN
                    RAISE EXCEPTION 'Invalid internal vehicle overflow'
                        USING ERRCODE='23514';
                END IF;
            ELSIF damage_hit.location_code IS DISTINCT FROM
                  overflow_location THEN
                RAISE EXCEPTION 'Invalid vehicle damage overflow target'
                    USING ERRCODE='23514';
            END IF;
        END IF;

        SELECT * INTO location
        FROM rule_vehicle_hit_location
        WHERE location_code=damage_hit.location_code;
        IF damage_hit.armor_before<>armor_state
           OR damage_hit.hull_before<>hull_state
           OR damage_hit.structure_before<>structure_state THEN
            RAISE EXCEPTION 'Vehicle damage state chain is discontinuous'
                USING ERRCODE='23514';
        END IF;

        armor_state:=greatest(
            armor_state-location.direct_armor_loss,0
        );
        hull_state:=greatest(
            hull_state-location.direct_hull_loss,0
        );
        structure_state:=greatest(
            structure_state-location.direct_structure_loss,0
        );
        IF damage_hit.armor_after<>armor_state
           OR damage_hit.hull_after<>hull_state
           OR damage_hit.structure_after<>structure_state
           OR damage_hit.occupant_damage IS DISTINCT FROM (
              CASE WHEN location.receives_vehicle_damage_amount
                   THEN attack_damage ELSE NULL END)
           OR damage_hit.cargo_affected<>
              location.cargo_is_at_risk THEN
            RAISE EXCEPTION 'Vehicle damage effect does not match location'
                USING ERRCODE='23514';
        END IF;

        IF location.location_kind='system' THEN
            SELECT * INTO system_state
            FROM vehicle_system_state
            WHERE vehicle_system_state_id=
                  damage_hit.vehicle_system_state_id
              AND vehicle_id=OLD.target_vehicle_instance_id
              AND campaign_id=OLD.campaign_id
            FOR UPDATE;
            SELECT system_status INTO stage_status
            FROM rule_vehicle_system_hit_stage
            WHERE location_code=damage_hit.location_code
              AND hit_number=system_state.current_hits+1;
            IF system_state.location_code<>
               damage_hit.location_code
               OR damage_hit.system_hits_before<>
                  system_state.current_hits
               OR damage_hit.system_hits_after<>
                  system_state.current_hits+1
               OR damage_hit.system_status_after IS DISTINCT FROM
                  stage_status THEN
                RAISE EXCEPTION 'Vehicle system hit stage is inconsistent'
                    USING ERRCODE='23514';
            END IF;
            UPDATE vehicle_system_state
            SET current_hits=damage_hit.system_hits_after,
                system_status=damage_hit.system_status_after,
                updated_at=NEW.applied_at
            WHERE vehicle_system_state_id=
                  damage_hit.vehicle_system_state_id;
            IF system_state.vehicle_component_id IS NOT NULL THEN
                UPDATE vehicle_component
                SET operational_status=CASE
                    WHEN damage_hit.system_status_after='destroyed'
                        THEN 'destroyed'
                    WHEN damage_hit.system_status_after='disabled'
                        THEN 'disabled'
                    ELSE 'degraded'
                END
                WHERE vehicle_component_id=
                      system_state.vehicle_component_id;
            END IF;
        ELSIF damage_hit.vehicle_system_state_id IS NOT NULL THEN
            RAISE EXCEPTION 'Non-system damage names a vehicle system'
                USING ERRCODE='23514';
        END IF;
    END LOOP;

    IF NEW.armor_after<>armor_state
       OR NEW.hull_after<>hull_state
       OR NEW.structure_after<>structure_state
       OR NEW.lifecycle_after<>(CASE
           WHEN structure_state=0 THEN 'destroyed'
           WHEN hull_state=0 THEN 'disabled'
           ELSE OLD.lifecycle_before
       END) THEN
        RAISE EXCEPTION 'Vehicle damage final state does not reconcile'
            USING ERRCODE='23514';
    END IF;

    UPDATE vehicle_vehicle
    SET armor_current=armor_state,
        hull_current=hull_state,
        structure_current=structure_state,
        lifecycle_status=NEW.lifecycle_after,
        ended_at=CASE
            WHEN NEW.lifecycle_after='destroyed'
                THEN NEW.applied_at
            ELSE NULL
        END,
        concurrency_version=concurrency_version+1
    WHERE vehicle_id=OLD.target_vehicle_instance_id
      AND campaign_id=OLD.campaign_id
      AND armor_current=OLD.armor_before
      AND hull_current=OLD.hull_before
      AND structure_current=OLD.structure_before
      AND lifecycle_status=OLD.lifecycle_before;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Vehicle state changed before damage application'
            USING ERRCODE='40001';
    END IF;
    RETURN NEW;
END;
$$;
