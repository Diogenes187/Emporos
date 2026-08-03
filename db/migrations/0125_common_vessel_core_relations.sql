ALTER TABLE ship_class_drive
    ADD COLUMN validation_status text NOT NULL DEFAULT 'validated' CHECK (
        validation_status IN ('validated','published_conflict')
    );

CREATE TABLE ship_class_published_armor (
    ship_class_rule_id bigint PRIMARY KEY REFERENCES
        ship_class_design_hull(ship_class_rule_id),
    armor_code text NOT NULL REFERENCES
        rule_ship_armor_design(armor_code),
    armor_value smallint NOT NULL CHECK (armor_value>0),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

CREATE OR REPLACE FUNCTION ship_validate_design_hull()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    class_hull_tons numeric;
    class_configuration text;
    catalog_hull_tons numeric;
    armor_tl smallint;
    class_tl smallint;
BEGIN
    SELECT hull_tons,hull_configuration,minimum_tech_level
    INTO class_hull_tons,class_configuration,class_tl
    FROM ship_class
    WHERE ship_class_rule_id=NEW.ship_class_rule_id;

    SELECT hull_tons INTO catalog_hull_tons
    FROM rule_ship_hull_design
    WHERE hull_code=NEW.hull_code;

    IF class_hull_tons<>catalog_hull_tons
       OR (
           class_configuration IS NOT NULL
           AND class_configuration<>NEW.configuration_code
       ) THEN
        RAISE EXCEPTION
            'Ship class hull design conflicts with published hull'
            USING ERRCODE='23514';
    END IF;

    IF NEW.armor_code IS NOT NULL THEN
        SELECT minimum_tech_level INTO armor_tl
        FROM rule_ship_armor_design
        WHERE armor_code=NEW.armor_code;
        IF class_tl<armor_tl THEN
            RAISE EXCEPTION
                'Ship class tech level is below selected armor'
                USING ERRCODE='23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION ship_validate_class_drive()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    selected_hull_code text;
    hull_scale text;
    published_performance smallint;
    class_performance smallint;
    conflict_recorded boolean;
BEGIN
    SELECT design.hull_code,hull.craft_scale
    INTO selected_hull_code,hull_scale
    FROM ship_class_design_hull design
    JOIN rule_ship_hull_design hull
      ON hull.hull_code=design.hull_code
    WHERE design.ship_class_rule_id=NEW.ship_class_rule_id;

    SELECT CASE NEW.drive_kind
               WHEN 'jump' THEN jump_rating
               WHEN 'maneuver' THEN maneuver_rating
               ELSE power_rating
           END
    INTO class_performance
    FROM ship_class
    WHERE ship_class_rule_id=NEW.ship_class_rule_id;

    IF NEW.craft_scale<>hull_scale
       OR NEW.performance<>class_performance THEN
        RAISE EXCEPTION
            'Ship class drive conflicts with class scale or performance'
            USING ERRCODE='23514';
    END IF;

    IF NEW.drive_kind='power_plant' THEN
        RETURN NEW;
    END IF;

    SELECT performance INTO published_performance
    FROM rule_ship_drive_performance
    WHERE craft_scale=NEW.craft_scale
      AND drive_code=NEW.drive_code
      AND hull_code=selected_hull_code;

    IF NEW.validation_status='validated'
       AND (
           published_performance IS NULL
           OR NEW.performance<>published_performance
       ) THEN
        RAISE EXCEPTION
            'Ship class drive conflicts with hull performance matrix'
            USING ERRCODE='23514';
    END IF;

    IF NEW.validation_status='published_conflict' THEN
        SELECT EXISTS (
            SELECT 1
            FROM ship_class_source_assertion assertion
            WHERE assertion.ship_class_rule_id=NEW.ship_class_rule_id
              AND assertion.field_code=NEW.drive_kind||'-drive-performance'
              AND assertion.assertion_status='unresolved_conflict'
        )
        INTO conflict_recorded;
        IF NOT conflict_recorded
           OR published_performance=NEW.performance THEN
            RAISE EXCEPTION
                'Published drive conflict lacks unresolved source assertion'
                USING ERRCODE='23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

INSERT INTO ship_class_source_assertion (
    ship_class_rule_id,field_code,published_value,canonical_value,
    assertion_status,rationale,source_locator_id
)
SELECT class.ship_class_rule_id,source.field_code,
       source.published_value,source.canonical_value,
       source.assertion_status,source.rationale,class.source_locator_id
FROM (
    VALUES
        ('raider','jump-drive','M','D','reconciled',
         'The printed drive letters are transposed: code D gives Jump-1 on a 600-ton hull and code M gives the stated 4-G maneuver performance.'),
        ('raider','maneuver-drive','D','M','reconciled',
         'The printed drive letters are transposed: code M gives 4-G on a 600-ton hull and also matches power plant M.'),
        ('destroyer','jump-drive-performance','D / Jump-2',NULL,
         'unresolved_conflict',
         'Drive D produces Jump-1 on an 800-ton hull, while the design states Jump-2 and carries fuel for two Jump-2 transits.'),
        ('destroyer','maneuver-drive-performance','M / 4-G',NULL,
         'unresolved_conflict',
         'Drive M produces 3-G on an 800-ton hull, while the design states 4-G; its power-plant fuel total corroborates power plant M.')
) source(
    class_code,field_code,published_value,canonical_value,
    assertion_status,rationale
)
JOIN ship_class class
  ON class.class_code=source.class_code;

INSERT INTO ship_class_design_hull (
    ship_class_rule_id,hull_code,configuration_code,
    armor_code,armor_increments
)
SELECT class.ship_class_rule_id,source.hull_code,
       class.hull_configuration,NULL,0
FROM (
    VALUES
        ('asteroid-miner','2'),('corvette','3'),('courier','1'),
        ('destroyer','8'),('dreadnought','P'),('frontier-trader','3'),
        ('heavy-cruiser','L'),('light-cruiser','A'),
        ('merchant-freighter','4'),('merchant-liner','3'),
        ('merchant-trader','2'),('patrol-frigate','3'),('raider','6'),
        ('research-vessel','2'),('survey-vessel','3'),
        ('system-defense-boat','4'),('system-monitor','A'),('yacht','1'),
        ('cutter','s9'),('fighter','s1'),('launch','s3'),
        ('pinnace','s7'),('ships-boat','s5'),('shuttle','sH')
) source(class_code,hull_code)
JOIN ship_class class
  ON class.class_code=source.class_code;

INSERT INTO ship_class_published_armor (
    ship_class_rule_id,armor_code,armor_value,source_locator_id
)
SELECT class.ship_class_rule_id,source.armor_code,
       source.armor_value,class.source_locator_id
FROM (
    VALUES
        ('asteroid-miner','titanium-steel',2::smallint),
        ('corvette','crystaliron',8),('courier','titanium-steel',2),
        ('destroyer','crystaliron',11),
        ('dreadnought','bonded-superdense',14),
        ('frontier-trader','titanium-steel',2),
        ('heavy-cruiser','crystaliron',11),
        ('light-cruiser','crystaliron',11),
        ('merchant-freighter','titanium-steel',2),
        ('merchant-liner','titanium-steel',2),
        ('merchant-trader','titanium-steel',2),
        ('patrol-frigate','crystaliron',8),
        ('raider','titanium-steel',8),
        ('research-vessel','titanium-steel',2),
        ('survey-vessel','titanium-steel',2),
        ('system-defense-boat','titanium-steel',8),
        ('system-monitor','titanium-steel',9),
        ('yacht','titanium-steel',2)
) source(class_code,armor_code,armor_value)
JOIN ship_class class
  ON class.class_code=source.class_code;

INSERT INTO ship_class_armor_option (
    ship_class_rule_id,armor_option_code,installation_count
)
SELECT class.ship_class_rule_id,'stealth',1
FROM ship_class class
WHERE class.class_code IN (
    'corvette','destroyer','dreadnought','heavy-cruiser',
    'light-cruiser','patrol-frigate'
);

INSERT INTO ship_class_drive (
    ship_class_rule_id,drive_kind,craft_scale,
    drive_code,performance,validation_status
)
SELECT class.ship_class_rule_id,drive.drive_kind,class.craft_scale,
       drive.drive_code,drive.performance,drive.validation_status
FROM (
    VALUES
        ('asteroid-miner','A','A','A','validated','validated'),
        ('corvette','C','J','J','validated','validated'),
        ('courier','A','B','B','validated','validated'),
        ('destroyer','D','M','M','published_conflict','published_conflict'),
        ('dreadnought','Z','Z','Z','validated','validated'),
        ('frontier-trader','B','C','C','validated','validated'),
        ('heavy-cruiser','N','N','N','validated','validated'),
        ('light-cruiser','H','L','L','validated','validated'),
        ('merchant-freighter','B','B','B','validated','validated'),
        ('merchant-liner','B','B','B','validated','validated'),
        ('merchant-trader','A','A','A','validated','validated'),
        ('patrol-frigate','C','F','F','validated','validated'),
        ('raider','D','M','M','validated','validated'),
        ('research-vessel','A','A','A','validated','validated'),
        ('survey-vessel','B','C','C','validated','validated'),
        ('system-defense-boat',NULL,'M','M',NULL,'validated'),
        ('system-monitor',NULL,'X','X',NULL,'validated'),
        ('yacht','A','A','A','validated','validated'),
        ('cutter',NULL,'sK','sK',NULL,'validated'),
        ('fighter',NULL,'sC','sL',NULL,'validated'),
        ('launch',NULL,'sA','sA',NULL,'validated'),
        ('pinnace',NULL,'sK','sL',NULL,'validated'),
        ('ships-boat',NULL,'sJ','sJ',NULL,'validated'),
        ('shuttle',NULL,'sN','sN',NULL,'validated')
) source(
    class_code,jump_code,maneuver_code,power_code,
    jump_status,maneuver_status
)
JOIN ship_class class
  ON class.class_code=source.class_code
CROSS JOIN LATERAL (
    VALUES
        ('jump',source.jump_code,class.jump_rating,source.jump_status),
        ('maneuver',source.maneuver_code,class.maneuver_rating,
         source.maneuver_status),
        ('power_plant',source.power_code,class.power_rating,'validated')
) drive(drive_kind,drive_code,performance,validation_status)
WHERE drive.drive_code IS NOT NULL;

INSERT INTO ship_class_computer (
    ship_class_rule_id,computer_code
)
SELECT class.ship_class_rule_id,'model-'||source.model_number
FROM (
    VALUES
        ('asteroid-miner',2),('corvette',3),('courier',2),
        ('destroyer',3),('dreadnought',6),('frontier-trader',2),
        ('heavy-cruiser',3),('light-cruiser',3),
        ('merchant-freighter',2),('merchant-liner',2),
        ('merchant-trader',2),('patrol-frigate',3),('raider',2),
        ('research-vessel',2),('survey-vessel',2),
        ('system-defense-boat',2),('system-monitor',2),('yacht',2),
        ('cutter',1),('fighter',1),('launch',1),('pinnace',1),
        ('ships-boat',1),('shuttle',1)
) source(class_code,model_number)
JOIN ship_class class
  ON class.class_code=source.class_code;

INSERT INTO ship_class_computer_option (
    ship_class_rule_id,computer_option_code
)
SELECT ship_class_rule_id,'fib'
FROM ship_class
WHERE class_code IN (
    'corvette','destroyer','dreadnought','heavy-cruiser',
    'light-cruiser','patrol-frigate','raider',
    'system-defense-boat','system-monitor','fighter'
);

INSERT INTO ship_class_software (
    ship_class_rule_id,software_code,software_level,allocated_rating
)
SELECT ship_class_rule_id,'jump-control',2,10
FROM ship_class
WHERE class_code IN ('courier','yacht');

INSERT INTO ship_class_electronics (
    ship_class_rule_id,electronics_code
)
SELECT class.ship_class_rule_id,source.electronics_code
FROM (
    VALUES
        ('asteroid-miner','basic-civilian'),('corvette','advanced'),
        ('courier','basic-civilian'),('destroyer','advanced'),
        ('dreadnought','very-advanced'),('frontier-trader','basic-civilian'),
        ('heavy-cruiser','advanced'),('light-cruiser','advanced'),
        ('merchant-freighter','basic-civilian'),
        ('merchant-liner','basic-civilian'),
        ('merchant-trader','basic-civilian'),('patrol-frigate','advanced'),
        ('raider','basic-civilian'),('research-vessel','basic-civilian'),
        ('survey-vessel','basic-civilian'),
        ('system-defense-boat','basic-civilian'),
        ('system-monitor','basic-civilian'),('yacht','basic-civilian'),
        ('cutter','standard'),('fighter','standard'),('launch','standard'),
        ('pinnace','standard'),('ships-boat','standard'),('shuttle','standard')
) source(class_code,electronics_code)
JOIN ship_class class
  ON class.class_code=source.class_code;
