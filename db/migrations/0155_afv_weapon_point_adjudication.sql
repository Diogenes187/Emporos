ALTER TABLE vehicle_class_weapon_point_summary
    ADD COLUMN effective_available_weapon_points smallint,
    ADD COLUMN adjudication_basis text,
    ADD COLUMN effective_unused_weapon_points smallint
        GENERATED ALWAYS AS (
            effective_available_weapon_points-
            published_used_weapon_points
        ) STORED;

UPDATE vehicle_class_weapon_point_summary summary
SET effective_available_weapon_points=
        CASE
            WHEN class.class_code='afv-tracked'
                THEN summary.calculated_available_weapon_points
            ELSE summary.published_available_weapon_points
        END,
    adjudication_basis=
        CASE
            WHEN class.class_code='afv-tracked'
                THEN 'governing-rule'
            ELSE 'published-profile'
        END
FROM vehicle_class class
WHERE class.vehicle_class_rule_id=summary.vehicle_class_rule_id;

ALTER TABLE vehicle_class_weapon_point_summary
    ALTER COLUMN effective_available_weapon_points SET NOT NULL,
    ALTER COLUMN adjudication_basis SET NOT NULL,
    ADD CHECK (effective_available_weapon_points>0),
    ADD CHECK (effective_unused_weapon_points>=0),
    ADD CHECK (
        adjudication_basis IN (
            'published-profile','governing-rule'
        )
    ),
    ADD CHECK (
        (adjudication_basis='published-profile'
         AND effective_available_weapon_points=
             published_available_weapon_points)
        OR
        (adjudication_basis='governing-rule'
         AND effective_available_weapon_points=
             calculated_available_weapon_points)
    );

CREATE OR REPLACE FUNCTION vehicle_validate_class_armament_mount()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    available_points smallint;
    other_points integer;
    class_tech smallint;
    mount_tech smallint;
BEGIN
    SELECT summary.effective_available_weapon_points,
           class.minimum_tech_level
    INTO available_points,class_tech
    FROM vehicle_class_weapon_point_summary summary
    JOIN vehicle_class class USING (vehicle_class_rule_id)
    WHERE summary.vehicle_class_rule_id=NEW.vehicle_class_rule_id;

    SELECT coalesce(
               sum(mount.quantity*mount.weapon_points_each),0
           )
    INTO other_points
    FROM vehicle_class_armament_mount mount
    WHERE mount.vehicle_class_rule_id=NEW.vehicle_class_rule_id
      AND mount.class_armament_mount_id<>
          coalesce(NEW.class_armament_mount_id,0);

    IF other_points+NEW.quantity*NEW.weapon_points_each>
       available_points THEN
        RAISE EXCEPTION
            'Vehicle class armaments exceed effective weapon points'
            USING ERRCODE='23514';
    END IF;

    IF NEW.weapon_mount_rule_id IS NOT NULL THEN
        SELECT minimum_tech_level INTO mount_tech
        FROM rule_vehicle_weapon_mount
        WHERE mount_rule_id=NEW.weapon_mount_rule_id;
        IF class_tech<mount_tech THEN
            RAISE EXCEPTION
                'Vehicle class tech level is below weapon mount tech level'
                USING ERRCODE='23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

UPDATE src_issue
SET engine_disposition='preserve_rule'
WHERE issue_code='vehicle.class.afv-weapon-points';
