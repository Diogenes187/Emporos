ALTER TABLE senc_attack_damage
    ADD COLUMN target_ship_id bigint NOT NULL,
    ADD CONSTRAINT senc_attack_damage_target_ship_fkey
        FOREIGN KEY (ship_damage_id,target_ship_id,campaign_id)
        REFERENCES ship_damage(
            ship_damage_id,ship_id,campaign_id
        );

CREATE OR REPLACE FUNCTION senc_validate_engagement_activation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.engagement_status='active'
       AND OLD.engagement_status<>'active' THEN
        IF (
            SELECT count(*) FROM senc_force
            WHERE engagement_id=NEW.engagement_id
        )<2 OR (
            SELECT count(*) FROM senc_vessel
            WHERE engagement_id=NEW.engagement_id
        )<2 THEN
            RAISE EXCEPTION
                'Active space combat requires two forces and vessels'
                USING ERRCODE='23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER senc_engagement_activation_valid
BEFORE UPDATE OF engagement_status ON senc_engagement
FOR EACH ROW EXECUTE FUNCTION senc_validate_engagement_activation();

CREATE OR REPLACE FUNCTION senc_validate_crew_turn()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    vessel_ship bigint;
    assignment_ship bigint;
    assignment_status text;
BEGIN
    SELECT ship_id INTO vessel_ship
    FROM senc_vessel
    WHERE senc_vessel_id=NEW.senc_vessel_id
      AND engagement_id=NEW.engagement_id
      AND campaign_id=NEW.campaign_id;
    SELECT ship_id,duty_status INTO assignment_ship,assignment_status
    FROM ship_crew_assignment
    WHERE crew_assignment_id=NEW.crew_assignment_id;
    IF vessel_ship<>assignment_ship OR assignment_status<>'active' THEN
        RAISE EXCEPTION
            'Space combat crew turn requires active crew aboard vessel'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER senc_crew_turn_assignment_valid
BEFORE INSERT OR UPDATE ON senc_crew_turn
FOR EACH ROW EXECUTE FUNCTION senc_validate_crew_turn();

CREATE OR REPLACE FUNCTION senc_consume_action_budget()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    kind text;
    significant_used smallint;
    minor_used smallint;
BEGIN
    SELECT action_kind INTO kind
    FROM rule_space_combat_action
    WHERE action_code=NEW.action_code;
    SELECT significant_actions_used,minor_actions_used
    INTO significant_used,minor_used
    FROM senc_crew_turn
    WHERE crew_turn_id=NEW.crew_turn_id
    FOR UPDATE;

    IF kind='significant' THEN
        IF significant_used>=1 OR minor_used>1 THEN
            RAISE EXCEPTION 'Space combat significant action budget spent'
                USING ERRCODE='23514';
        END IF;
        UPDATE senc_crew_turn
        SET significant_actions_used=significant_actions_used+1
        WHERE crew_turn_id=NEW.crew_turn_id;
    ELSIF kind='minor' THEN
        IF minor_used >= (
            CASE WHEN significant_used=0 THEN 3 ELSE 1 END
        ) THEN
            RAISE EXCEPTION 'Space combat minor action budget spent'
                USING ERRCODE='23514';
        END IF;
        UPDATE senc_crew_turn
        SET minor_actions_used=minor_actions_used+1
        WHERE crew_turn_id=NEW.crew_turn_id;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER senc_action_consumes_budget
BEFORE INSERT ON senc_action
FOR EACH ROW EXECUTE FUNCTION senc_consume_action_budget();

CREATE OR REPLACE FUNCTION senc_validate_attack()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    acting_vessel bigint;
    declared_target bigint;
    action_type text;
BEGIN
    SELECT turn.senc_vessel_id,action.target_vessel_id,
           action.action_code
    INTO acting_vessel,declared_target,action_type
    FROM senc_action action
    JOIN senc_crew_turn turn ON turn.crew_turn_id=action.crew_turn_id
    WHERE action.space_combat_action_id=NEW.space_combat_action_id;
    IF action_type<>'attack'
       OR acting_vessel<>NEW.attacker_vessel_id
       OR declared_target<>NEW.target_vessel_id THEN
        RAISE EXCEPTION 'Space combat attack declaration is inconsistent'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER senc_attack_declaration_valid
BEFORE INSERT OR UPDATE ON senc_attack
FOR EACH ROW EXECUTE FUNCTION senc_validate_attack();

CREATE OR REPLACE FUNCTION senc_validate_attack_damage()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    target_ship bigint;
    net_damage_value integer;
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
    SELECT coalesce(sum(allocated_damage),0)
    INTO allocated
    FROM senc_attack_damage
    WHERE attack_id=NEW.attack_id
      AND allocation_order<>NEW.allocation_order;
    IF NEW.target_ship_id<>target_ship
       OR allocated+NEW.allocated_damage>net_damage_value THEN
        RAISE EXCEPTION 'Space combat damage allocation is inconsistent'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER senc_attack_damage_valid
BEFORE INSERT OR UPDATE ON senc_attack_damage
FOR EACH ROW EXECUTE FUNCTION senc_validate_attack_damage();
