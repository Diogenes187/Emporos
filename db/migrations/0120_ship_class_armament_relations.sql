CREATE TABLE rule_ship_sand_ammunition (
    ammunition_code text PRIMARY KEY CHECK (
        ammunition_code='sand-barrel'
    ),
    minimum_tech_level smallint NOT NULL CHECK (
        minimum_tech_level>=0
    ),
    units_per_ton smallint NOT NULL CHECK (units_per_ton>0),
    cost_minor_per_ton bigint NOT NULL CHECK (
        cost_minor_per_ton>0
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_ship_sand_ammunition
SELECT 'sand-barrel',5,20,10000,source_locator_id
FROM src_locator
WHERE heading_path=
      'Ship Design and Construction > Armaments > Turrets';

CREATE TABLE ship_class_weapon_mount (
    class_weapon_mount_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ship_class_rule_id bigint NOT NULL REFERENCES
        ship_class(ship_class_rule_id),
    mount_code text NOT NULL REFERENCES
        rule_ship_weapon_mount(mount_code),
    mount_identifier text NOT NULL CHECK (
        btrim(mount_identifier)<>''
    ),
    mount_count smallint NOT NULL DEFAULT 1 CHECK (mount_count>0),
    UNIQUE (class_weapon_mount_id,ship_class_rule_id),
    UNIQUE (ship_class_rule_id,mount_identifier)
);

CREATE TABLE ship_class_mount_weapon (
    class_weapon_mount_id bigint NOT NULL,
    ship_class_rule_id bigint NOT NULL,
    weapon_slot smallint NOT NULL CHECK (weapon_slot>0),
    weapon_rule_id bigint NOT NULL REFERENCES
        ship_weapon_definition(weapon_rule_id),
    PRIMARY KEY (class_weapon_mount_id,weapon_slot),
    FOREIGN KEY (class_weapon_mount_id,ship_class_rule_id)
        REFERENCES ship_class_weapon_mount(
            class_weapon_mount_id,ship_class_rule_id
        )
);

CREATE TABLE ship_class_screen (
    ship_class_rule_id bigint NOT NULL REFERENCES
        ship_class(ship_class_rule_id),
    screen_code text NOT NULL REFERENCES
        rule_ship_screen(screen_code),
    screen_count smallint NOT NULL DEFAULT 1 CHECK (screen_count>0),
    PRIMARY KEY (ship_class_rule_id,screen_code)
);

CREATE TABLE ship_class_missile_store (
    ship_class_rule_id bigint NOT NULL REFERENCES
        ship_class(ship_class_rule_id),
    missile_code text NOT NULL REFERENCES
        rule_ship_missile(missile_code),
    missile_count integer NOT NULL CHECK (missile_count>0),
    allocated_tons numeric NOT NULL CHECK (allocated_tons>0),
    PRIMARY KEY (ship_class_rule_id,missile_code)
);

CREATE TABLE ship_class_sand_store (
    ship_class_rule_id bigint PRIMARY KEY REFERENCES
        ship_class(ship_class_rule_id),
    ammunition_code text NOT NULL REFERENCES
        rule_ship_sand_ammunition(ammunition_code),
    barrel_count integer NOT NULL CHECK (barrel_count>0),
    allocated_tons numeric NOT NULL CHECK (allocated_tons>0)
);

CREATE OR REPLACE FUNCTION ship_validate_class_weapon_mount()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    class_tl smallint;
    hull_tons numeric;
    mount_tl smallint;
    hardpoints_per_mount smallint;
    hardpoints_already integer;
BEGIN
    SELECT minimum_tech_level,class.hull_tons
    INTO class_tl,hull_tons
    FROM ship_class class
    WHERE ship_class_rule_id=NEW.ship_class_rule_id;

    SELECT minimum_tech_level,hardpoints_used
    INTO mount_tl,hardpoints_per_mount
    FROM rule_ship_weapon_mount
    WHERE mount_code=NEW.mount_code;

    SELECT coalesce(sum(
               existing.mount_count*mount.hardpoints_used
           ),0)
    INTO hardpoints_already
    FROM ship_class_weapon_mount existing
    JOIN rule_ship_weapon_mount mount
      ON mount.mount_code=existing.mount_code
    WHERE existing.ship_class_rule_id=NEW.ship_class_rule_id
      AND (
          TG_OP='INSERT'
          OR existing.class_weapon_mount_id<>
             NEW.class_weapon_mount_id
      );

    IF (mount_tl IS NOT NULL AND class_tl<mount_tl)
       OR hardpoints_already+
          NEW.mount_count*hardpoints_per_mount>
          floor(hull_tons/100) THEN
        RAISE EXCEPTION
            'Ship weapon mounts exceed tech level or hardpoints'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER ship_class_weapon_mount_valid
BEFORE INSERT OR UPDATE ON ship_class_weapon_mount
FOR EACH ROW EXECUTE FUNCTION ship_validate_class_weapon_mount();

CREATE OR REPLACE FUNCTION ship_validate_class_mount_weapon()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    mount_capacity smallint;
    selected_mount_kind text;
    weapon_mount_kind text;
    weapon_tl smallint;
    class_tl smallint;
BEGIN
    SELECT mount.weapon_capacity,mount.mount_kind,
           class.minimum_tech_level
    INTO mount_capacity,selected_mount_kind,class_tl
    FROM ship_class_weapon_mount selected
    JOIN rule_ship_weapon_mount mount
      ON mount.mount_code=selected.mount_code
    JOIN ship_class class
      ON class.ship_class_rule_id=selected.ship_class_rule_id
    WHERE selected.class_weapon_mount_id=
          NEW.class_weapon_mount_id
      AND selected.ship_class_rule_id=NEW.ship_class_rule_id;

    SELECT mount_kind,minimum_tech_level
    INTO weapon_mount_kind,weapon_tl
    FROM ship_weapon_definition
    WHERE weapon_rule_id=NEW.weapon_rule_id;

    IF NEW.weapon_slot>mount_capacity
       OR weapon_mount_kind<>selected_mount_kind
       OR (weapon_tl IS NOT NULL AND class_tl<weapon_tl) THEN
        RAISE EXCEPTION
            'Ship weapon conflicts with mount capacity, type, or tech'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER ship_class_mount_weapon_valid
BEFORE INSERT OR UPDATE ON ship_class_mount_weapon
FOR EACH ROW EXECUTE FUNCTION ship_validate_class_mount_weapon();

CREATE OR REPLACE FUNCTION ship_validate_class_screen()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    class_tl smallint;
    screen_tl smallint;
BEGIN
    SELECT minimum_tech_level INTO class_tl
    FROM ship_class
    WHERE ship_class_rule_id=NEW.ship_class_rule_id;
    SELECT minimum_tech_level INTO screen_tl
    FROM rule_ship_screen
    WHERE screen_code=NEW.screen_code;
    IF class_tl<screen_tl THEN
        RAISE EXCEPTION 'Ship class tech level is below selected screen'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER ship_class_screen_valid
BEFORE INSERT OR UPDATE ON ship_class_screen
FOR EACH ROW EXECUTE FUNCTION ship_validate_class_screen();

CREATE OR REPLACE FUNCTION ship_validate_class_ammunition()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    units_per_ton smallint;
BEGIN
    IF TG_TABLE_NAME='ship_class_missile_store' THEN
        SELECT missile.units_per_ton
        INTO units_per_ton
        FROM rule_ship_missile missile
        WHERE missile_code=NEW.missile_code;
        IF NEW.allocated_tons<>
           NEW.missile_count::numeric/units_per_ton THEN
            RAISE EXCEPTION
                'Ship missile storage tonnage is inconsistent'
                USING ERRCODE='23514';
        END IF;
    ELSE
        SELECT ammunition.units_per_ton
        INTO units_per_ton
        FROM rule_ship_sand_ammunition ammunition
        WHERE ammunition_code=NEW.ammunition_code;
        IF NEW.allocated_tons<>
           NEW.barrel_count::numeric/units_per_ton THEN
            RAISE EXCEPTION
                'Ship sand storage tonnage is inconsistent'
                USING ERRCODE='23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER ship_class_missile_store_valid
BEFORE INSERT OR UPDATE ON ship_class_missile_store
FOR EACH ROW EXECUTE FUNCTION ship_validate_class_ammunition();

CREATE TRIGGER ship_class_sand_store_valid
BEFORE INSERT OR UPDATE ON ship_class_sand_store
FOR EACH ROW EXECUTE FUNCTION ship_validate_class_ammunition();
