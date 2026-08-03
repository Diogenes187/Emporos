ALTER TABLE ship_repair_job
    DROP CONSTRAINT ship_repair_job_check1;

ALTER TABLE ship_repair_job
    ADD CONSTRAINT ship_repair_job_completed_payment_check CHECK (
        repair_status<>'completed'
        OR estimated_cost_minor=0
        OR financial_transaction_id IS NOT NULL
    );

CREATE OR REPLACE FUNCTION ship_validate_repair_points()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    damage_total smallint;
    completed_total integer;
BEGIN
    SELECT damage_points INTO damage_total
    FROM ship_damage
    WHERE ship_damage_id=NEW.ship_damage_id
      AND ship_id=NEW.ship_id
      AND campaign_id=NEW.campaign_id
    FOR UPDATE;
    SELECT coalesce(sum(repair_points),0)
    INTO completed_total
    FROM ship_repair_job
    WHERE ship_damage_id=NEW.ship_damage_id
      AND repair_status='completed'
      AND repair_job_id<>coalesce(NEW.repair_job_id,0);
    IF NEW.repair_status='completed' THEN
        completed_total=completed_total+NEW.repair_points;
    END IF;
    IF completed_total>damage_total THEN
        RAISE EXCEPTION 'Completed repairs exceed recorded damage'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER ship_repair_points_valid
BEFORE INSERT OR UPDATE ON ship_repair_job
FOR EACH ROW EXECUTE FUNCTION ship_validate_repair_points();

CREATE OR REPLACE FUNCTION ship_apply_completed_repair()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    damage_total smallint;
    completed_total integer;
BEGIN
    IF NEW.repair_status<>'completed' THEN
        RETURN NEW;
    END IF;
    SELECT damage_points INTO damage_total
    FROM ship_damage
    WHERE ship_damage_id=NEW.ship_damage_id;
    SELECT coalesce(sum(repair_points),0)
    INTO completed_total
    FROM ship_repair_job
    WHERE ship_damage_id=NEW.ship_damage_id
      AND repair_status='completed';
    IF completed_total=damage_total THEN
        UPDATE ship_damage
        SET damage_status='repaired',
            repaired_at=NEW.completed_at
        WHERE ship_damage_id=NEW.ship_damage_id;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER ship_completed_repair_updates_damage
AFTER INSERT OR UPDATE OF repair_status,repair_points
ON ship_repair_job
FOR EACH ROW EXECUTE FUNCTION ship_apply_completed_repair();

CREATE OR REPLACE FUNCTION journey_validate_ship_resource_plan()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    planned_ship bigint;
    available numeric;
BEGIN
    SELECT journey.ship_id INTO planned_ship
    FROM journey_leg leg
    JOIN journey_journey journey
      ON journey.journey_id=leg.journey_id
     AND journey.campaign_id=leg.campaign_id
    WHERE leg.journey_leg_id=NEW.journey_leg_id
      AND leg.campaign_id=NEW.campaign_id;
    SELECT current_quantity INTO available
    FROM ship_resource
    WHERE ship_id=NEW.ship_id
      AND campaign_id=NEW.campaign_id
      AND resource_type_code=NEW.resource_type_code
    FOR UPDATE;

    IF planned_ship<>NEW.ship_id
       OR (
           NEW.plan_status='reserved'
           AND available<NEW.planned_quantity+NEW.reserve_quantity
       ) THEN
        RAISE EXCEPTION 'Journey resource plan is inconsistent'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION vehicle_validate_class_capacity()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    chassis_spaces smallint;
    armor_base smallint;
    armor_maximum smallint;
    armor_tech_level smallint;
BEGIN
    SELECT spaces INTO chassis_spaces
    FROM rule_vehicle_chassis
    WHERE chassis_code=NEW.chassis_code;
    IF NEW.allocated_spaces+NEW.cargo_spaces>chassis_spaces THEN
        RAISE EXCEPTION 'Vehicle design exceeds chassis spaces'
            USING ERRCODE='23514';
    END IF;
    IF NEW.armor_code IS NOT NULL THEN
        SELECT base_armor,maximum_armor,minimum_tech_level
        INTO armor_base,armor_maximum,armor_tech_level
        FROM rule_vehicle_armor
        WHERE armor_code=NEW.armor_code;
        IF NEW.armor_rating<armor_base
           OR NEW.armor_rating>armor_maximum
           OR NEW.minimum_tech_level<armor_tech_level THEN
            RAISE EXCEPTION
                'Vehicle armor is invalid for material or tech level'
                USING ERRCODE='23514';
        END IF;
    ELSIF NEW.armor_rating<>0 THEN
        RAISE EXCEPTION 'Vehicle armor rating requires armor material'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;
