CREATE TABLE inv_item_instance (
    item_instance_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    item_rule_id bigint NOT NULL REFERENCES inv_item_definition(rule_id),
    instance_name text CHECK (
        instance_name IS NULL OR btrim(instance_name) <> ''
    ),
    serial_identifier text CHECK (
        serial_identifier IS NULL OR btrim(serial_identifier) <> ''
    ),
    item_status text NOT NULL DEFAULT 'active' CHECK (
        item_status IN ('active','lost','destroyed','consumed','archived')
    ),
    acquired_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    retired_at timestamptz,
    source_command_id bigint REFERENCES cmd_command(command_id),
    concurrency_version bigint NOT NULL DEFAULT 1 CHECK (
        concurrency_version > 0
    ),
    UNIQUE (item_instance_id,campaign_id),
    UNIQUE NULLS NOT DISTINCT (
        campaign_id,item_rule_id,serial_identifier
    ),
    CHECK (
        (item_status='active' AND retired_at IS NULL)
        OR (item_status<>'active' AND retired_at IS NOT NULL)
    )
);

CREATE TABLE inv_lot (
    lot_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    item_rule_id bigint NOT NULL REFERENCES inv_item_definition(rule_id),
    lot_identifier text CHECK (
        lot_identifier IS NULL OR btrim(lot_identifier) <> ''
    ),
    quantity bigint NOT NULL CHECK (quantity > 0),
    lot_status text NOT NULL DEFAULT 'active' CHECK (
        lot_status IN ('active','depleted','destroyed','archived')
    ),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    ended_at timestamptz,
    source_command_id bigint REFERENCES cmd_command(command_id),
    concurrency_version bigint NOT NULL DEFAULT 1 CHECK (
        concurrency_version > 0
    ),
    UNIQUE (lot_id,campaign_id),
    UNIQUE NULLS NOT DISTINCT (
        campaign_id,item_rule_id,lot_identifier
    ),
    CHECK (
        (lot_status='active' AND ended_at IS NULL)
        OR (lot_status<>'active' AND ended_at IS NOT NULL)
    )
);

CREATE TABLE inv_container (
    container_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    name text NOT NULL CHECK (btrim(name) <> ''),
    capacity_mass_grams bigint CHECK (capacity_mass_grams >= 0),
    container_status text NOT NULL DEFAULT 'active' CHECK (
        container_status IN ('active','sealed','destroyed','archived')
    ),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    ended_at timestamptz,
    concurrency_version bigint NOT NULL DEFAULT 1 CHECK (
        concurrency_version > 0
    ),
    UNIQUE (container_id,campaign_id),
    CHECK (
        (container_status IN ('active','sealed') AND ended_at IS NULL)
        OR (container_status IN ('destroyed','archived')
            AND ended_at IS NOT NULL)
    )
);

CREATE TABLE inv_actor_container (
    container_id bigint PRIMARY KEY,
    campaign_id bigint NOT NULL,
    actor_id bigint NOT NULL,
    FOREIGN KEY (container_id,campaign_id)
        REFERENCES inv_container(container_id,campaign_id),
    FOREIGN KEY (actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id)
);

CREATE TABLE inv_faction_container (
    container_id bigint PRIMARY KEY,
    campaign_id bigint NOT NULL,
    faction_id bigint NOT NULL,
    FOREIGN KEY (container_id,campaign_id)
        REFERENCES inv_container(container_id,campaign_id),
    FOREIGN KEY (faction_id,campaign_id)
        REFERENCES actor_faction(faction_id,campaign_id)
);

CREATE TABLE inv_location_container (
    container_id bigint PRIMARY KEY,
    campaign_id bigint NOT NULL,
    location_id bigint NOT NULL,
    FOREIGN KEY (container_id,campaign_id)
        REFERENCES inv_container(container_id,campaign_id),
    FOREIGN KEY (location_id,campaign_id)
        REFERENCES loc_location(location_id,campaign_id)
);

CREATE TABLE inv_item_container (
    container_id bigint PRIMARY KEY,
    campaign_id bigint NOT NULL,
    owner_item_instance_id bigint NOT NULL,
    FOREIGN KEY (container_id,campaign_id)
        REFERENCES inv_container(container_id,campaign_id),
    FOREIGN KEY (owner_item_instance_id,campaign_id)
        REFERENCES inv_item_instance(item_instance_id,campaign_id),
    UNIQUE (owner_item_instance_id)
);

