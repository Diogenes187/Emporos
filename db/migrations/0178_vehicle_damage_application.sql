ALTER TABLE vehicle_vehicle
    ADD COLUMN armor_current smallint;

UPDATE vehicle_vehicle vehicle
SET armor_current=class.armor_rating
FROM vehicle_class class
WHERE class.vehicle_class_rule_id=vehicle.vehicle_class_rule_id;

ALTER TABLE vehicle_vehicle
    ALTER COLUMN armor_current SET NOT NULL,
    ADD CHECK (armor_current>=0);

CREATE OR REPLACE FUNCTION vehicle_validate_instance_state()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    class_hull smallint;
    class_structure smallint;
    class_armor smallint;
BEGIN
    SELECT hull_points,structure_points,armor_rating
    INTO class_hull,class_structure,class_armor
    FROM vehicle_class
    WHERE vehicle_class_rule_id=NEW.vehicle_class_rule_id;
    IF NEW.armor_current IS NULL THEN
        NEW.armor_current:=class_armor;
    END IF;
    IF NEW.hull_current>class_hull
       OR NEW.structure_current>class_structure
       OR NEW.armor_current>class_armor THEN
        RAISE EXCEPTION 'Vehicle state exceeds class maxima'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TABLE vehicle_system_state (
    vehicle_system_state_id bigint GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,
    vehicle_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    location_code text NOT NULL REFERENCES
        rule_vehicle_hit_location(location_code),
    system_identifier text NOT NULL CHECK (
        btrim(system_identifier)<>''
    ),
    vehicle_component_id bigint,
    class_armament_mount_id bigint REFERENCES
        vehicle_class_armament_mount(class_armament_mount_id),
    current_hits smallint NOT NULL DEFAULT 0 CHECK (
        current_hits>=0
    ),
    system_status text NOT NULL DEFAULT 'operational' CHECK (
        system_status IN (
            'operational','degraded','disabled','destroyed',
            'blinded','actions-lost'
        )
    ),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    FOREIGN KEY (vehicle_id,campaign_id)
        REFERENCES vehicle_vehicle(vehicle_id,campaign_id),
    FOREIGN KEY (vehicle_component_id,vehicle_id,campaign_id)
        REFERENCES vehicle_component(
            vehicle_component_id,vehicle_id,campaign_id
        ),
    UNIQUE (vehicle_system_state_id,vehicle_id,campaign_id),
    UNIQUE (vehicle_id,system_identifier),
    CHECK (num_nonnulls(
        vehicle_component_id,class_armament_mount_id
    )<=1),
    CHECK (
        (current_hits=0 AND system_status='operational')
        OR (current_hits>0 AND system_status<>'operational')
    )
);

CREATE OR REPLACE FUNCTION vehicle_validate_system_state()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    location_kind text;
    maximum_hits smallint;
    expected_status text;
    vehicle_class_id bigint;
    mount_class_id bigint;
BEGIN
    SELECT location.location_kind,location.maximum_staged_hits
    INTO location_kind,maximum_hits
    FROM rule_vehicle_hit_location location
    WHERE location.location_code=NEW.location_code;

    IF location_kind<>'system'
       OR NEW.current_hits>maximum_hits THEN
        RAISE EXCEPTION 'Invalid vehicle system damage state'
            USING ERRCODE='23514';
    END IF;

    IF NEW.current_hits>0 THEN
        SELECT stage.system_status INTO expected_status
        FROM rule_vehicle_system_hit_stage stage
        WHERE stage.location_code=NEW.location_code
          AND stage.hit_number=NEW.current_hits;
        IF expected_status IS DISTINCT FROM NEW.system_status THEN
            RAISE EXCEPTION 'Vehicle system status does not match hit stage'
                USING ERRCODE='23514';
        END IF;
    END IF;

    IF NEW.class_armament_mount_id IS NOT NULL THEN
        IF NEW.location_code<>'weapon' THEN
            RAISE EXCEPTION 'Armament targets must be weapon systems'
                USING ERRCODE='23514';
        END IF;
        SELECT vehicle.vehicle_class_rule_id,mount.vehicle_class_rule_id
        INTO vehicle_class_id,mount_class_id
        FROM vehicle_vehicle vehicle
        CROSS JOIN vehicle_class_armament_mount mount
        WHERE vehicle.vehicle_id=NEW.vehicle_id
          AND vehicle.campaign_id=NEW.campaign_id
          AND mount.class_armament_mount_id=
              NEW.class_armament_mount_id;
        IF vehicle_class_id IS DISTINCT FROM mount_class_id THEN
            RAISE EXCEPTION 'Armament target does not belong to vehicle class'
                USING ERRCODE='23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER vehicle_system_state_valid
