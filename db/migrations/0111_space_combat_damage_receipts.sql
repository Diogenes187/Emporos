CREATE OR REPLACE FUNCTION senc_validate_attack_damage()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    target_ship bigint;
    net_damage_value integer;
    recorded_damage integer;
    allocated integer;
BEGIN
    PERFORM 1
    FROM senc_attack
    WHERE attack_id=NEW.attack_id
    FOR UPDATE;

    SELECT vessel.ship_id,attack.net_damage
    INTO target_ship,net_damage_value
    FROM senc_attack attack
    JOIN senc_vessel vessel
      ON vessel.senc_vessel_id=attack.target_vessel_id
    WHERE attack.attack_id=NEW.attack_id
      AND attack.engagement_id=NEW.engagement_id
      AND attack.campaign_id=NEW.campaign_id;

    SELECT damage_points
    INTO recorded_damage
    FROM ship_damage
    WHERE ship_damage_id=NEW.ship_damage_id
      AND ship_id=NEW.target_ship_id
      AND campaign_id=NEW.campaign_id;

    IF TG_OP='UPDATE' THEN
        SELECT coalesce(sum(allocated_damage),0)
        INTO allocated
        FROM senc_attack_damage
        WHERE attack_id=NEW.attack_id
          AND NOT (
              attack_id=OLD.attack_id
              AND allocation_order=OLD.allocation_order
          );
    ELSE
        SELECT coalesce(sum(allocated_damage),0)
        INTO allocated
        FROM senc_attack_damage
        WHERE attack_id=NEW.attack_id;
    END IF;

    IF NEW.target_ship_id<>target_ship
       OR NEW.allocated_damage<>recorded_damage
       OR allocated+NEW.allocated_damage>net_damage_value THEN
        RAISE EXCEPTION 'Space combat damage allocation is inconsistent'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

