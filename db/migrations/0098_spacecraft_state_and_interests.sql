CREATE TABLE ship_legal_interest (
    legal_interest_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ship_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    interest_kind text NOT NULL CHECK (
        interest_kind IN (
            'ownership','mortgage','lien','lease','charter','salvage_claim'
        )
    ),
    actor_id bigint,
    faction_id bigint,
    account_id bigint,
    share_basis_points smallint CHECK (
        share_basis_points BETWEEN 1 AND 10000
    ),
    effective_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    ended_at timestamptz,
    source_command_id bigint REFERENCES cmd_command(command_id),
    FOREIGN KEY (ship_id,campaign_id)
        REFERENCES ship_ship(ship_id,campaign_id),
    FOREIGN KEY (actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    FOREIGN KEY (faction_id,campaign_id)
        REFERENCES actor_faction(faction_id,campaign_id),
    FOREIGN KEY (account_id,campaign_id)
        REFERENCES fin_account(account_id,campaign_id),
    CHECK (num_nonnulls(actor_id,faction_id,account_id)=1),
    CHECK (
        (interest_kind='ownership' AND share_basis_points IS NOT NULL)
        OR (interest_kind<>'ownership' AND share_basis_points IS NULL)
    ),
    CHECK (ended_at IS NULL OR ended_at>=effective_at)
);

CREATE UNIQUE INDEX ship_active_legal_interest_identity
    ON ship_legal_interest(
        ship_id,interest_kind,
        coalesce(actor_id,0),coalesce(faction_id,0),coalesce(account_id,0)
    )
    WHERE ended_at IS NULL;

CREATE OR REPLACE FUNCTION ship_limit_ownership_shares()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    assigned integer;
BEGIN
    IF NEW.interest_kind<>'ownership' OR NEW.ended_at IS NOT NULL THEN
        RETURN NEW;
    END IF;

    PERFORM 1
    FROM ship_ship
    WHERE ship_id=NEW.ship_id AND campaign_id=NEW.campaign_id
    FOR UPDATE;

    SELECT coalesce(sum(share_basis_points),0)
    INTO assigned
    FROM ship_legal_interest
    WHERE ship_id=NEW.ship_id
      AND campaign_id=NEW.campaign_id
      AND interest_kind='ownership'
      AND ended_at IS NULL
      AND legal_interest_id<>coalesce(NEW.legal_interest_id,0);

    IF assigned+NEW.share_basis_points>10000 THEN
        RAISE EXCEPTION 'Active ship ownership exceeds 100 percent'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER ship_ownership_share_limit
BEFORE INSERT OR UPDATE ON ship_legal_interest
FOR EACH ROW EXECUTE FUNCTION ship_limit_ownership_shares();

CREATE TABLE ship_operational_control (
    operational_control_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ship_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    actor_id bigint,
    faction_id bigint,
    control_basis text NOT NULL CHECK (
        control_basis IN (
            'owner','captaincy','charter','lease','court_order',
            'seizure','theft','other'
        )
    ),
    effective_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    ended_at timestamptz,
    source_command_id bigint REFERENCES cmd_command(command_id),
    FOREIGN KEY (ship_id,campaign_id)
        REFERENCES ship_ship(ship_id,campaign_id),
    FOREIGN KEY (actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    FOREIGN KEY (faction_id,campaign_id)
        REFERENCES actor_faction(faction_id,campaign_id),
    CHECK (num_nonnulls(actor_id,faction_id)=1),
    CHECK (ended_at IS NULL OR ended_at>=effective_at)
);

CREATE UNIQUE INDEX ship_one_active_operational_controller
    ON ship_operational_control(ship_id)
    WHERE ended_at IS NULL;

ALTER TABLE enc_encounter
    ADD CONSTRAINT enc_encounter_id_campaign_unique
    UNIQUE (encounter_id,campaign_id);

CREATE TABLE ship_damage (
    ship_damage_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ship_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    target_kind text NOT NULL CHECK (
        target_kind IN ('hull','structure','component','crew_position')
    ),
    ship_component_id bigint,
    ship_crew_position_id bigint,
    damage_points smallint NOT NULL CHECK (damage_points>0),
    damage_status text NOT NULL DEFAULT 'unrepaired' CHECK (
        damage_status IN ('unrepaired','temporarily_restored','repaired')
    ),
    description text NOT NULL CHECK (btrim(description)<>''),
    encounter_id bigint,
    source_command_id bigint REFERENCES cmd_command(command_id),
    incurred_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    repaired_at timestamptz,
    FOREIGN KEY (ship_id,campaign_id)
        REFERENCES ship_ship(ship_id,campaign_id),
    FOREIGN KEY (encounter_id,campaign_id)
        REFERENCES enc_encounter(encounter_id,campaign_id),
    FOREIGN KEY (ship_component_id,campaign_id)
        REFERENCES ship_component(ship_component_id,campaign_id),
    FOREIGN KEY (ship_crew_position_id,ship_id,campaign_id)
        REFERENCES ship_crew_position(
            ship_crew_position_id,ship_id,campaign_id
        ),
    UNIQUE (ship_damage_id,ship_id,campaign_id),
    CHECK (
        (target_kind='component'
         AND ship_component_id IS NOT NULL
         AND ship_crew_position_id IS NULL)
        OR
        (target_kind='crew_position'
         AND ship_component_id IS NULL
         AND ship_crew_position_id IS NOT NULL)
        OR
        (target_kind IN ('hull','structure')
         AND ship_component_id IS NULL
         AND ship_crew_position_id IS NULL)
    ),
    CHECK (
        (damage_status='repaired' AND repaired_at IS NOT NULL)
        OR (damage_status<>'repaired' AND repaired_at IS NULL)
    )
);

CREATE TABLE ship_temporary_restoration (
    temporary_restoration_id bigint
        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ship_damage_id bigint NOT NULL,
    ship_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    restored_points smallint NOT NULL CHECK (restored_points>0),
    restoration_method text NOT NULL CHECK (
        restoration_method IN (
            'damage_control','jury_rig','emergency_patch','other'
        )
    ),
    restoration_status text NOT NULL DEFAULT 'active' CHECK (
        restoration_status IN ('active','expired','superseded')
    ),
    applied_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    expires_at timestamptz,
    ended_at timestamptz,
    source_command_id bigint REFERENCES cmd_command(command_id),
    FOREIGN KEY (ship_damage_id,ship_id,campaign_id)
        REFERENCES ship_damage(ship_damage_id,ship_id,campaign_id),
    CHECK (
        (restoration_status='active' AND ended_at IS NULL)
        OR (restoration_status<>'active' AND ended_at IS NOT NULL)
    ),
    CHECK (expires_at IS NULL OR expires_at>=applied_at),
    CHECK (ended_at IS NULL OR ended_at>=applied_at)
);

CREATE UNIQUE INDEX ship_one_active_restoration_per_damage
    ON ship_temporary_restoration(ship_damage_id)
    WHERE restoration_status='active';

CREATE TABLE ship_resource_movement (
    resource_movement_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ship_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    resource_type_code text NOT NULL,
    quantity_delta numeric NOT NULL CHECK (quantity_delta<>0),
    balance_after numeric NOT NULL CHECK (balance_after>=0),
    movement_kind text NOT NULL CHECK (
        movement_kind IN (
            'load','consume','dump','transfer','production',
            'correction','initial'
        )
    ),
    occurred_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    source_command_id bigint REFERENCES cmd_command(command_id),
    FOREIGN KEY (ship_id,resource_type_code)
        REFERENCES ship_resource(ship_id,resource_type_code),
    FOREIGN KEY (ship_id,campaign_id)
        REFERENCES ship_ship(ship_id,campaign_id)
);

CREATE OR REPLACE FUNCTION ship_validate_instance_state()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    class_hull smallint;
    class_structure smallint;
BEGIN
    SELECT hull_points,structure_points
    INTO class_hull,class_structure
    FROM ship_class
    WHERE ship_class_rule_id=NEW.ship_class_rule_id;

    IF NEW.hull_current>class_hull
       OR NEW.structure_current>class_structure THEN
        RAISE EXCEPTION 'Ship state exceeds class maxima'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER ship_instance_state_within_class
BEFORE INSERT OR UPDATE OF ship_class_rule_id,hull_current,structure_current
ON ship_ship
FOR EACH ROW EXECUTE FUNCTION ship_validate_instance_state();

CREATE OR REPLACE FUNCTION ship_validate_component_class()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    instance_class bigint;
    declared_class bigint;
    declared_component bigint;
BEGIN
    IF NEW.class_component_id IS NULL THEN
        RETURN NEW;
    END IF;

    SELECT ship_class_rule_id INTO instance_class
    FROM ship_ship
    WHERE ship_id=NEW.ship_id AND campaign_id=NEW.campaign_id;

    SELECT ship_class_rule_id,component_rule_id
    INTO declared_class,declared_component
    FROM ship_class_component
    WHERE ship_class_component_id=NEW.class_component_id;

    IF instance_class<>declared_class
       OR NEW.component_rule_id<>declared_component THEN
        RAISE EXCEPTION 'Installed component disagrees with ship class'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER ship_component_matches_class
BEFORE INSERT OR UPDATE OF ship_id,campaign_id,class_component_id,
    component_rule_id
ON ship_component
FOR EACH ROW EXECUTE FUNCTION ship_validate_component_class();