CREATE OR REPLACE FUNCTION inv_reject_multiple_container_owners()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    owner_count integer;
BEGIN
    PERFORM 1 FROM inv_container
    WHERE container_id=NEW.container_id
    FOR UPDATE;

    SELECT
        (SELECT count(*) FROM inv_actor_container
         WHERE container_id=NEW.container_id)
      + (SELECT count(*) FROM inv_faction_container
         WHERE container_id=NEW.container_id)
      + (SELECT count(*) FROM inv_location_container
         WHERE container_id=NEW.container_id)
      + (SELECT count(*) FROM inv_item_container
         WHERE container_id=NEW.container_id)
    INTO owner_count;

    IF owner_count > 0 THEN
        RAISE EXCEPTION 'Container already has a typed owner'
            USING ERRCODE='23505';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER inv_actor_container_one_owner
BEFORE INSERT ON inv_actor_container
FOR EACH ROW EXECUTE FUNCTION inv_reject_multiple_container_owners();

CREATE TRIGGER inv_faction_container_one_owner
BEFORE INSERT ON inv_faction_container
FOR EACH ROW EXECUTE FUNCTION inv_reject_multiple_container_owners();

CREATE TRIGGER inv_location_container_one_owner
BEFORE INSERT ON inv_location_container
FOR EACH ROW EXECUTE FUNCTION inv_reject_multiple_container_owners();

CREATE TRIGGER inv_item_container_one_owner
BEFORE INSERT ON inv_item_container
FOR EACH ROW EXECUTE FUNCTION inv_reject_multiple_container_owners();

CREATE TABLE inv_transfer (
    transfer_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    transfer_kind text NOT NULL CHECK (
        transfer_kind IN (
            'custody','ownership','custody_and_ownership',
            'split','merge','consumption','adjustment'
        )
    ),
    transfer_status text NOT NULL DEFAULT 'pending' CHECK (
        transfer_status IN ('pending','completed','rejected','reversed')
    ),
    command_id bigint REFERENCES cmd_command(command_id),
    description text CHECK (
        description IS NULL OR btrim(description) <> ''
    ),
    occurred_day bigint,
    occurred_second integer CHECK (
        occurred_second IS NULL OR occurred_second BETWEEN 0 AND 86399
    ),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    completed_at timestamptz,
    UNIQUE (transfer_id,campaign_id),
    CHECK (
        (occurred_day IS NULL)=(occurred_second IS NULL)
    ),
    CHECK (
        (transfer_status='pending' AND completed_at IS NULL)
        OR (transfer_status<>'pending' AND completed_at IS NOT NULL)
    )
);

CREATE TABLE inv_container_item (
    item_instance_id bigint PRIMARY KEY,
    campaign_id bigint NOT NULL,
    container_id bigint NOT NULL,
    placed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    source_transfer_id bigint,
    FOREIGN KEY (item_instance_id,campaign_id)
        REFERENCES inv_item_instance(item_instance_id,campaign_id),
    FOREIGN KEY (container_id,campaign_id)
        REFERENCES inv_container(container_id,campaign_id),
    FOREIGN KEY (source_transfer_id,campaign_id)
        REFERENCES inv_transfer(transfer_id,campaign_id)
);

CREATE TABLE inv_container_lot (
    container_lot_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    campaign_id bigint NOT NULL,
    container_id bigint NOT NULL,
    lot_id bigint NOT NULL,
    quantity bigint NOT NULL CHECK (quantity > 0),
    placed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    source_transfer_id bigint,
    FOREIGN KEY (container_id,campaign_id)
        REFERENCES inv_container(container_id,campaign_id),
    FOREIGN KEY (lot_id,campaign_id)
        REFERENCES inv_lot(lot_id,campaign_id),
    FOREIGN KEY (source_transfer_id,campaign_id)
        REFERENCES inv_transfer(transfer_id,campaign_id),
    UNIQUE (container_id,lot_id)
);

