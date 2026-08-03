CREATE TABLE venc_engagement (
    vehicle_engagement_id bigint GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,
    public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    encounter_id bigint NOT NULL UNIQUE,
    campaign_id bigint NOT NULL,
    engagement_status text NOT NULL DEFAULT 'forming' CHECK (
        engagement_status IN (
            'forming','active','resolved','escaped','aborted'
        )
    ),
    current_round integer CHECK (current_round>0),
    started_at timestamptz,
    ended_at timestamptz,
    FOREIGN KEY (encounter_id,campaign_id)
        REFERENCES enc_encounter(encounter_id,campaign_id),
    UNIQUE (vehicle_engagement_id,campaign_id),
    CHECK (
        (
            engagement_status='forming'
            AND current_round IS NULL
            AND started_at IS NULL
            AND ended_at IS NULL
        )
        OR (
            engagement_status='active'
            AND current_round IS NOT NULL
            AND started_at IS NOT NULL
            AND ended_at IS NULL
        )
        OR (
            engagement_status IN (
                'resolved','escaped','aborted'
            )
            AND started_at IS NOT NULL
            AND ended_at IS NOT NULL
        )
    )
);

CREATE TABLE venc_force (
    vehicle_force_id bigint GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,
    vehicle_engagement_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    side_code text NOT NULL CHECK (btrim(side_code)<>''),
    force_name text NOT NULL CHECK (btrim(force_name)<>''),
    FOREIGN KEY (vehicle_engagement_id,campaign_id)
        REFERENCES venc_engagement(
            vehicle_engagement_id,campaign_id
        ),
    UNIQUE (
        vehicle_force_id,vehicle_engagement_id,campaign_id
    ),
    UNIQUE (vehicle_engagement_id,side_code)
);

CREATE TABLE venc_vehicle (
    venc_vehicle_id bigint GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,
    vehicle_engagement_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    vehicle_force_id bigint NOT NULL,
    vehicle_id bigint NOT NULL,
    initiative_current integer,
    engagement_status text NOT NULL DEFAULT 'engaged' CHECK (
        engagement_status IN (
            'engaged','disabled','destroyed','escaped',
            'surrendered','withdrawn'
        )
    ),
    joined_round integer CHECK (joined_round>0),
    ended_round integer CHECK (ended_round>0),
    FOREIGN KEY (
        vehicle_force_id,vehicle_engagement_id,campaign_id
    ) REFERENCES venc_force(
        vehicle_force_id,vehicle_engagement_id,campaign_id
    ),
    FOREIGN KEY (vehicle_id,campaign_id)
        REFERENCES vehicle_vehicle(vehicle_id,campaign_id),
    UNIQUE (
        venc_vehicle_id,vehicle_engagement_id,campaign_id
    ),
    UNIQUE (vehicle_engagement_id,vehicle_id),
    CHECK (
        ended_round IS NULL OR ended_round>=joined_round
    )
);

CREATE TABLE venc_round (
    vehicle_combat_round_id bigint GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,
    vehicle_engagement_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    round_number integer NOT NULL CHECK (round_number>0),
    round_status text NOT NULL DEFAULT 'open' CHECK (
        round_status IN (
            'open','resolving','completed','aborted'
        )
    ),
    started_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    ended_at timestamptz,
    FOREIGN KEY (vehicle_engagement_id,campaign_id)
        REFERENCES venc_engagement(
            vehicle_engagement_id,campaign_id
        ),
    UNIQUE (
        vehicle_combat_round_id,
        vehicle_engagement_id,campaign_id
    ),
    UNIQUE (vehicle_engagement_id,round_number),
    CHECK (
        (
            round_status IN ('open','resolving')
            AND ended_at IS NULL
        )
        OR (
            round_status IN ('completed','aborted')
            AND ended_at IS NOT NULL
        )
    )
);