BEFORE INSERT OR UPDATE ON vehicle_system_state
FOR EACH ROW EXECUTE FUNCTION vehicle_validate_system_state();

CREATE TABLE venc_damage_application (
    vehicle_damage_application_id bigint
        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    vehicle_attack_id bigint NOT NULL UNIQUE REFERENCES
        venc_attack(vehicle_attack_id),
    vehicle_engagement_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    target_vehicle_id bigint NOT NULL,
    target_vehicle_instance_id bigint NOT NULL,
    armor_before smallint NOT NULL CHECK (armor_before>=0),
    hull_before smallint NOT NULL CHECK (hull_before>=0),
    structure_before smallint NOT NULL CHECK (structure_before>=0),
    armor_after smallint NOT NULL CHECK (armor_after>=0),
    hull_after smallint NOT NULL CHECK (hull_after>=0),
    structure_after smallint NOT NULL CHECK (structure_after>=0),
    lifecycle_before text NOT NULL CHECK (
        lifecycle_before IN ('active','disabled')
    ),
    lifecycle_after text NOT NULL CHECK (
        lifecycle_after IN ('active','disabled','destroyed')
    ),
    finalized boolean NOT NULL DEFAULT false,
    applied_at timestamptz,
    FOREIGN KEY (
        target_vehicle_id,vehicle_engagement_id,campaign_id
    ) REFERENCES venc_vehicle(
        venc_vehicle_id,vehicle_engagement_id,campaign_id
    ),
    FOREIGN KEY (target_vehicle_instance_id,campaign_id)
        REFERENCES vehicle_vehicle(vehicle_id,campaign_id),
    UNIQUE (
        vehicle_damage_application_id,
        vehicle_engagement_id,campaign_id
    ),
    CHECK (
        (finalized AND applied_at IS NOT NULL)
        OR (NOT finalized AND applied_at IS NULL)
    )
);

CREATE TABLE venc_damage_location_hit (
    vehicle_damage_application_id bigint NOT NULL REFERENCES
        venc_damage_application(vehicle_damage_application_id),
    hit_order smallint NOT NULL CHECK (hit_order>0),
    packet_order smallint NOT NULL CHECK (packet_order>0),
    packet_instance smallint NOT NULL CHECK (packet_instance>0),
    hit_within_packet smallint NOT NULL CHECK (hit_within_packet>0),
    rolled_context text NOT NULL CHECK (
        rolled_context IN (
            'vehicle-external','vehicle-internal','robot-drone'
        )
    ),
    roll_total smallint NOT NULL CHECK (
        roll_total BETWEEN 2 AND 12
    ),
    rolled_option_order smallint NOT NULL CHECK (
        rolled_option_order>0
    ),
    rolled_location_code text NOT NULL REFERENCES
        rule_vehicle_hit_location(location_code),
    resolution_kind text NOT NULL CHECK (
        resolution_kind IN ('direct','overflow')
    ),
    resolved_context text NOT NULL CHECK (
        resolved_context IN (
            'vehicle-external','vehicle-internal','robot-drone'
        )
    ),
    location_code text NOT NULL REFERENCES
        rule_vehicle_hit_location(location_code),
    vehicle_system_state_id bigint,
    armor_before smallint NOT NULL CHECK (armor_before>=0),
    hull_before smallint NOT NULL CHECK (hull_before>=0),
    structure_before smallint NOT NULL CHECK (structure_before>=0),
    armor_after smallint NOT NULL CHECK (armor_after>=0),
    hull_after smallint NOT NULL CHECK (hull_after>=0),
    structure_after smallint NOT NULL CHECK (structure_after>=0),
    system_hits_before smallint CHECK (system_hits_before>=0),
    system_hits_after smallint CHECK (system_hits_after>0),
    system_status_after text CHECK (
        system_status_after IN (
            'degraded','disabled','destroyed',
            'blinded','actions-lost'
        )
    ),
    occupant_damage integer CHECK (occupant_damage>=0),
    cargo_affected boolean NOT NULL DEFAULT false,
    PRIMARY KEY (vehicle_damage_application_id,hit_order),
    UNIQUE (
        vehicle_damage_application_id,packet_order,
        packet_instance,hit_within_packet
    ),
    CHECK (
        num_nonnulls(
            system_hits_before,system_hits_after,
            system_status_after
        )=CASE
            WHEN vehicle_system_state_id IS NULL THEN 0
            ELSE 3
        END
    )
);