CREATE TABLE loc_item_position (
    item_instance_id bigint PRIMARY KEY,
    campaign_id bigint NOT NULL,
    location_id bigint NOT NULL,
    position_label text CHECK (
        position_label IS NULL OR btrim(position_label) <> ''
    ),
    placed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    source_transfer_id bigint,
    FOREIGN KEY (item_instance_id,campaign_id)
        REFERENCES inv_item_instance(item_instance_id,campaign_id),
    FOREIGN KEY (location_id,campaign_id)
        REFERENCES loc_location(location_id,campaign_id),
    FOREIGN KEY (source_transfer_id,campaign_id)
        REFERENCES inv_transfer(transfer_id,campaign_id)
);

CREATE OR REPLACE FUNCTION inv_reject_multiple_item_positions()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM 1 FROM inv_item_instance
    WHERE item_instance_id=NEW.item_instance_id
    FOR UPDATE;

    IF TG_TABLE_NAME='inv_container_item' AND EXISTS (
        SELECT 1 FROM loc_item_position
        WHERE item_instance_id=NEW.item_instance_id
    ) THEN
        RAISE EXCEPTION 'Item already has a direct location'
            USING ERRCODE='23505';
    END IF;
    IF TG_TABLE_NAME='loc_item_position' AND EXISTS (
        SELECT 1 FROM inv_container_item
        WHERE item_instance_id=NEW.item_instance_id
    ) THEN
        RAISE EXCEPTION 'Item is already inside a container'
            USING ERRCODE='23505';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER inv_container_item_one_position
BEFORE INSERT ON inv_container_item
FOR EACH ROW EXECUTE FUNCTION inv_reject_multiple_item_positions();

CREATE TRIGGER loc_item_position_one_position
BEFORE INSERT ON loc_item_position
FOR EACH ROW EXECUTE FUNCTION inv_reject_multiple_item_positions();

CREATE OR REPLACE FUNCTION inv_reject_item_containment_cycle()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    creates_cycle boolean;
BEGIN
    WITH RECURSIVE owner_chain(item_instance_id) AS (
        SELECT owner.owner_item_instance_id
        FROM inv_item_container owner
        WHERE owner.container_id=NEW.container_id
          AND owner.campaign_id=NEW.campaign_id
        UNION
        SELECT next_owner.owner_item_instance_id
        FROM owner_chain chain
        JOIN inv_container_item placement
          ON placement.item_instance_id=chain.item_instance_id
         AND placement.campaign_id=NEW.campaign_id
        JOIN inv_item_container next_owner
          ON next_owner.container_id=placement.container_id
         AND next_owner.campaign_id=NEW.campaign_id
    )
    SELECT EXISTS (
        SELECT 1 FROM owner_chain
        WHERE item_instance_id=NEW.item_instance_id
    ) INTO creates_cycle;

    IF creates_cycle THEN
        RAISE EXCEPTION 'Item containment cycle is not permitted'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER inv_container_item_acyclic
BEFORE INSERT OR UPDATE ON inv_container_item
FOR EACH ROW EXECUTE FUNCTION inv_reject_item_containment_cycle();

CREATE OR REPLACE FUNCTION inv_validate_lot_allocation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    lot_quantity bigint;
    allocated bigint;
BEGIN
    PERFORM 1 FROM inv_lot WHERE lot_id=NEW.lot_id FOR UPDATE;
    SELECT quantity INTO lot_quantity
    FROM inv_lot WHERE lot_id=NEW.lot_id;
    SELECT COALESCE(sum(quantity),0) INTO allocated
    FROM inv_container_lot
    WHERE lot_id=NEW.lot_id
      AND container_lot_id IS DISTINCT FROM NEW.container_lot_id;
    IF allocated+NEW.quantity > lot_quantity THEN
        RAISE EXCEPTION 'Lot allocation exceeds authoritative quantity'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER inv_container_lot_quantity
BEFORE INSERT OR UPDATE ON inv_container_lot
FOR EACH ROW EXECUTE FUNCTION inv_validate_lot_allocation();

CREATE OR REPLACE FUNCTION inv_validate_container_capacity()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    target_container bigint;
    maximum_mass bigint;
    used_mass numeric;
