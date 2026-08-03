CREATE TABLE actor_relationship_type (
    relationship_type_rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    relationship_type_code text NOT NULL UNIQUE CHECK (
        relationship_type_code ~
            '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
    ),
    is_symmetric boolean NOT NULL,
    inverse_relationship_type_rule_id bigint REFERENCES
        actor_relationship_type(relationship_type_rule_id),
    CHECK (
        inverse_relationship_type_rule_id IS NULL
        OR inverse_relationship_type_rule_id <>
            relationship_type_rule_id
        OR is_symmetric
    )
);

CREATE TABLE actor_relationship (
    actor_relationship_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    source_actor_id bigint NOT NULL,
    target_actor_id bigint NOT NULL,
    relationship_type_rule_id bigint NOT NULL REFERENCES
        actor_relationship_type(relationship_type_rule_id),
    relationship_strength integer,
    relationship_status text NOT NULL DEFAULT 'active' CHECK (
        relationship_status IN ('active','ended','rejected')
    ),
    source_rule_id bigint REFERENCES rule_rule(rule_id),
    source_command_id bigint REFERENCES cmd_command(command_id),
    effective_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    ended_at timestamptz,
    FOREIGN KEY (source_actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    FOREIGN KEY (target_actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    CHECK (source_actor_id <> target_actor_id),
    CHECK (
        (relationship_status='active' AND ended_at IS NULL)
        OR (relationship_status<>'active' AND ended_at IS NOT NULL)
    )
);

CREATE UNIQUE INDEX actor_one_active_relationship
    ON actor_relationship(
        campaign_id,source_actor_id,target_actor_id,
        relationship_type_rule_id
    )
    WHERE relationship_status='active';

CREATE TABLE actor_faction (
    faction_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    name text NOT NULL CHECK (btrim(name) <> ''),
    faction_status text NOT NULL DEFAULT 'active' CHECK (
        faction_status IN ('active','dissolved','destroyed','archived')
    ),
    source_rule_id bigint REFERENCES rule_rule(rule_id),
    concurrency_version bigint NOT NULL DEFAULT 1 CHECK (
        concurrency_version > 0
    ),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    ended_at timestamptz,
    UNIQUE (faction_id,campaign_id),
    UNIQUE (campaign_id,name),
    CHECK (
        (faction_status='active' AND ended_at IS NULL)
        OR (faction_status<>'active' AND ended_at IS NOT NULL)
    )
);

CREATE TABLE actor_faction_membership (
    faction_membership_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    faction_id bigint NOT NULL,
    actor_id bigint NOT NULL,
    role_name text,
    rank_name text,
    standing integer,
    membership_status text NOT NULL DEFAULT 'active' CHECK (
        membership_status IN ('active','ended','expelled')
    ),
    effective_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    ended_at timestamptz,
    source_command_id bigint REFERENCES cmd_command(command_id),
    FOREIGN KEY (faction_id,campaign_id)
        REFERENCES actor_faction(faction_id,campaign_id),
    FOREIGN KEY (actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    CHECK (role_name IS NULL OR btrim(role_name) <> ''),
    CHECK (rank_name IS NULL OR btrim(rank_name) <> ''),
    CHECK (
        (membership_status='active' AND ended_at IS NULL)
        OR (membership_status<>'active' AND ended_at IS NOT NULL)
    )
);

CREATE UNIQUE INDEX actor_one_active_faction_membership
    ON actor_faction_membership(campaign_id,faction_id,actor_id)
    WHERE membership_status='active';

CREATE TABLE actor_faction_relationship (
    faction_relationship_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    source_faction_id bigint NOT NULL,
    target_faction_id bigint NOT NULL,
    relationship_type_rule_id bigint NOT NULL REFERENCES
        actor_relationship_type(relationship_type_rule_id),
    relationship_strength integer,
    relationship_status text NOT NULL DEFAULT 'active' CHECK (
        relationship_status IN ('active','ended','rejected')
    ),
    effective_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    ended_at timestamptz,
    source_command_id bigint REFERENCES cmd_command(command_id),
    FOREIGN KEY (source_faction_id,campaign_id)
        REFERENCES actor_faction(faction_id,campaign_id),
    FOREIGN KEY (target_faction_id,campaign_id)
        REFERENCES actor_faction(faction_id,campaign_id),
    CHECK (source_faction_id <> target_faction_id),
    CHECK (
        (relationship_status='active' AND ended_at IS NULL)
        OR (relationship_status<>'active' AND ended_at IS NOT NULL)
    )
);

CREATE UNIQUE INDEX actor_one_active_faction_relationship
    ON actor_faction_relationship(
        campaign_id,source_faction_id,target_faction_id,
        relationship_type_rule_id
    )
    WHERE relationship_status='active';

CREATE TABLE rule_location_type (
    location_type_rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    location_type_code text NOT NULL UNIQUE CHECK (
        location_type_code ~
            '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
    ),
    permits_containment boolean NOT NULL,
    permits_actor_position boolean NOT NULL
);

CREATE TABLE rule_location_connection_type (
    connection_type_rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    connection_type_code text NOT NULL UNIQUE CHECK (
        connection_type_code ~
            '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
    )
);

CREATE TABLE rule_location_feature_type (
    feature_type_rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    feature_type_code text NOT NULL UNIQUE CHECK (
        feature_type_code ~
            '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
    )
);

CREATE TABLE loc_location (
    location_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    location_type_rule_id bigint NOT NULL REFERENCES
        rule_location_type(location_type_rule_id),
    name text NOT NULL CHECK (btrim(name) <> ''),
    visibility_status text NOT NULL DEFAULT 'known' CHECK (
        visibility_status IN ('hidden','rumored','discovered','known')
    ),
    location_status text NOT NULL DEFAULT 'active' CHECK (
        location_status IN ('active','inaccessible','destroyed','archived')
    ),
    source_rule_id bigint REFERENCES rule_rule(rule_id),
    concurrency_version bigint NOT NULL DEFAULT 1 CHECK (
        concurrency_version > 0
    ),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    ended_at timestamptz,
    UNIQUE (location_id,campaign_id),
    CHECK (
        (location_status IN ('active','inaccessible') AND ended_at IS NULL)
        OR (location_status IN ('destroyed','archived')
            AND ended_at IS NOT NULL)
    )
);

CREATE TABLE loc_containment (
    containment_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    parent_location_id bigint NOT NULL,
    child_location_id bigint NOT NULL,
    containment_status text NOT NULL DEFAULT 'active' CHECK (
        containment_status IN ('active','ended')
    ),
    effective_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    ended_at timestamptz,
    source_command_id bigint REFERENCES cmd_command(command_id),
    FOREIGN KEY (parent_location_id,campaign_id)
        REFERENCES loc_location(location_id,campaign_id),
    FOREIGN KEY (child_location_id,campaign_id)
        REFERENCES loc_location(location_id,campaign_id),
    CHECK (parent_location_id <> child_location_id),
    CHECK (
        (containment_status='active' AND ended_at IS NULL)
        OR (containment_status='ended' AND ended_at IS NOT NULL)
    )
);

CREATE UNIQUE INDEX loc_one_active_parent
    ON loc_containment(campaign_id,child_location_id)
    WHERE containment_status='active';

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

CREATE TRIGGER loc_containment_no_cycle
BEFORE INSERT OR UPDATE ON loc_containment
FOR EACH ROW EXECUTE FUNCTION loc_reject_containment_cycle();

CREATE TABLE loc_connection (
    location_connection_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    from_location_id bigint NOT NULL,
    to_location_id bigint NOT NULL,
    connection_type_rule_id bigint NOT NULL REFERENCES
        rule_location_connection_type(connection_type_rule_id),
    bidirectional boolean NOT NULL,
    traversal_status text NOT NULL DEFAULT 'open' CHECK (
        traversal_status IN (
            'open','closed','locked','blocked','destroyed','unknown'
        )
    ),
    visibility_status text NOT NULL DEFAULT 'known' CHECK (
        visibility_status IN ('hidden','rumored','discovered','known')
    ),
    distance_value numeric CHECK (distance_value >= 0),
    distance_unit text CHECK (
        distance_unit IS NULL OR distance_unit IN (
            'metre','kilometre','astronomical_unit','parsec'
        )
    ),
    access_requirement_rule_id bigint REFERENCES rule_rule(rule_id),
    connection_status text NOT NULL DEFAULT 'active' CHECK (
        connection_status IN ('active','ended')
    ),
    effective_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    ended_at timestamptz,
    FOREIGN KEY (from_location_id,campaign_id)
        REFERENCES loc_location(location_id,campaign_id),
    FOREIGN KEY (to_location_id,campaign_id)
        REFERENCES loc_location(location_id,campaign_id),
    CHECK (from_location_id <> to_location_id),
    CHECK ((distance_value IS NULL)=(distance_unit IS NULL)),
    CHECK (
        (connection_status='active' AND ended_at IS NULL)
        OR (connection_status='ended' AND ended_at IS NOT NULL)
    )
);

CREATE UNIQUE INDEX loc_one_active_directed_connection
    ON loc_connection(
        campaign_id,from_location_id,to_location_id,
        connection_type_rule_id
    )
    WHERE connection_status='active';

CREATE TABLE loc_feature (
    location_feature_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    location_id bigint NOT NULL,
    feature_type_rule_id bigint NOT NULL REFERENCES
        rule_location_feature_type(feature_type_rule_id),
    name text NOT NULL CHECK (btrim(name) <> ''),
    feature_status text NOT NULL DEFAULT 'active' CHECK (
        feature_status IN (
            'active','disabled','damaged','destroyed','concealed'
        )
    ),
    source_rule_id bigint REFERENCES rule_rule(rule_id),
    concurrency_version bigint NOT NULL DEFAULT 1 CHECK (
        concurrency_version > 0
    ),
    FOREIGN KEY (location_id,campaign_id)
        REFERENCES loc_location(location_id,campaign_id),
    UNIQUE (location_feature_id,campaign_id)
);

CREATE TABLE loc_actor_position (
    actor_position_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    actor_id bigint NOT NULL,
    location_id bigint NOT NULL,
    coordinate_x numeric,
    coordinate_y numeric,
    coordinate_z numeric,
    coordinate_unit text CHECK (
        coordinate_unit IS NULL OR coordinate_unit IN ('metre','kilometre')
    ),
    position_status text NOT NULL DEFAULT 'current' CHECK (
        position_status IN ('current','departed')
    ),
    effective_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    ended_at timestamptz,
    source_command_id bigint REFERENCES cmd_command(command_id),
    FOREIGN KEY (actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    FOREIGN KEY (location_id,campaign_id)
        REFERENCES loc_location(location_id,campaign_id),
    CHECK (
        coordinate_unit IS NOT NULL
        OR num_nonnulls(coordinate_x,coordinate_y,coordinate_z)=0
    ),
    CHECK (
        (position_status='current' AND ended_at IS NULL)
        OR (position_status='departed' AND ended_at IS NOT NULL)
    )
);

CREATE UNIQUE INDEX loc_one_current_actor_position
    ON loc_actor_position(campaign_id,actor_id)
    WHERE position_status='current';

CREATE TABLE actor_reputation (
    actor_reputation_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    actor_id bigint NOT NULL,
    faction_id bigint,
    location_id bigint,
    reputation_value integer NOT NULL,
    reputation_status text NOT NULL DEFAULT 'active' CHECK (
        reputation_status IN ('active','ended')
    ),
    effective_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    ended_at timestamptz,
    source_command_id bigint REFERENCES cmd_command(command_id),
    FOREIGN KEY (actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    FOREIGN KEY (faction_id,campaign_id)
        REFERENCES actor_faction(faction_id,campaign_id),
    FOREIGN KEY (location_id,campaign_id)
        REFERENCES loc_location(location_id,campaign_id),
    CHECK (num_nonnulls(faction_id,location_id)=1),
    CHECK (
        (reputation_status='active' AND ended_at IS NULL)
        OR (reputation_status='ended' AND ended_at IS NOT NULL)
    )
);

CREATE UNIQUE INDEX actor_one_active_faction_reputation
    ON actor_reputation(campaign_id,actor_id,faction_id)
    WHERE reputation_status='active' AND faction_id IS NOT NULL;
CREATE UNIQUE INDEX actor_one_active_location_reputation
    ON actor_reputation(campaign_id,actor_id,location_id)
    WHERE reputation_status='active' AND location_id IS NOT NULL;

CREATE TABLE actor_note (
    actor_note_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    actor_id bigint NOT NULL,
    author_account_id bigint REFERENCES iam_account(account_id),
    visibility text NOT NULL CHECK (
        visibility IN ('private','referee','campaign')
    ),
    note_text text NOT NULL CHECK (btrim(note_text) <> ''),
    note_status text NOT NULL DEFAULT 'current' CHECK (
        note_status IN ('current','superseded','deleted')
    ),
    supersedes_actor_note_id bigint,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    ended_at timestamptz,
    FOREIGN KEY (actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    UNIQUE (actor_note_id,actor_id,campaign_id),
    FOREIGN KEY (supersedes_actor_note_id,actor_id,campaign_id)
        REFERENCES actor_note(actor_note_id,actor_id,campaign_id),
    CHECK (
        (note_status='current' AND ended_at IS NULL)
        OR (note_status<>'current' AND ended_at IS NOT NULL)
    )
);

CREATE TABLE loc_sector (
    location_id bigint PRIMARY KEY,
    campaign_id bigint NOT NULL,
    sector_x integer NOT NULL,
    sector_y integer NOT NULL,
    FOREIGN KEY (location_id,campaign_id)
        REFERENCES loc_location(location_id,campaign_id),
    UNIQUE (location_id,campaign_id),
    UNIQUE (campaign_id,sector_x,sector_y)
);

CREATE TABLE loc_subsector (
    location_id bigint PRIMARY KEY,
    campaign_id bigint NOT NULL,
    sector_location_id bigint NOT NULL,
    subsector_column smallint NOT NULL CHECK (
        subsector_column BETWEEN 1 AND 4
    ),
    subsector_row smallint NOT NULL CHECK (subsector_row BETWEEN 1 AND 4),
    FOREIGN KEY (location_id,campaign_id)
        REFERENCES loc_location(location_id,campaign_id),
    FOREIGN KEY (sector_location_id,campaign_id)
        REFERENCES loc_sector(location_id,campaign_id),
    UNIQUE (location_id,sector_location_id,campaign_id),
    UNIQUE (
        campaign_id,sector_location_id,subsector_column,subsector_row
    )
);

CREATE TABLE loc_star_system (
    location_id bigint PRIMARY KEY,
    campaign_id bigint NOT NULL,
    sector_location_id bigint NOT NULL,
    subsector_location_id bigint,
    hex_column smallint NOT NULL CHECK (hex_column BETWEEN 1 AND 32),
    hex_row smallint NOT NULL CHECK (hex_row BETWEEN 1 AND 40),
    discovery_status text NOT NULL DEFAULT 'known' CHECK (
        discovery_status IN (
            'unknown','suspected','charted','surveyed','known'
        )
    ),
    FOREIGN KEY (location_id,campaign_id)
        REFERENCES loc_location(location_id,campaign_id),
    FOREIGN KEY (sector_location_id,campaign_id)
        REFERENCES loc_sector(location_id,campaign_id),
    FOREIGN KEY (
        subsector_location_id,sector_location_id,campaign_id
    ) REFERENCES loc_subsector(
        location_id,sector_location_id,campaign_id
    ),
    UNIQUE (location_id,campaign_id),
    UNIQUE (campaign_id,sector_location_id,hex_column,hex_row)
);

CREATE TABLE loc_celestial_body (
    location_id bigint PRIMARY KEY,
    campaign_id bigint NOT NULL,
    system_location_id bigint NOT NULL,
    parent_body_location_id bigint,
    body_kind text NOT NULL CHECK (
        body_kind IN (
            'star','planet','dwarf_planet','moon',
            'asteroid_belt','gas_giant','other'
        )
    ),
    orbit_order smallint CHECK (orbit_order >= 0),
    FOREIGN KEY (location_id,campaign_id)
        REFERENCES loc_location(location_id,campaign_id),
    FOREIGN KEY (system_location_id,campaign_id)
        REFERENCES loc_star_system(location_id,campaign_id),
    UNIQUE (location_id,campaign_id),
    UNIQUE (location_id,system_location_id,campaign_id),
    FOREIGN KEY (
        parent_body_location_id,system_location_id,campaign_id
    ) REFERENCES loc_celestial_body(
        location_id,system_location_id,campaign_id
    ),
    CHECK (parent_body_location_id IS NULL
           OR parent_body_location_id <> location_id)
);

CREATE TABLE loc_world_profile (
    world_profile_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    location_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    revision_number integer NOT NULL CHECK (revision_number > 0),
    starport_code text NOT NULL CHECK (
        starport_code ~ '^[A-HX][0-9]?$'
    ),
    size_code smallint NOT NULL CHECK (size_code BETWEEN 0 AND 15),
    atmosphere_code smallint NOT NULL CHECK (
        atmosphere_code BETWEEN 0 AND 15
    ),
    hydrographics_code smallint NOT NULL CHECK (
        hydrographics_code BETWEEN 0 AND 15
    ),
    population_code smallint NOT NULL CHECK (
        population_code BETWEEN 0 AND 15
    ),
    government_code smallint NOT NULL CHECK (
        government_code BETWEEN 0 AND 15
    ),
    law_level_code smallint NOT NULL CHECK (
        law_level_code BETWEEN 0 AND 15
    ),
    technology_level smallint NOT NULL CHECK (
        technology_level BETWEEN 0 AND 35
    ),
    profile_status text NOT NULL DEFAULT 'current' CHECK (
        profile_status IN ('current','superseded')
    ),
    effective_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    ended_at timestamptz,
    source_rule_id bigint REFERENCES rule_rule(rule_id),
    FOREIGN KEY (location_id,campaign_id)
        REFERENCES loc_celestial_body(location_id,campaign_id),
    UNIQUE (location_id,revision_number),
    CHECK (
        (profile_status='current' AND ended_at IS NULL)
        OR (profile_status='superseded' AND ended_at IS NOT NULL)
    )
);

CREATE UNIQUE INDEX loc_one_current_world_profile
    ON loc_world_profile(campaign_id,location_id)
    WHERE profile_status='current';

CREATE TABLE loc_trade_code (
    trade_code_rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    trade_code text NOT NULL UNIQUE CHECK (
        trade_code ~ '^[A-Za-z][A-Za-z0-9]{0,7}$'
    )
);

CREATE TABLE loc_world_trade_code (
    world_profile_id bigint NOT NULL REFERENCES
        loc_world_profile(world_profile_id),
    trade_code_rule_id bigint NOT NULL REFERENCES
        loc_trade_code(trade_code_rule_id),
    source_rule_id bigint REFERENCES rule_rule(rule_id),
    PRIMARY KEY (world_profile_id,trade_code_rule_id)
);

CREATE TABLE loc_star_route (
    star_route_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    from_system_location_id bigint NOT NULL,
    to_system_location_id bigint NOT NULL,
    distance_parsecs numeric NOT NULL CHECK (distance_parsecs > 0),
    bidirectional boolean NOT NULL DEFAULT true,
    navigation_status text NOT NULL DEFAULT 'charted' CHECK (
        navigation_status IN (
            'unknown','suspected','charted','hazardous','closed'
        )
    ),
    route_status text NOT NULL DEFAULT 'active' CHECK (
        route_status IN ('active','ended')
    ),
    effective_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    ended_at timestamptz,
    FOREIGN KEY (from_system_location_id,campaign_id)
        REFERENCES loc_star_system(location_id,campaign_id),
    FOREIGN KEY (to_system_location_id,campaign_id)
        REFERENCES loc_star_system(location_id,campaign_id),
    CHECK (from_system_location_id <> to_system_location_id),
    CHECK (
        (route_status='active' AND ended_at IS NULL)
        OR (route_status='ended' AND ended_at IS NOT NULL)
    )
);

CREATE UNIQUE INDEX loc_one_active_star_route
    ON loc_star_route(
        campaign_id,from_system_location_id,to_system_location_id
    )
    WHERE route_status='active';

COMMENT ON TABLE loc_containment IS
    'Current containment is acyclic and gives each child one direct parent.';
COMMENT ON TABLE loc_world_profile IS
    'Versioned Cepheus world profile; prior revisions remain immutable history.';
COMMENT ON TABLE actor_note IS
    'Authored annotation only; notes are not canonical mechanical facts.';
