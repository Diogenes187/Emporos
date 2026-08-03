ALTER TABLE vehicle_system_state
    ADD COLUMN temporary_restore_until timestamptz,
    ADD COLUMN temporary_restore_receipt_id bigint;

CREATE TABLE vehicle_repair_receipt (
    vehicle_repair_receipt_id bigint
        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    vehicle_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    repair_rule_id bigint NOT NULL REFERENCES
        rule_vehicle_repair_category(repair_rule_id),
    repair_category text NOT NULL CHECK (
        repair_category IN ('system','hull','structure')
    ),
    repair_method text NOT NULL CHECK (
        repair_method IN ('full','jury-rig')
    ),
    vehicle_system_state_id bigint,
    repairing_actor_id bigint,
    skill_rule_id bigint REFERENCES rule_rule(rule_id),
    difficulty_rule_id bigint REFERENCES
        rule_difficulty(rule_id),
    check_roll integer,
    check_total integer,
    target_number integer,
    succeeded boolean NOT NULL,
    integrity_points_restored smallint NOT NULL DEFAULT 0 CHECK (
        integrity_points_restored>=0
    ),
    system_hits_before smallint CHECK (system_hits_before>0),
    system_hits_after smallint CHECK (system_hits_after>=0),
    system_status_before text CHECK (
        system_status_before IN (
            'degraded','disabled','destroyed',
            'blinded','actions-lost'
        )
    ),
    system_status_after text CHECK (
        system_status_after IN (
            'operational','degraded','disabled','destroyed',
            'blinded','actions-lost'
        )
    ),
    armor_before smallint NOT NULL CHECK (armor_before>=0),
    hull_before smallint NOT NULL CHECK (hull_before>=0),
    structure_before smallint NOT NULL CHECK (structure_before>=0),
    armor_after smallint NOT NULL CHECK (armor_after>=0),
    hull_after smallint NOT NULL CHECK (hull_after>=0),
    structure_after smallint NOT NULL CHECK (structure_after>=0),
    lifecycle_before text NOT NULL CHECK (
        lifecycle_before IN ('active','disabled','destroyed')
    ),
    lifecycle_after text NOT NULL CHECK (
        lifecycle_after IN ('active','disabled','destroyed')
    ),
    work_duration_hours integer CHECK (work_duration_hours>0),
    temporary_restore_until timestamptz,
    workshop_used boolean NOT NULL,
    specialist_materials_used boolean NOT NULL,
    spare_part_hits_consumed smallint NOT NULL DEFAULT 0 CHECK (
        spare_part_hits_consumed>=0
    ),
    cost_basis_minor numeric(18,2) CHECK (cost_basis_minor>0),
    repair_cost_minor numeric(18,2) NOT NULL DEFAULT 0 CHECK (
        repair_cost_minor>=0
    ),
    source_command_id bigint REFERENCES cmd_command(command_id),
    finalized boolean NOT NULL DEFAULT false,
    applied_at timestamptz,
    FOREIGN KEY (vehicle_id,campaign_id)
        REFERENCES vehicle_vehicle(vehicle_id,campaign_id),
    FOREIGN KEY (
        vehicle_system_state_id,vehicle_id,campaign_id
    ) REFERENCES vehicle_system_state(
        vehicle_system_state_id,vehicle_id,campaign_id
    ),
    FOREIGN KEY (repairing_actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    UNIQUE (vehicle_repair_receipt_id,campaign_id),
    CHECK (
        (repair_category='system'
         AND vehicle_system_state_id IS NOT NULL
         AND integrity_points_restored=0
         AND num_nonnulls(
             system_hits_before,system_hits_after,
             system_status_before,system_status_after
         )=4)
        OR
        (repair_category IN ('hull','structure')
         AND vehicle_system_state_id IS NULL
         AND integrity_points_restored>0
         AND num_nonnulls(
             system_hits_before,system_hits_after,
             system_status_before,system_status_after
         )=0)
    ),
    CHECK (
        (check_roll IS NULL AND check_total IS NULL)
        OR (check_roll IS NOT NULL AND check_total IS NOT NULL)
    ),
    CHECK (
        (target_number IS NULL)
        OR (check_total IS NOT NULL
            AND succeeded=(check_total>=target_number))
    ),
    CHECK (
        (repair_method='jury-rig'
         AND repair_category='system'
         AND temporary_restore_until IS NOT NULL)
        OR
        (repair_method='full'
         AND temporary_restore_until IS NULL)
    ),
    CHECK (
        (finalized AND applied_at IS NOT NULL)
        OR (NOT finalized AND applied_at IS NULL)
    )
);

ALTER TABLE vehicle_system_state
    ADD CONSTRAINT vehicle_system_temporary_repair_receipt_fk
    FOREIGN KEY (temporary_restore_receipt_id,campaign_id)
    REFERENCES vehicle_repair_receipt(
        vehicle_repair_receipt_id,campaign_id
    ),
    ADD CHECK (
        num_nonnulls(
            temporary_restore_until,
            temporary_restore_receipt_id
        ) IN (0,2)
    );

CREATE TABLE vehicle_repair_modifier (
    vehicle_repair_receipt_id bigint NOT NULL REFERENCES
        vehicle_repair_receipt(vehicle_repair_receipt_id),
    modifier_order smallint NOT NULL CHECK (modifier_order>0),
    modifier_code text NOT NULL CHECK (
        modifier_code IN (
            'skill','characteristic','tools',
            'parts-quality','circumstance'
        )
    ),
    modifier_value integer NOT NULL,
    source_reference text CHECK (
        source_reference IS NULL
        OR btrim(source_reference)<>''
    ),
    PRIMARY KEY (vehicle_repair_receipt_id,modifier_order),
    UNIQUE (vehicle_repair_receipt_id,modifier_code)
);

CREATE TABLE vehicle_repair_random_die (
    vehicle_repair_receipt_id bigint NOT NULL REFERENCES
        vehicle_repair_receipt(vehicle_repair_receipt_id),
    roll_kind text NOT NULL CHECK (
        roll_kind IN (
            'work-duration','operating-duration','repair-cost'
        )
    ),
    die_order smallint NOT NULL CHECK (die_order>0),
    die_sides smallint NOT NULL CHECK (die_sides>1),
    face_value smallint NOT NULL CHECK (
        face_value>0 AND face_value<=die_sides
    ),
    PRIMARY KEY (
        vehicle_repair_receipt_id,roll_kind,die_order
    )
);

CREATE TABLE vehicle_repair_spare_source (
    vehicle_repair_receipt_id bigint NOT NULL REFERENCES
        vehicle_repair_receipt(vehicle_repair_receipt_id),
    source_order smallint NOT NULL CHECK (source_order>0),
    source_kind text NOT NULL CHECK (
        source_kind IN (
            'scrap-yard','workshop','other-vehicle-system',
            'same-vehicle-system','cybernetic','other'
        )
    ),
    donor_vehicle_system_state_id bigint REFERENCES
        vehicle_system_state(vehicle_system_state_id),
    source_reference text CHECK (
        source_reference IS NULL
        OR btrim(source_reference)<>''
    ),
    spare_part_hits smallint NOT NULL CHECK (spare_part_hits>0),
    PRIMARY KEY (vehicle_repair_receipt_id,source_order),
    CHECK (
        (
            source_kind IN (
                'other-vehicle-system','same-vehicle-system'
            )
            AND donor_vehicle_system_state_id IS NOT NULL
        )
        OR (
            source_kind NOT IN (
                'other-vehicle-system','same-vehicle-system'
            )
            AND donor_vehicle_system_state_id IS NULL
            AND source_reference IS NOT NULL
        )
    )
);

CREATE OR REPLACE FUNCTION vehicle_validate_repair_identity()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    current_vehicle record;
    current_system record;
    category_code text;
BEGIN
    SELECT vehicle.armor_current,vehicle.hull_current,
           vehicle.structure_current,vehicle.lifecycle_status,
           class.construction_cost_minor
    INTO current_vehicle
    FROM vehicle_vehicle vehicle
    JOIN vehicle_class class
      ON class.vehicle_class_rule_id=
         vehicle.vehicle_class_rule_id
    WHERE vehicle.vehicle_id=NEW.vehicle_id
      AND vehicle.campaign_id=NEW.campaign_id;
    SELECT repair_category INTO category_code
    FROM rule_vehicle_repair_category
    WHERE repair_rule_id=NEW.repair_rule_id;

    IF category_code<>NEW.repair_category
       OR current_vehicle.armor_current<>NEW.armor_before
       OR current_vehicle.hull_current<>NEW.hull_before
       OR current_vehicle.structure_current<>
          NEW.structure_before
       OR current_vehicle.lifecycle_status<>
          NEW.lifecycle_before THEN
        RAISE EXCEPTION 'Vehicle repair identity is inconsistent'
            USING ERRCODE='23514';
    END IF;

    IF NEW.repair_category='structure'
       AND NEW.cost_basis_minor IS DISTINCT FROM
           current_vehicle.construction_cost_minor::numeric THEN
        RAISE EXCEPTION 'Structure repair cost basis is inconsistent'
            USING ERRCODE='23514';
    END IF;

    IF NEW.repair_category='system' THEN
        SELECT current_hits,system_status
        INTO current_system
        FROM vehicle_system_state
        WHERE vehicle_system_state_id=
              NEW.vehicle_system_state_id
          AND vehicle_id=NEW.vehicle_id
          AND campaign_id=NEW.campaign_id;
        IF current_system.current_hits IS DISTINCT FROM
           NEW.system_hits_before
           OR current_system.system_status IS DISTINCT FROM
              NEW.system_status_before THEN
            RAISE EXCEPTION 'Vehicle repair system state is inconsistent'
                USING ERRCODE='23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER vehicle_repair_identity_valid
BEFORE INSERT ON vehicle_repair_receipt
FOR EACH ROW EXECUTE FUNCTION vehicle_validate_repair_identity();

CREATE OR REPLACE FUNCTION vehicle_finalize_repair()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    repair_rule record;
    system_rule record;
    modifier_total integer;
    duration_total integer;
    duration_count integer;
    operating_total integer;
    operating_count integer;
    cost_total integer;
    cost_count integer;
    spare_total integer;
    expected_hull smallint:=OLD.hull_before;
    expected_structure smallint:=OLD.structure_before;
    expected_system_hits smallint;
    expected_system_status text;
    expected_lifecycle text;
    expected_target integer;
BEGIN
    IF TG_OP='DELETE' OR OLD.finalized
       OR NOT NEW.finalized OR NEW.applied_at IS NULL THEN
        RAISE EXCEPTION 'Finalized vehicle repairs are immutable'
            USING ERRCODE='23514';
    END IF;
    IF (to_jsonb(NEW)-'finalized'-'applied_at')
       IS DISTINCT FROM
       (to_jsonb(OLD)-'finalized'-'applied_at') THEN
        RAISE EXCEPTION 'Repair body cannot change during finalization'
            USING ERRCODE='23514';
    END IF;

    SELECT * INTO repair_rule
    FROM rule_vehicle_repair_category
    WHERE repair_rule_id=OLD.repair_rule_id;
    SELECT coalesce(sum(modifier_value),0)
    INTO modifier_total
    FROM vehicle_repair_modifier
    WHERE vehicle_repair_receipt_id=
          OLD.vehicle_repair_receipt_id;
    SELECT coalesce(sum(face_value),0),count(*)
    INTO duration_total,duration_count
    FROM vehicle_repair_random_die
    WHERE vehicle_repair_receipt_id=
          OLD.vehicle_repair_receipt_id
      AND roll_kind='work-duration';
    SELECT coalesce(sum(face_value),0),count(*)
    INTO operating_total,operating_count
    FROM vehicle_repair_random_die
    WHERE vehicle_repair_receipt_id=
          OLD.vehicle_repair_receipt_id
      AND roll_kind='operating-duration';
    SELECT coalesce(sum(face_value),0),count(*)
    INTO cost_total,cost_count
    FROM vehicle_repair_random_die
    WHERE vehicle_repair_receipt_id=
          OLD.vehicle_repair_receipt_id
      AND roll_kind='repair-cost';
    SELECT coalesce(sum(spare_part_hits),0)
    INTO spare_total
    FROM vehicle_repair_spare_source
    WHERE vehicle_repair_receipt_id=
          OLD.vehicle_repair_receipt_id;

    IF OLD.repair_method='jury-rig' THEN
        SELECT * INTO system_rule
        FROM rule_vehicle_system_repair_state
        WHERE system_damage_state='damaged';
        IF NOT system_rule.may_be_jury_rigged
           OR OLD.system_status_before='destroyed'
           OR OLD.system_hits_after<>OLD.system_hits_before
           OR OLD.system_status_after<>OLD.system_status_before
           OR OLD.check_roll IS NOT NULL
           OR OLD.work_duration_hours IS NOT NULL
           OR duration_count<>0 OR cost_count<>0
           OR operating_count<>
              system_rule.jury_rig_duration_dice_count
           OR OLD.temporary_restore_until<>
              NEW.applied_at+
              make_interval(hours=>operating_total)
           OR OLD.spare_part_hits_consumed<>0
           OR spare_total<>0
           OR OLD.repair_cost_minor<>0
           OR OLD.workshop_used
           OR OLD.specialist_materials_used THEN
            RAISE EXCEPTION 'Vehicle jury-rig receipt does not reconcile'
                USING ERRCODE='23514';
        END IF;
    ELSE
        IF duration_count<>(
           repair_rule.time_dice_count*CASE
               WHEN repair_rule.time_basis='per-damage-point'
                   THEN OLD.integrity_points_restored
               ELSE 1
           END)
           OR EXISTS (
               SELECT 1 FROM vehicle_repair_random_die
               WHERE vehicle_repair_receipt_id=
                     OLD.vehicle_repair_receipt_id
                 AND roll_kind='work-duration'
                 AND die_sides<>repair_rule.time_die_sides
           )
           OR OLD.work_duration_hours<>
              duration_total*
              repair_rule.time_multiplier_hours THEN
            RAISE EXCEPTION 'Vehicle repair duration does not reconcile'
                USING ERRCODE='23514';
        END IF;

        IF repair_rule.skill_requirement='none' THEN
            IF OLD.skill_rule_id IS NOT NULL
               OR OLD.check_roll IS NOT NULL
               OR NOT OLD.succeeded THEN
                RAISE EXCEPTION 'Skill-free vehicle repair is inconsistent'
                    USING ERRCODE='23514';
            END IF;
        ELSE
            IF OLD.skill_rule_id IS NULL
               OR OLD.check_roll IS NULL
               OR OLD.check_total<>
                  OLD.check_roll+modifier_total
               OR (
                   repair_rule.skill_requirement='fixed'
                   AND OLD.skill_rule_id<>
                       repair_rule.fixed_skill_rule_id
               )
               OR OLD.difficulty_rule_id IS DISTINCT FROM
                  repair_rule.difficulty_rule_id THEN
                RAISE EXCEPTION 'Vehicle repair check does not reconcile'
                    USING ERRCODE='23514';
            END IF;
            IF repair_rule.difficulty_rule_id IS NOT NULL THEN
                SELECT check_system.target_number+
                       difficulty.modifier
                INTO expected_target
                FROM rule_check_system check_system
                CROSS JOIN rule_difficulty difficulty
                WHERE difficulty.rule_id=
                      repair_rule.difficulty_rule_id;
                IF OLD.target_number IS DISTINCT FROM
                   expected_target THEN
                    RAISE EXCEPTION
                        'Vehicle repair target number does not reconcile'
                        USING ERRCODE='23514';
                END IF;
            ELSIF OLD.target_number IS NOT NULL THEN
                RAISE EXCEPTION
                    'Source-unspecified repair difficulty gained a target'
                    USING ERRCODE='23514';
            END IF;
        END IF;

        IF OLD.repair_category='system' THEN
            SELECT * INTO system_rule
            FROM rule_vehicle_system_repair_state
            WHERE system_damage_state=CASE
                WHEN OLD.system_status_before='destroyed'
                    THEN 'destroyed'
                ELSE 'damaged'
            END;
            IF system_rule.workshop_required<>OLD.workshop_used
               OR system_rule.specialist_materials_required<>
                  OLD.specialist_materials_used THEN
                RAISE EXCEPTION 'Vehicle system repair facilities mismatch'
                    USING ERRCODE='23514';
            END IF;
            IF OLD.system_status_before='destroyed' THEN
                IF cost_count<>system_rule.repair_cost_dice_count
                   OR EXISTS (
                       SELECT 1 FROM vehicle_repair_random_die
                       WHERE vehicle_repair_receipt_id=
                             OLD.vehicle_repair_receipt_id
                         AND roll_kind='repair-cost'
                         AND die_sides<>
                             system_rule.repair_cost_die_sides
                   )
                   OR OLD.cost_basis_minor IS NULL
                   OR OLD.repair_cost_minor<>
                      OLD.cost_basis_minor*cost_total*
                      system_rule.repair_cost_fraction_per_die_point
                   OR spare_total<>0
                   OR OLD.spare_part_hits_consumed<>0 THEN
                    RAISE EXCEPTION
                        'Destroyed system repair cost does not reconcile'
                        USING ERRCODE='23514';
                END IF;
                expected_system_hits:=CASE
                    WHEN OLD.succeeded THEN 0
                    ELSE OLD.system_hits_before
                END;
            ELSE
                IF cost_count<>0 OR OLD.repair_cost_minor<>0
                   OR OLD.cost_basis_minor IS NOT NULL
                   OR OLD.spare_part_hits_consumed<>
                      repair_rule.spare_part_hits_consumed
                   OR spare_total<>
                      repair_rule.spare_part_hits_consumed THEN
                    RAISE EXCEPTION
                        'Damaged system repair parts do not reconcile'
                        USING ERRCODE='23514';
                END IF;
                expected_system_hits:=CASE
                    WHEN OLD.succeeded
                        THEN OLD.system_hits_before-1
                    ELSE OLD.system_hits_before
                END;
            END IF;
            SELECT coalesce(
                (
                    SELECT system_status
                    FROM rule_vehicle_system_hit_stage
                    WHERE location_code=system.location_code
                      AND hit_number=expected_system_hits
                ),
                'operational'
            )
            INTO expected_system_status
            FROM vehicle_system_state system
            WHERE system.vehicle_system_state_id=
                  OLD.vehicle_system_state_id;
            IF OLD.system_hits_after<>expected_system_hits
               OR OLD.system_status_after<>
                  expected_system_status THEN
                RAISE EXCEPTION 'Vehicle system repair result mismatch'
                    USING ERRCODE='23514';
            END IF;
        ELSIF OLD.repair_category='hull' THEN
            IF OLD.workshop_used
               OR OLD.specialist_materials_used
               OR cost_count<>0 OR OLD.repair_cost_minor<>0
               OR OLD.cost_basis_minor IS NOT NULL
               OR OLD.spare_part_hits_consumed<>
                  repair_rule.spare_part_hits_consumed
               OR spare_total<>
                  repair_rule.spare_part_hits_consumed THEN
                RAISE EXCEPTION 'Hull repair resources do not reconcile'
                    USING ERRCODE='23514';
            END IF;
            IF OLD.succeeded THEN
                expected_hull:=OLD.hull_before+
                    OLD.integrity_points_restored;
            END IF;
        ELSE
            IF NOT OLD.workshop_used
               OR NOT OLD.specialist_materials_used
               OR spare_total<>0
               OR OLD.spare_part_hits_consumed<>0
               OR cost_count<>0
               OR OLD.repair_cost_minor<>
                  OLD.cost_basis_minor*
                  repair_rule.base_vehicle_cost_fraction_per_point*
                  OLD.integrity_points_restored THEN
                RAISE EXCEPTION
                    'Structure repair resources do not reconcile'
                    USING ERRCODE='23514';
            END IF;
            expected_structure:=OLD.structure_before+
                OLD.integrity_points_restored;
        END IF;
    END IF;

    expected_lifecycle:=CASE
        WHEN expected_structure=0 THEN 'destroyed'
        WHEN expected_hull=0 THEN 'disabled'
        ELSE 'active'
    END;
    IF OLD.armor_after<>OLD.armor_before
       OR OLD.hull_after<>expected_hull
       OR OLD.structure_after<>expected_structure
       OR OLD.lifecycle_after<>expected_lifecycle THEN
        RAISE EXCEPTION 'Vehicle repair final state does not reconcile'
            USING ERRCODE='23514';
    END IF;

    IF OLD.repair_method='jury-rig' THEN
        UPDATE vehicle_system_state
        SET temporary_restore_until=OLD.temporary_restore_until,
            temporary_restore_receipt_id=
                OLD.vehicle_repair_receipt_id,
            updated_at=NEW.applied_at
        WHERE vehicle_system_state_id=
              OLD.vehicle_system_state_id;
    ELSIF OLD.repair_category='system' AND OLD.succeeded THEN
        UPDATE vehicle_system_state
        SET current_hits=OLD.system_hits_after,
            system_status=OLD.system_status_after,
            temporary_restore_until=NULL,
            temporary_restore_receipt_id=NULL,
            updated_at=NEW.applied_at
        WHERE vehicle_system_state_id=
              OLD.vehicle_system_state_id
          AND current_hits=OLD.system_hits_before
          AND system_status=OLD.system_status_before;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'Vehicle system changed before repair'
                USING ERRCODE='40001';
        END IF;
    END IF;

    UPDATE vehicle_vehicle
    SET hull_current=OLD.hull_after,
        structure_current=OLD.structure_after,
        lifecycle_status=OLD.lifecycle_after,
        ended_at=CASE
            WHEN OLD.lifecycle_after='destroyed'
                THEN coalesce(ended_at,NEW.applied_at)
            ELSE NULL
        END,
        concurrency_version=concurrency_version+1
    WHERE vehicle_id=OLD.vehicle_id
      AND campaign_id=OLD.campaign_id
      AND hull_current=OLD.hull_before
      AND structure_current=OLD.structure_before
      AND lifecycle_status=OLD.lifecycle_before;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Vehicle changed before repair'
            USING ERRCODE='40001';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER vehicle_repair_finalization_valid
BEFORE UPDATE OR DELETE ON vehicle_repair_receipt
FOR EACH ROW EXECUTE FUNCTION vehicle_finalize_repair();

CREATE OR REPLACE FUNCTION vehicle_repair_line_open()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    receipt_id bigint;
    receipt_finalized boolean;
BEGIN
    receipt_id:=CASE
        WHEN TG_OP='DELETE' THEN OLD.vehicle_repair_receipt_id
        ELSE NEW.vehicle_repair_receipt_id
    END;
    SELECT finalized INTO receipt_finalized
    FROM vehicle_repair_receipt
    WHERE vehicle_repair_receipt_id=receipt_id;
    IF receipt_finalized THEN
        RAISE EXCEPTION 'Finalized vehicle repair lines are immutable'
            USING ERRCODE='23514';
    END IF;
    RETURN CASE WHEN TG_OP='DELETE' THEN OLD ELSE NEW END;
END;
$$;

CREATE TRIGGER vehicle_repair_modifier_open
BEFORE INSERT OR UPDATE OR DELETE ON vehicle_repair_modifier
FOR EACH ROW EXECUTE FUNCTION vehicle_repair_line_open();

CREATE TRIGGER vehicle_repair_die_open
BEFORE INSERT OR UPDATE OR DELETE ON vehicle_repair_random_die
FOR EACH ROW EXECUTE FUNCTION vehicle_repair_line_open();

CREATE TRIGGER vehicle_repair_spare_open
BEFORE INSERT OR UPDATE OR DELETE ON vehicle_repair_spare_source
FOR EACH ROW EXECUTE FUNCTION vehicle_repair_line_open();

CREATE VIEW vehicle_system_effective_state AS
SELECT system.vehicle_system_state_id,system.vehicle_id,
       system.campaign_id,system.location_code,
       system.system_identifier,system.current_hits,
       system.system_status AS damage_status,
       CASE
           WHEN system.temporary_restore_until>clock_timestamp()
               THEN 'operational'
           ELSE system.system_status
       END AS effective_status,
       system.temporary_restore_until,
       system.temporary_restore_receipt_id
FROM vehicle_system_state system;