CREATE TABLE venc_vehicle_round_state (
    vehicle_combat_round_id bigint NOT NULL,
    vehicle_engagement_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    venc_vehicle_id bigint NOT NULL,
    speed_kph numeric NOT NULL CHECK (speed_kph>=0),
    facing_degrees numeric NOT NULL CHECK (
        facing_degrees>=0 AND facing_degrees<360
    ),
    position_x_metres numeric,
    position_y_metres numeric,
    position_z_metres numeric,
    agility_dm smallint NOT NULL,
    movement_status text NOT NULL DEFAULT 'mobile' CHECK (
        movement_status IN (
            'stationary','mobile','disabled','destroyed'
        )
    ),
    control_action_required text NOT NULL CHECK (
        control_action_required IN ('minor','significant')
    ),
    control_action_satisfied boolean NOT NULL DEFAULT false,
    active_evasion_effect integer,
    evasion_expires_after_next_driver_action boolean NOT NULL
        DEFAULT false,
    state_version bigint NOT NULL DEFAULT 1 CHECK (state_version>0),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (vehicle_combat_round_id,venc_vehicle_id),
    FOREIGN KEY (
        vehicle_combat_round_id,
        vehicle_engagement_id,campaign_id
    ) REFERENCES venc_round(
        vehicle_combat_round_id,
        vehicle_engagement_id,campaign_id
    ),
    FOREIGN KEY (
        venc_vehicle_id,vehicle_engagement_id,campaign_id
    ) REFERENCES venc_vehicle(
        venc_vehicle_id,vehicle_engagement_id,campaign_id
    ),
    CHECK (
        (
            active_evasion_effect IS NULL
            AND NOT evasion_expires_after_next_driver_action
        )
        OR (
            active_evasion_effect IS NOT NULL
            AND active_evasion_effect>=0
            AND evasion_expires_after_next_driver_action
        )
    ),
    CHECK (
        (
            movement_status='stationary' AND speed_kph=0
        )
        OR movement_status<>'stationary'
    )
);

CREATE TABLE venc_crew_turn (
    vehicle_crew_turn_id bigint GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,
    vehicle_combat_round_id bigint NOT NULL,
    vehicle_engagement_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    venc_vehicle_id bigint NOT NULL,
    crew_assignment_id bigint NOT NULL REFERENCES
        vehicle_crew_assignment(crew_assignment_id),
    initiative_at_action integer NOT NULL,
    significant_actions_used smallint NOT NULL DEFAULT 0 CHECK (
        significant_actions_used BETWEEN 0 AND 1
    ),
    minor_actions_used smallint NOT NULL DEFAULT 0 CHECK (
        minor_actions_used BETWEEN 0 AND 3
    ),
    turn_status text NOT NULL DEFAULT 'pending' CHECK (
        turn_status IN (
            'pending','acting','completed','forfeited'
        )
    ),
    FOREIGN KEY (
        vehicle_combat_round_id,
        vehicle_engagement_id,campaign_id
    ) REFERENCES venc_round(
        vehicle_combat_round_id,
        vehicle_engagement_id,campaign_id
    ),
    FOREIGN KEY (
        venc_vehicle_id,vehicle_engagement_id,campaign_id
    ) REFERENCES venc_vehicle(
        venc_vehicle_id,vehicle_engagement_id,campaign_id
    ),
    UNIQUE (vehicle_combat_round_id,crew_assignment_id),
    UNIQUE (
        vehicle_crew_turn_id,vehicle_combat_round_id,
        vehicle_engagement_id,campaign_id
    ),
    CHECK (
        significant_actions_used=0 OR minor_actions_used<=1
    )
);

CREATE OR REPLACE FUNCTION venc_validate_crew_turn()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    encounter_vehicle bigint;
    assigned_vehicle bigint;
    assigned_campaign bigint;
BEGIN
    SELECT vehicle_id
    INTO encounter_vehicle
    FROM venc_vehicle
    WHERE venc_vehicle_id=NEW.venc_vehicle_id
      AND vehicle_engagement_id=NEW.vehicle_engagement_id
      AND campaign_id=NEW.campaign_id;

    SELECT vehicle_id,campaign_id
    INTO assigned_vehicle,assigned_campaign
    FROM vehicle_crew_assignment
    WHERE crew_assignment_id=NEW.crew_assignment_id
      AND duty_status='active';

    IF assigned_vehicle IS NULL
       OR encounter_vehicle<>assigned_vehicle
       OR NEW.campaign_id<>assigned_campaign THEN
        RAISE EXCEPTION
            'Vehicle combat crew turn requires an active assignment'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER venc_crew_turn_assignment_valid
BEFORE INSERT OR UPDATE ON venc_crew_turn
FOR EACH ROW EXECUTE FUNCTION venc_validate_crew_turn();