CREATE OR REPLACE FUNCTION venc_validate_damage_application_identity()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    attack_row venc_attack%ROWTYPE;
    participant_vehicle bigint;
    current_state record;
BEGIN
    SELECT * INTO attack_row
    FROM venc_attack
    WHERE vehicle_attack_id=NEW.vehicle_attack_id;
    SELECT vehicle_id INTO participant_vehicle
    FROM venc_vehicle
    WHERE venc_vehicle_id=NEW.target_vehicle_id
      AND vehicle_engagement_id=NEW.vehicle_engagement_id
      AND campaign_id=NEW.campaign_id;
    SELECT armor_current,hull_current,structure_current,
           lifecycle_status
    INTO current_state
    FROM vehicle_vehicle
    WHERE vehicle_id=NEW.target_vehicle_instance_id
      AND campaign_id=NEW.campaign_id;

    IF NOT attack_row.finalized OR NOT attack_row.hit
       OR attack_row.target_vehicle_id<>NEW.target_vehicle_id
       OR attack_row.vehicle_engagement_id<>
          NEW.vehicle_engagement_id
       OR attack_row.campaign_id<>NEW.campaign_id
       OR participant_vehicle<>NEW.target_vehicle_instance_id
       OR current_state.armor_current<>NEW.armor_before
       OR current_state.hull_current<>NEW.hull_before
       OR current_state.structure_current<>NEW.structure_before
       OR current_state.lifecycle_status<>NEW.lifecycle_before THEN
        RAISE EXCEPTION 'Vehicle damage application identity is inconsistent'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER venc_damage_application_identity_valid
BEFORE INSERT ON venc_damage_application
FOR EACH ROW EXECUTE FUNCTION
    venc_validate_damage_application_identity();

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
    hit record;
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
              FROM venc_damage_location_hit hit
              WHERE hit.vehicle_damage_application_id=
                    OLD.vehicle_damage_application_id
                AND hit.packet_order=packet.packet_order
                AND hit.packet_instance=
                    packet_instance.packet_instance
                AND hit.hit_within_packet=
                    hit_within_packet.hit_within_packet
          )
    ) INTO packet_mismatch;
    IF attack_damage IS NULL OR actual_hits<>expected_hits
       OR packet_mismatch THEN
        RAISE EXCEPTION 'Vehicle damage hit plan does not reconcile'
            USING ERRCODE='23514';
    END IF;

    FOR hit IN
        SELECT *
        FROM venc_damage_location_hit
        WHERE vehicle_damage_application_id=
              OLD.vehicle_damage_application_id
        ORDER BY hit_order
    LOOP
        PERFORM 1
        FROM rule_vehicle_hit_location_roll_option option
        WHERE option.target_context=hit.rolled_context
          AND option.roll_total=hit.roll_total
          AND option.option_order=hit.rolled_option_order
          AND option.location_code=hit.rolled_location_code;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'Vehicle damage roll does not match hit matrix'
                USING ERRCODE='23514';
        END IF;

        IF hit.resolution_kind='direct' THEN
            IF hit.location_code<>hit.rolled_location_code
               OR hit.resolved_context<>hit.rolled_context
               OR (
                   hit.location_code='hull'
                   AND hull_state=0
               ) THEN
                RAISE EXCEPTION 'Direct vehicle damage changed location'
                    USING ERRCODE='23514';
            END IF;
        ELSE
            SELECT overflow.overflow_location_code
            INTO overflow_location
            FROM rule_vehicle_location_overflow overflow
            WHERE overflow.location_code=hit.rolled_location_code
              AND overflow.target_context IN (
                  hit.rolled_context,'any'
              );
            IF overflow_location IS NULL
               AND hit.rolled_location_code='hull'
               AND hit.rolled_context='vehicle-external' THEN
                PERFORM 1
                FROM rule_vehicle_hit_location_roll_option option
                WHERE option.target_context='vehicle-internal'
                  AND option.roll_total=hit.roll_total
                  AND option.option_order=
                      hit.rolled_option_order
                  AND option.location_code=hit.location_code;
                IF NOT FOUND OR hull_state<>0
                   OR hit.resolved_context<>'vehicle-internal' THEN
                    RAISE EXCEPTION 'Invalid internal vehicle overflow'
                        USING ERRCODE='23514';
                END IF;
            ELSIF hit.location_code IS DISTINCT FROM overflow_location THEN
                RAISE EXCEPTION 'Invalid vehicle damage overflow target'
                    USING ERRCODE='23514';
            END IF;
        END IF;

        SELECT * INTO location
        FROM rule_vehicle_hit_location
        WHERE location_code=hit.location_code;
        IF hit.armor_before<>armor_state
           OR hit.hull_before<>hull_state
           OR hit.structure_before<>structure_state THEN
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
        IF hit.armor_after<>armor_state
           OR hit.hull_after<>hull_state
           OR hit.structure_after<>structure_state
           OR hit.occupant_damage IS DISTINCT FROM (
              CASE WHEN location.receives_vehicle_damage_amount
                   THEN attack_damage ELSE NULL END)
           OR hit.cargo_affected<>location.cargo_is_at_risk THEN
            RAISE EXCEPTION 'Vehicle damage effect does not match location'
                USING ERRCODE='23514';
        END IF;

        IF location.location_kind='system' THEN
            SELECT * INTO system_state
            FROM vehicle_system_state
            WHERE vehicle_system_state_id=
                  hit.vehicle_system_state_id
              AND vehicle_id=OLD.target_vehicle_instance_id
              AND campaign_id=OLD.campaign_id
            FOR UPDATE;
            SELECT system_status INTO stage_status
            FROM rule_vehicle_system_hit_stage
            WHERE location_code=hit.location_code
              AND hit_number=system_state.current_hits+1;
            IF system_state.location_code<>hit.location_code
               OR hit.system_hits_before<>
                  system_state.current_hits
               OR hit.system_hits_after<>
                  system_state.current_hits+1
               OR hit.system_status_after IS DISTINCT FROM
                  stage_status THEN
                RAISE EXCEPTION 'Vehicle system hit stage is inconsistent'
                    USING ERRCODE='23514';
            END IF;
            UPDATE vehicle_system_state
            SET current_hits=hit.system_hits_after,
                system_status=hit.system_status_after,
                updated_at=NEW.applied_at
            WHERE vehicle_system_state_id=
                  hit.vehicle_system_state_id;
            IF system_state.vehicle_component_id IS NOT NULL THEN
                UPDATE vehicle_component
                SET operational_status=CASE
                    WHEN hit.system_status_after='destroyed'
                        THEN 'destroyed'
                    WHEN hit.system_status_after='disabled'
                        THEN 'disabled'
                    ELSE 'degraded'
                END
                WHERE vehicle_component_id=
                      system_state.vehicle_component_id;
            END IF;
        ELSIF hit.vehicle_system_state_id IS NOT NULL THEN
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

