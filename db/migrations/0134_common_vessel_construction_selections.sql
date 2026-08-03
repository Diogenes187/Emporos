ALTER TABLE ship_class_weapon_mount
    ADD COLUMN pricing_mount_code text REFERENCES
        rule_ship_weapon_mount(mount_code),
    ADD CONSTRAINT ship_class_fixed_mount_pricing_check CHECK (
        (mount_code='fixed-mount' AND pricing_mount_code IN (
            'single-turret','double-turret','triple-turret'
        ))
        OR
        (mount_code<>'fixed-mount' AND pricing_mount_code IS NULL)
    );

UPDATE rule_ship_weapon_mount mount
SET allocated_tons=source.mount_tons,
    fire_control_tons=source.fire_control_tons
FROM (
    VALUES
        ('single-turret',0::numeric,1::numeric),
        ('double-turret',0,1),
        ('triple-turret',0,1),
        ('pop-up-turret',1,1),
        ('fixed-mount',0,1),
        ('bay',50,1)
) source(mount_code,mount_tons,fire_control_tons)
WHERE source.mount_code=mount.mount_code;

UPDATE ship_class_weapon_mount mount
SET pricing_mount_code='single-turret'
FROM ship_class class
WHERE class.ship_class_rule_id=mount.ship_class_rule_id
  AND class.class_code='fighter'
  AND mount.mount_identifier='fixed-pulse-laser';

UPDATE ship_class_design_hull design
SET armor_code=source.armor_code,
    armor_increments=source.armor_increments
FROM ship_class class
JOIN (
    VALUES
        ('asteroid-miner','titanium-steel',1::smallint),
        ('corvette','crystaliron',2),
        ('courier','titanium-steel',1),
        ('destroyer','crystaliron',3),
        ('dreadnought','bonded-superdense',3),
        ('frontier-trader','titanium-steel',1),
        ('heavy-cruiser','crystaliron',3),
        ('light-cruiser','crystaliron',3),
        ('merchant-freighter','titanium-steel',1),
        ('merchant-liner','titanium-steel',1),
        ('merchant-trader','titanium-steel',1),
        ('patrol-frigate','crystaliron',2),
        ('raider','titanium-steel',4),
        ('research-vessel','titanium-steel',1),
        ('survey-vessel','titanium-steel',1),
        ('system-defense-boat','titanium-steel',4),
        ('system-monitor','titanium-steel',5),
        ('yacht','titanium-steel',1)
) source(class_code,armor_code,armor_increments)
  ON source.class_code=class.class_code
WHERE design.ship_class_rule_id=class.ship_class_rule_id;

CREATE OR REPLACE FUNCTION ship_validate_published_armor()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    selected_armor_code text;
    selected_increments smallint;
    protection_per_increment smallint;
    class_tl smallint;
    expected_armor smallint;
BEGIN
    SELECT design.armor_code,design.armor_increments,
           armor.protection_per_increment,class.minimum_tech_level
    INTO selected_armor_code,selected_increments,
         protection_per_increment,class_tl
    FROM ship_class_design_hull design
    JOIN ship_class class
      ON class.ship_class_rule_id=design.ship_class_rule_id
    LEFT JOIN rule_ship_armor_design armor
      ON armor.armor_code=design.armor_code
    WHERE design.ship_class_rule_id=NEW.ship_class_rule_id;

    expected_armor:=least(
        selected_increments*protection_per_increment,
        class_tl
    );

    IF NEW.armor_code<>selected_armor_code
       OR NEW.armor_value<>expected_armor THEN
        RAISE EXCEPTION
            'Published armor conflicts with construction selection'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER ship_published_armor_valid
BEFORE INSERT OR UPDATE ON ship_class_published_armor
FOR EACH ROW EXECUTE FUNCTION ship_validate_published_armor();