CREATE TABLE venc_action (
    vehicle_action_id bigint GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,
    vehicle_crew_turn_id bigint NOT NULL,
    vehicle_combat_round_id bigint NOT NULL,
    vehicle_engagement_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    action_order smallint NOT NULL CHECK (action_order>0),
    action_rule_id bigint NOT NULL REFERENCES
        rule_vehicle_combat_action(action_rule_id),
    target_vehicle_id bigint,
    declared_weave_number smallint CHECK (
        declared_weave_number>0
    ),
    action_status text NOT NULL DEFAULT 'declared' CHECK (
        action_status IN (
            'declared','resolved','failed','cancelled'
        )
    ),
    source_command_id bigint REFERENCES cmd_command(command_id),
    declared_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    resolved_at timestamptz,
    FOREIGN KEY (
        vehicle_crew_turn_id,vehicle_combat_round_id,
        vehicle_engagement_id,campaign_id
    ) REFERENCES venc_crew_turn(
        vehicle_crew_turn_id,vehicle_combat_round_id,
        vehicle_engagement_id,campaign_id
    ),
    FOREIGN KEY (
        target_vehicle_id,vehicle_engagement_id,campaign_id
    ) REFERENCES venc_vehicle(
        venc_vehicle_id,vehicle_engagement_id,campaign_id
    ),
    UNIQUE (vehicle_crew_turn_id,action_order),
    UNIQUE (
        vehicle_action_id,vehicle_engagement_id,campaign_id
    ),
    CHECK (
        (
            action_status='declared' AND resolved_at IS NULL
        )
        OR (
            action_status<>'declared' AND resolved_at IS NOT NULL
        )
    )
);

CREATE TABLE venc_action_resolution (
    vehicle_action_id bigint PRIMARY KEY REFERENCES
        venc_action(vehicle_action_id),
    action_rule_id bigint NOT NULL REFERENCES
        rule_vehicle_combat_action(action_rule_id),
    source_command_id bigint REFERENCES cmd_command(command_id),
    check_required boolean NOT NULL,
    check_total integer,
    target_number integer,
    effect integer,
    succeeded boolean NOT NULL,
    incoming_attack_dm integer,
    outgoing_attack_dm integer,
    collision_generated boolean NOT NULL DEFAULT false,
    resolved_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CHECK (
        (
            check_required
            AND check_total IS NOT NULL
            AND target_number IS NOT NULL
            AND effect IS NOT NULL
            AND succeeded=(check_total>=target_number)
        )
        OR (
            NOT check_required
            AND check_total IS NULL
            AND target_number IS NULL
            AND effect IS NULL
            AND succeeded
        )
    ),
    CHECK (
        incoming_attack_dm IS NULL
        OR incoming_attack_dm<=0
    ),
    CHECK (
        outgoing_attack_dm IS NULL
        OR outgoing_attack_dm<=0
    )
);

CREATE OR REPLACE FUNCTION venc_validate_action_resolution()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    declared_rule bigint;
    requirement text;
    action_code_value text;
BEGIN
    SELECT action.action_rule_id,rule.check_requirement,
           rule.action_code
    INTO declared_rule,requirement,action_code_value
    FROM venc_action action
    JOIN rule_vehicle_combat_action rule
      ON rule.action_rule_id=action.action_rule_id
    WHERE action.vehicle_action_id=NEW.vehicle_action_id;

    IF declared_rule<>NEW.action_rule_id
       OR NEW.check_required<>(requirement<>'none')
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

CREATE TRIGGER venc_action_resolution_valid
BEFORE INSERT ON venc_action_resolution
FOR EACH ROW EXECUTE FUNCTION venc_validate_action_resolution();

CREATE OR REPLACE FUNCTION venc_resolution_immutable()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'Vehicle action resolutions are immutable'
        USING ERRCODE='23514';
END;
$$;

CREATE TRIGGER venc_action_resolution_immutable
BEFORE UPDATE OR DELETE ON venc_action_resolution
FOR EACH ROW EXECUTE FUNCTION venc_resolution_immutable();