CREATE TRIGGER venc_damage_application_finalization_valid
BEFORE UPDATE OR DELETE ON venc_damage_application
FOR EACH ROW EXECUTE FUNCTION
    venc_finalize_damage_application();

CREATE OR REPLACE FUNCTION venc_damage_hit_open()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    application_id bigint;
    application_finalized boolean;
BEGIN
    application_id:=CASE
        WHEN TG_OP='DELETE'
            THEN OLD.vehicle_damage_application_id
        ELSE NEW.vehicle_damage_application_id
    END;
    SELECT finalized INTO application_finalized
    FROM venc_damage_application
    WHERE vehicle_damage_application_id=application_id;
    IF application_finalized THEN
        RAISE EXCEPTION 'Finalized vehicle damage hits are immutable'
            USING ERRCODE='23514';
    END IF;
    RETURN CASE WHEN TG_OP='DELETE' THEN OLD ELSE NEW END;
END;
$$;

CREATE TRIGGER venc_damage_hit_open
BEFORE INSERT OR UPDATE OR DELETE ON venc_damage_location_hit
FOR EACH ROW EXECUTE FUNCTION venc_damage_hit_open();

CREATE VIEW vehicle_current_damage_state AS
SELECT vehicle.vehicle_id,vehicle.campaign_id,
       vehicle.lifecycle_status,vehicle.armor_current,
       class.armor_rating AS armor_maximum,
       vehicle.hull_current,class.hull_points AS hull_maximum,
       vehicle.structure_current,
       class.structure_points AS structure_maximum,
       count(system.vehicle_system_state_id)
           FILTER (WHERE system.current_hits>0) AS damaged_systems,
       coalesce(sum(system.current_hits),0) AS system_hits
FROM vehicle_vehicle vehicle
JOIN vehicle_class class
  ON class.vehicle_class_rule_id=vehicle.vehicle_class_rule_id
LEFT JOIN vehicle_system_state system
  ON system.vehicle_id=vehicle.vehicle_id
 AND system.campaign_id=vehicle.campaign_id
GROUP BY vehicle.vehicle_id,vehicle.campaign_id,
         vehicle.lifecycle_status,vehicle.armor_current,
         class.armor_rating,vehicle.hull_current,
         class.hull_points,vehicle.structure_current,
         class.structure_points;