BEGIN
    target_container := NEW.container_id;
    SELECT capacity_mass_grams INTO maximum_mass
    FROM inv_container
    WHERE container_id=target_container
    FOR UPDATE;
    IF maximum_mass IS NULL THEN
        RETURN NEW;
    END IF;

    SELECT
        COALESCE((
            SELECT sum(definition.mass_grams)
            FROM inv_container_item placement
            JOIN inv_item_instance item
              ON item.item_instance_id=placement.item_instance_id
            JOIN inv_item_definition definition
              ON definition.rule_id=item.item_rule_id
            WHERE placement.container_id=target_container
              AND (
                  TG_TABLE_NAME<>'inv_container_item'
                  OR placement.item_instance_id IS DISTINCT FROM
                     NEW.item_instance_id
              )
        ),0)
        + COALESCE((
            SELECT sum(definition.mass_grams*placement.quantity)
            FROM inv_container_lot placement
            JOIN inv_lot lot ON lot.lot_id=placement.lot_id
            JOIN inv_item_definition definition
              ON definition.rule_id=lot.item_rule_id
            WHERE placement.container_id=target_container
              AND (
                  TG_TABLE_NAME<>'inv_container_lot'
                  OR placement.container_lot_id IS DISTINCT FROM
                     NEW.container_lot_id
              )
        ),0)
    INTO used_mass;

    IF TG_TABLE_NAME='inv_container_item' THEN
        SELECT used_mass+definition.mass_grams INTO used_mass
        FROM inv_item_instance item
        JOIN inv_item_definition definition
          ON definition.rule_id=item.item_rule_id
        WHERE item.item_instance_id=NEW.item_instance_id;
    ELSE
        SELECT used_mass+(definition.mass_grams*NEW.quantity)
        INTO used_mass
        FROM inv_lot lot
        JOIN inv_item_definition definition
          ON definition.rule_id=lot.item_rule_id
        WHERE lot.lot_id=NEW.lot_id;
    END IF;

    IF used_mass IS NULL THEN
        RAISE EXCEPTION
            'Capacity-limited container requires known item mass'
            USING ERRCODE='23514';
    END IF;
    IF used_mass > maximum_mass THEN
        RAISE EXCEPTION 'Container mass capacity exceeded'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER inv_container_item_capacity
BEFORE INSERT OR UPDATE ON inv_container_item
FOR EACH ROW EXECUTE FUNCTION inv_validate_container_capacity();

CREATE TRIGGER inv_container_lot_capacity
BEFORE INSERT OR UPDATE ON inv_container_lot
FOR EACH ROW EXECUTE FUNCTION inv_validate_container_capacity();