CREATE TABLE venc_pursuit (
    vehicle_pursuit_id bigint GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,
    vehicle_engagement_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    pursuing_vehicle_id bigint NOT NULL,
    pursued_vehicle_id bigint NOT NULL,
    current_weave_action_id bigint,
    pursuit_status text NOT NULL DEFAULT 'active' CHECK (
        pursuit_status IN (
            'active','broken-off','lost','caught','ended'
        )
    ),
    started_round integer NOT NULL CHECK (started_round>0),
    ended_round integer CHECK (ended_round>0),
    FOREIGN KEY (
        pursuing_vehicle_id,vehicle_engagement_id,campaign_id
    ) REFERENCES venc_vehicle(
        venc_vehicle_id,vehicle_engagement_id,campaign_id
    ),
    FOREIGN KEY (
        pursued_vehicle_id,vehicle_engagement_id,campaign_id
    ) REFERENCES venc_vehicle(
        venc_vehicle_id,vehicle_engagement_id,campaign_id
    ),
    FOREIGN KEY (
        current_weave_action_id,
        vehicle_engagement_id,campaign_id
    ) REFERENCES venc_action(
        vehicle_action_id,vehicle_engagement_id,campaign_id
    ),
    UNIQUE (
        vehicle_engagement_id,
        pursuing_vehicle_id,pursued_vehicle_id
    ),
    CHECK (pursuing_vehicle_id<>pursued_vehicle_id),
    CHECK (
        ended_round IS NULL OR ended_round>=started_round
    )
);

CREATE TABLE venc_collision (
    vehicle_collision_id bigint GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,
    vehicle_engagement_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    vehicle_combat_round_id bigint NOT NULL,
    action_resolution_id bigint REFERENCES
        venc_action_resolution(vehicle_action_id),
    striking_vehicle_id bigint NOT NULL,
    target_vehicle_id bigint,
    target_actor_id bigint,
    obstacle_reference text CHECK (
        obstacle_reference IS NULL
        OR btrim(obstacle_reference)<>''
    ),
    impact_speed_kph numeric NOT NULL CHECK (impact_speed_kph>0),
    speed_increment_count integer GENERATED ALWAYS AS (
        ceil(impact_speed_kph/10)
    ) STORED,
    collision_damage_dice integer NOT NULL CHECK (
        collision_damage_dice>0
    ),
    rolled_damage integer NOT NULL CHECK (rolled_damage>=0),
    target_damage integer NOT NULL CHECK (target_damage>=0),
    striking_vehicle_damage integer CHECK (
        striking_vehicle_damage>=0
    ),
    source_command_id bigint REFERENCES cmd_command(command_id),
    occurred_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    FOREIGN KEY (
        vehicle_combat_round_id,
        vehicle_engagement_id,campaign_id
    ) REFERENCES venc_round(
        vehicle_combat_round_id,
        vehicle_engagement_id,campaign_id
    ),
    FOREIGN KEY (
        striking_vehicle_id,vehicle_engagement_id,campaign_id
    ) REFERENCES venc_vehicle(
        venc_vehicle_id,vehicle_engagement_id,campaign_id
    ),
    FOREIGN KEY (
        target_vehicle_id,vehicle_engagement_id,campaign_id
    ) REFERENCES venc_vehicle(
        venc_vehicle_id,vehicle_engagement_id,campaign_id
    ),
    FOREIGN KEY (target_actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    UNIQUE (vehicle_collision_id,campaign_id),
    CHECK (
        num_nonnulls(
            target_vehicle_id,target_actor_id,obstacle_reference
        )=1
    ),
    CHECK (
        target_vehicle_id IS NULL
        OR target_vehicle_id<>striking_vehicle_id
    ),
    CHECK (collision_damage_dice=speed_increment_count),
    CHECK (target_damage=rolled_damage),
    CHECK (
        action_resolution_id IS NULL
        OR striking_vehicle_damage IS NOT NULL
    )
);

CREATE TABLE venc_collision_occupant_effect (
    vehicle_collision_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    actor_id bigint NOT NULL,
    secured boolean NOT NULL,
    damage_taken integer NOT NULL CHECK (damage_taken>=0),
    thrown_metres numeric NOT NULL CHECK (thrown_metres>=0),
    PRIMARY KEY (vehicle_collision_id,actor_id),
    FOREIGN KEY (vehicle_collision_id,campaign_id)
        REFERENCES venc_collision(
            vehicle_collision_id,campaign_id
        ),
    FOREIGN KEY (actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    CHECK (
        (secured AND thrown_metres=0)
        OR NOT secured
    )
);
