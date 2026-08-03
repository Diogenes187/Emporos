CREATE OR REPLACE FUNCTION actor_require_canonical_symmetric_relationship()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    symmetric_value boolean;
BEGIN
    SELECT is_symmetric INTO symmetric_value
    FROM actor_relationship_type
    WHERE relationship_type_rule_id=NEW.relationship_type_rule_id;
    IF symmetric_value AND NEW.source_actor_id > NEW.target_actor_id THEN
        RAISE EXCEPTION
            'Symmetric actor relationships require canonical actor order'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER actor_relationship_canonical_symmetric
BEFORE INSERT OR UPDATE ON actor_relationship
FOR EACH ROW EXECUTE FUNCTION
    actor_require_canonical_symmetric_relationship();

CREATE OR REPLACE FUNCTION actor_require_canonical_symmetric_factions()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    symmetric_value boolean;
BEGIN
    SELECT is_symmetric INTO symmetric_value
    FROM actor_relationship_type
    WHERE relationship_type_rule_id=NEW.relationship_type_rule_id;
    IF symmetric_value AND NEW.source_faction_id > NEW.target_faction_id THEN
        RAISE EXCEPTION
            'Symmetric faction relationships require canonical faction order'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER actor_faction_relationship_canonical_symmetric
BEFORE INSERT OR UPDATE ON actor_faction_relationship
FOR EACH ROW EXECUTE FUNCTION
    actor_require_canonical_symmetric_factions();

CREATE OR REPLACE FUNCTION loc_reject_containment_cycle()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    creates_cycle boolean;
BEGIN
    IF NEW.containment_status <> 'active' THEN
        RETURN NEW;
    END IF;
    IF NOT EXISTS (
        SELECT 1
        FROM loc_location location
        JOIN rule_location_type location_type
          ON location_type.location_type_rule_id=
             location.location_type_rule_id
        WHERE location.location_id=NEW.parent_location_id
          AND location.campaign_id=NEW.campaign_id
          AND location_type.permits_containment
    ) THEN
        RAISE EXCEPTION 'Parent location type cannot contain locations'
            USING ERRCODE='23514';
    END IF;
    WITH RECURSIVE descendants(location_id) AS (
        SELECT NEW.child_location_id
        UNION
        SELECT containment.child_location_id
        FROM loc_containment containment
        JOIN descendants
          ON containment.parent_location_id=descendants.location_id
        WHERE containment.campaign_id=NEW.campaign_id
          AND containment.containment_status='active'
          AND containment.containment_id IS DISTINCT FROM
              NEW.containment_id
    )
    SELECT EXISTS (
        SELECT 1 FROM descendants
        WHERE location_id=NEW.parent_location_id
    ) INTO creates_cycle;
    IF creates_cycle THEN
        RAISE EXCEPTION 'Location containment cycle is not permitted'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION loc_require_actor_position_capability()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM loc_location location
        JOIN rule_location_type location_type
          ON location_type.location_type_rule_id=
             location.location_type_rule_id
        WHERE location.location_id=NEW.location_id
          AND location.campaign_id=NEW.campaign_id
          AND location_type.permits_actor_position
    ) THEN
        RAISE EXCEPTION 'Location type cannot contain actor positions'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER loc_actor_position_capability
BEFORE INSERT OR UPDATE ON loc_actor_position
FOR EACH ROW EXECUTE FUNCTION loc_require_actor_position_capability();

ALTER TABLE loc_connection
    ADD CONSTRAINT loc_connection_canonical_bidirectional_check CHECK (
        NOT bidirectional OR from_location_id < to_location_id
    );

ALTER TABLE loc_star_route
    ADD CONSTRAINT loc_star_route_canonical_bidirectional_check CHECK (
        NOT bidirectional
        OR from_system_location_id < to_system_location_id
    );