CREATE TABLE inv_item_owner (
    item_instance_id bigint PRIMARY KEY,
    campaign_id bigint NOT NULL,
    actor_id bigint,
    faction_id bigint,
    acquired_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    source_transfer_id bigint,
    FOREIGN KEY (item_instance_id,campaign_id)
        REFERENCES inv_item_instance(item_instance_id,campaign_id),
    FOREIGN KEY (actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    FOREIGN KEY (faction_id,campaign_id)
        REFERENCES actor_faction(faction_id,campaign_id),
    FOREIGN KEY (source_transfer_id,campaign_id)
        REFERENCES inv_transfer(transfer_id,campaign_id),
    CHECK ((actor_id IS NOT NULL)::integer
           +(faction_id IS NOT NULL)::integer=1)
);

CREATE TABLE inv_lot_owner (
    lot_id bigint PRIMARY KEY,
    campaign_id bigint NOT NULL,
    actor_id bigint,
    faction_id bigint,
    acquired_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    source_transfer_id bigint,
    FOREIGN KEY (lot_id,campaign_id)
        REFERENCES inv_lot(lot_id,campaign_id),
    FOREIGN KEY (actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    FOREIGN KEY (faction_id,campaign_id)
        REFERENCES actor_faction(faction_id,campaign_id),
    FOREIGN KEY (source_transfer_id,campaign_id)
        REFERENCES inv_transfer(transfer_id,campaign_id),
    CHECK ((actor_id IS NOT NULL)::integer
           +(faction_id IS NOT NULL)::integer=1)
);

CREATE TABLE inv_item_condition (
    item_condition_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    campaign_id bigint NOT NULL,
    item_instance_id bigint NOT NULL,
    condition_code text NOT NULL CHECK (
        condition_code IN (
            'pristine','serviceable','worn','damaged',
            'disabled','destroyed'
        )
    ),
    integrity_current integer,
    integrity_maximum integer,
    effective_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    ended_at timestamptz,
    source_command_id bigint REFERENCES cmd_command(command_id),
    FOREIGN KEY (item_instance_id,campaign_id)
        REFERENCES inv_item_instance(item_instance_id,campaign_id),
    CHECK (
        (integrity_current IS NULL)=(integrity_maximum IS NULL)
    ),
    CHECK (
        integrity_current IS NULL
        OR (
            integrity_current BETWEEN 0 AND integrity_maximum
            AND integrity_maximum > 0
        )
    )
);

CREATE UNIQUE INDEX inv_one_current_item_condition
    ON inv_item_condition(item_instance_id)
    WHERE ended_at IS NULL;

CREATE TABLE inv_equipped_item (
    equipped_item_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    campaign_id bigint NOT NULL,
    actor_id bigint NOT NULL,
    item_instance_id bigint NOT NULL,
    equipment_slot text NOT NULL CHECK (btrim(equipment_slot) <> ''),
    equipped_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    unequipped_at timestamptz,
    source_command_id bigint REFERENCES cmd_command(command_id),
    FOREIGN KEY (actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    FOREIGN KEY (item_instance_id,campaign_id)
        REFERENCES inv_item_instance(item_instance_id,campaign_id)
);

CREATE UNIQUE INDEX inv_one_current_equipment_slot
    ON inv_equipped_item(actor_id,equipment_slot)
    WHERE unequipped_at IS NULL;

CREATE UNIQUE INDEX inv_item_equipped_once
    ON inv_equipped_item(item_instance_id)
    WHERE unequipped_at IS NULL;

CREATE TABLE inv_item_transfer (
    transfer_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    item_instance_id bigint NOT NULL,
    from_container_id bigint,
    to_container_id bigint,
    from_actor_id bigint,
    to_actor_id bigint,
    from_faction_id bigint,
    to_faction_id bigint,
    PRIMARY KEY (transfer_id,item_instance_id),
    FOREIGN KEY (transfer_id,campaign_id)
        REFERENCES inv_transfer(transfer_id,campaign_id),
    FOREIGN KEY (item_instance_id,campaign_id)
        REFERENCES inv_item_instance(item_instance_id,campaign_id),
    FOREIGN KEY (from_container_id,campaign_id)
        REFERENCES inv_container(container_id,campaign_id),
    FOREIGN KEY (to_container_id,campaign_id)
        REFERENCES inv_container(container_id,campaign_id),
    FOREIGN KEY (from_actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    FOREIGN KEY (to_actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    FOREIGN KEY (from_faction_id,campaign_id)
        REFERENCES actor_faction(faction_id,campaign_id),
    FOREIGN KEY (to_faction_id,campaign_id)
        REFERENCES actor_faction(faction_id,campaign_id),
    CHECK (
        from_container_id IS DISTINCT FROM to_container_id
        OR from_actor_id IS DISTINCT FROM to_actor_id
        OR from_faction_id IS DISTINCT FROM to_faction_id
    ),
    CHECK (
        (from_actor_id IS NOT NULL)::integer
        +(from_faction_id IS NOT NULL)::integer <= 1
    ),
    CHECK (
        (to_actor_id IS NOT NULL)::integer
        +(to_faction_id IS NOT NULL)::integer <= 1
    )
);

CREATE TABLE inv_lot_transfer (
    lot_transfer_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    transfer_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    lot_id bigint NOT NULL,
    quantity bigint NOT NULL CHECK (quantity > 0),
    from_container_id bigint,
    to_container_id bigint,
    FOREIGN KEY (transfer_id,campaign_id)
        REFERENCES inv_transfer(transfer_id,campaign_id),
    FOREIGN KEY (lot_id,campaign_id)
        REFERENCES inv_lot(lot_id,campaign_id),
    FOREIGN KEY (from_container_id,campaign_id)
        REFERENCES inv_container(container_id,campaign_id),
    FOREIGN KEY (to_container_id,campaign_id)
        REFERENCES inv_container(container_id,campaign_id),
    CHECK (from_container_id IS DISTINCT FROM to_container_id),
    UNIQUE (transfer_id,lot_id,from_container_id,to_container_id)
);
