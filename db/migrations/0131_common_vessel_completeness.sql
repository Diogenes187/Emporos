CREATE TABLE ship_class_armament_declaration (
    ship_class_rule_id bigint PRIMARY KEY REFERENCES
        ship_class(ship_class_rule_id),
    armament_status text NOT NULL CHECK (
        armament_status IN (
            'armed','explicitly_unarmed','no_loadout_listed'
        )
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

CREATE OR REPLACE FUNCTION ship_validate_armament_declaration()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    has_mounts boolean;
BEGIN
    SELECT EXISTS (
        SELECT 1
        FROM ship_class_weapon_mount
        WHERE ship_class_rule_id=NEW.ship_class_rule_id
    )
    INTO has_mounts;

    IF (NEW.armament_status='armed' AND NOT has_mounts)
       OR (
           NEW.armament_status<>'armed'
           AND has_mounts
       ) THEN
        RAISE EXCEPTION
            'Ship armament declaration conflicts with mounted weapons'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER ship_armament_declaration_valid
BEFORE INSERT OR UPDATE ON ship_class_armament_declaration
FOR EACH ROW EXECUTE FUNCTION ship_validate_armament_declaration();

INSERT INTO ship_class_armament_declaration (
    ship_class_rule_id,armament_status,source_locator_id
)
SELECT class.ship_class_rule_id,source.armament_status,
       class.source_locator_id
FROM (
    VALUES
        ('asteroid-miner','no_loadout_listed'),
        ('corvette','armed'),('courier','explicitly_unarmed'),
        ('destroyer','armed'),('dreadnought','armed'),
        ('frontier-trader','armed'),('heavy-cruiser','armed'),
        ('light-cruiser','armed'),
        ('merchant-freighter','explicitly_unarmed'),
        ('merchant-liner','explicitly_unarmed'),
        ('merchant-trader','no_loadout_listed'),
        ('patrol-frigate','armed'),('raider','armed'),
        ('research-vessel','explicitly_unarmed'),
        ('survey-vessel','armed'),('system-defense-boat','armed'),
        ('system-monitor','armed'),('yacht','explicitly_unarmed'),
        ('cutter','explicitly_unarmed'),('fighter','armed'),
        ('launch','explicitly_unarmed'),('pinnace','explicitly_unarmed'),
        ('ships-boat','explicitly_unarmed'),('shuttle','explicitly_unarmed')
) source(class_code,armament_status)
JOIN ship_class class
  ON class.class_code=source.class_code;

CREATE VIEW ship_class_catalogue_completeness AS
SELECT class.ship_class_rule_id,
       class.class_code,
       class.craft_scale,
       (hull.ship_class_rule_id IS NOT NULL) AS has_hull,
       (
           SELECT count(*)
           FROM ship_class_drive drive
           WHERE drive.ship_class_rule_id=class.ship_class_rule_id
       )=CASE
             WHEN class.craft_scale='small_craft' THEN 2
             WHEN class.jump_rating=0 THEN 2
             ELSE 3
         END AS has_required_drives,
       (computer.ship_class_rule_id IS NOT NULL) AS has_computer,
       (electronics.ship_class_rule_id IS NOT NULL) AS has_electronics,
       EXISTS (
           SELECT 1
           FROM ship_class_component selected
           JOIN ship_component_definition component
             ON component.component_rule_id=selected.component_rule_id
           WHERE selected.ship_class_rule_id=class.ship_class_rule_id
             AND component.component_code='cargo-hold'
             AND selected.allocated_tons=class.cargo_capacity_tons
       ) AS has_published_cargo,
       EXISTS (
           SELECT 1
           FROM ship_class_component selected
           JOIN ship_component_definition component
             ON component.component_rule_id=selected.component_rule_id
           WHERE selected.ship_class_rule_id=class.ship_class_rule_id
             AND (
                 (
                     class.craft_scale='starship'
                     AND component.component_code='stateroom'
                 )
                 OR
                 (
                     class.craft_scale='small_craft'
                     AND component.component_code IN (
                         'one-person-cockpit','two-person-cockpit',
                         'one-person-control-cabin',
                         'two-person-control-cabin'
                     )
                 )
             )
       ) AS has_control_accommodation,
       (armament.ship_class_rule_id IS NOT NULL)
           AS has_armament_declaration,
       (
           SELECT count(*)
           FROM ship_class_source_assertion assertion
           WHERE assertion.ship_class_rule_id=class.ship_class_rule_id
             AND assertion.assertion_status IN (
                 'unresolved_conflict','source_unspecified'
             )
       ) AS unresolved_source_assertions,
       (
           hull.ship_class_rule_id IS NOT NULL
           AND computer.ship_class_rule_id IS NOT NULL
           AND electronics.ship_class_rule_id IS NOT NULL
           AND armament.ship_class_rule_id IS NOT NULL
           AND (
               SELECT count(*)
               FROM ship_class_drive drive
               WHERE drive.ship_class_rule_id=class.ship_class_rule_id
           )=CASE
                 WHEN class.craft_scale='small_craft' THEN 2
                 WHEN class.jump_rating=0 THEN 2
                 ELSE 3
             END
           AND EXISTS (
               SELECT 1
               FROM ship_class_component selected
               JOIN ship_component_definition component
                 ON component.component_rule_id=selected.component_rule_id
               WHERE selected.ship_class_rule_id=class.ship_class_rule_id
                 AND component.component_code='cargo-hold'
                 AND selected.allocated_tons=class.cargo_capacity_tons
           )
       ) AS is_structurally_complete
FROM ship_class class
LEFT JOIN ship_class_design_hull hull
  ON hull.ship_class_rule_id=class.ship_class_rule_id
LEFT JOIN ship_class_computer computer
  ON computer.ship_class_rule_id=class.ship_class_rule_id
LEFT JOIN ship_class_electronics electronics
  ON electronics.ship_class_rule_id=class.ship_class_rule_id
LEFT JOIN ship_class_armament_declaration armament
  ON armament.ship_class_rule_id=class.ship_class_rule_id;
