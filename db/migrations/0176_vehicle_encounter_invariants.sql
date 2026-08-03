CREATE OR REPLACE FUNCTION venc_validate_action()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    action_code_value text;
    acting_vehicle bigint;
    current_speed numeric;
    maximum_weave integer;
BEGIN
    SELECT action_code
    INTO action_code_value
    FROM rule_vehicle_combat_action
    WHERE action_rule_id=NEW.action_rule_id;

    IF (
        action_code_value='weave'
        AND NEW.declared_weave_number IS NULL
    ) OR (
        action_code_value<>'weave'
        AND NEW.declared_weave_number IS NOT NULL
    ) THEN
        RAISE EXCEPTION
            'Weave number is legal only for a weave action'
            USING ERRCODE='23514';
    END IF;

    IF action_code_value='weave' THEN
        SELECT turn.venc_vehicle_id,state.speed_kph
        INTO acting_vehicle,current_speed
        FROM venc_crew_turn turn
        JOIN venc_vehicle_round_state state
          ON state.vehicle_combat_round_id=
             turn.vehicle_combat_round_id
         AND state.venc_vehicle_id=turn.venc_vehicle_id
        WHERE turn.vehicle_crew_turn_id=
              NEW.vehicle_crew_turn_id;

        maximum_weave:=ceil(current_speed/20);
        IF current_speed IS NULL
           OR NEW.declared_weave_number>maximum_weave THEN
            RAISE EXCEPTION
                'Weave number exceeds the speed-based maximum'
                USING ERRCODE='23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER venc_action_declaration_valid
BEFORE INSERT OR UPDATE ON venc_action
FOR EACH ROW EXECUTE FUNCTION venc_validate_action();

CREATE OR REPLACE FUNCTION venc_validate_action_resolution()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    declared_rule bigint;
    requirement text;
    action_code_value text;
    declared_status text;
    declared_command bigint;
BEGIN
    SELECT action.action_rule_id,rule.check_requirement,
           rule.action_code,action.action_status,
           action.source_command_id
    INTO declared_rule,requirement,action_code_value,
         declared_status,declared_command
    FROM venc_action action
    JOIN rule_vehicle_combat_action rule
      ON rule.action_rule_id=action.action_rule_id
    WHERE action.vehicle_action_id=NEW.vehicle_action_id;

    IF declared_rule<>NEW.action_rule_id
       OR declared_status NOT IN ('resolved','failed')
       OR NEW.succeeded<>(declared_status='resolved')
       OR NEW.check_required<>(requirement<>'none')
       OR (
           declared_command IS NOT NULL
           AND NEW.source_command_id IS DISTINCT FROM
               declared_command
       )
       OR (
           action_code_value='evasive'
           AND NEW.succeeded
           AND (
               NEW.incoming_attack_dm<>-NEW.effect
               OR NEW.outgoing_attack_dm<>-NEW.effect
           )
       )
       OR (
           action_code_value='ram'
           AND NEW.collision_generated<>NEW.succeeded
       ) THEN
        RAISE EXCEPTION
            'Vehicle action resolution disagrees with its rule'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION venc_validate_collision()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    resolution_engagement bigint;
    generated boolean;
BEGIN
    IF NEW.action_resolution_id IS NULL THEN
        RETURN NEW;
    END IF;

    SELECT action.vehicle_engagement_id,
           resolution.collision_generated
    INTO resolution_engagement,generated
    FROM venc_action_resolution resolution
    JOIN venc_action action
      ON action.vehicle_action_id=resolution.vehicle_action_id
    WHERE resolution.vehicle_action_id=
          NEW.action_resolution_id;

    IF resolution_engagement<>NEW.vehicle_engagement_id
       OR NOT generated THEN
        RAISE EXCEPTION
            'Collision must match a collision-generating action'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER venc_collision_resolution_valid
BEFORE INSERT OR UPDATE ON venc_collision
FOR EACH ROW EXECUTE FUNCTION venc_validate_collision();

ALTER TABLE venc_collision_occupant_effect
    ALTER COLUMN damage_taken TYPE numeric;

CREATE OR REPLACE FUNCTION venc_validate_collision_occupant()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    collision_damage integer;
    increment_count integer;
BEGIN
    SELECT rolled_damage,speed_increment_count
    INTO collision_damage,increment_count
    FROM venc_collision
    WHERE vehicle_collision_id=NEW.vehicle_collision_id
      AND campaign_id=NEW.campaign_id;

    IF collision_damage IS NULL
       OR (
           NEW.secured
           AND (
               NEW.damage_taken<>collision_damage*0.25
               OR NEW.thrown_metres<>0
           )
       )
       OR (
           NOT NEW.secured
           AND (
               NEW.damage_taken<>collision_damage
               OR NEW.thrown_metres<>increment_count*3
           )
       ) THEN
        RAISE EXCEPTION
            'Collision occupant effect disagrees with collision rules'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER venc_collision_occupant_valid
BEFORE INSERT OR UPDATE ON venc_collision_occupant_effect
FOR EACH ROW EXECUTE FUNCTION
    venc_validate_collision_occupant();
