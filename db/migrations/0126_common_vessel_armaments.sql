CREATE OR REPLACE FUNCTION ship_validate_class_weapon_mount()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    class_tl smallint;
    hardpoint_capacity numeric;
    mount_tl smallint;
    hardpoints_per_mount smallint;
    hardpoints_already integer;
BEGIN
    SELECT class.minimum_tech_level,characteristic.characteristic_value
    INTO class_tl,hardpoint_capacity
    FROM ship_class class
    JOIN ship_class_characteristic characteristic
      ON characteristic.ship_class_rule_id=class.ship_class_rule_id
     AND characteristic.characteristic_code='hardpoints'
    WHERE class.ship_class_rule_id=NEW.ship_class_rule_id;

    IF hardpoint_capacity IS NULL THEN
        SELECT floor(hull_tons/100)
        INTO hardpoint_capacity
        FROM ship_class
        WHERE ship_class_rule_id=NEW.ship_class_rule_id;
    END IF;

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
          hardpoint_capacity THEN
        RAISE EXCEPTION
            'Ship weapon mounts exceed tech level or hardpoints'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

INSERT INTO ship_class_weapon_mount (
    ship_class_rule_id,mount_code,mount_identifier,mount_count
)
SELECT class.ship_class_rule_id,source.mount_code,
       source.mount_identifier,source.mount_count
FROM (
    VALUES
        ('corvette','triple-turret','missile-turrets',2),
        ('corvette','triple-turret','beam-turrets',1),
        ('destroyer','triple-turret','missile-turrets',2),
        ('destroyer','triple-turret','beam-turrets',6),
        ('dreadnought','bay','fusion-bays',10),
        ('dreadnought','bay','missile-bays',5),
        ('dreadnought','triple-turret','beam-turrets',35),
        ('frontier-trader','triple-turret','pulse-turrets',2),
        ('frontier-trader','triple-turret','sand-turret',1),
        ('heavy-cruiser','bay','missile-bays',4),
        ('heavy-cruiser','triple-turret','pulse-turrets',16),
        ('light-cruiser','bay','particle-bay',1),
        ('light-cruiser','triple-turret','missile-turrets',3),
        ('light-cruiser','triple-turret','beam-turrets',6),
        ('patrol-frigate','triple-turret','missile-turrets',2),
        ('patrol-frigate','triple-turret','beam-turret',1),
        ('raider','triple-turret','beam-turrets',6),
        ('survey-vessel','triple-turret','beam-turrets',3),
        ('system-defense-boat','triple-turret','missile-turrets',2),
        ('system-defense-boat','triple-turret','beam-turrets',2),
        ('system-monitor','bay','particle-bay',1),
        ('system-monitor','triple-turret','missile-turrets',3),
        ('system-monitor','triple-turret','pulse-turrets',3),
        ('system-monitor','triple-turret','particle-turrets',3),
        ('fighter','fixed-mount','fixed-pulse-laser',1)
) source(class_code,mount_code,mount_identifier,mount_count)
JOIN ship_class class
  ON class.class_code=source.class_code;

INSERT INTO ship_class_mount_weapon (
    class_weapon_mount_id,ship_class_rule_id,
    weapon_slot,weapon_rule_id
)
SELECT mount.class_weapon_mount_id,mount.ship_class_rule_id,
       slot.weapon_slot,weapon.weapon_rule_id
FROM ship_class_weapon_mount mount
JOIN ship_class class
  ON class.ship_class_rule_id=mount.ship_class_rule_id
JOIN (
    VALUES
        ('corvette','missile-turrets','missile-rack',3),
        ('corvette','beam-turrets','beam-laser',3),
        ('destroyer','missile-turrets','missile-rack',3),
        ('destroyer','beam-turrets','beam-laser',3),
        ('dreadnought','fusion-bays','fusion-gun-bay',1),
        ('dreadnought','missile-bays','missile-bank',1),
        ('dreadnought','beam-turrets','beam-laser',3),
        ('frontier-trader','pulse-turrets','pulse-laser',3),
        ('frontier-trader','sand-turret','sandcaster',3),
        ('heavy-cruiser','missile-bays','missile-bank',1),
        ('heavy-cruiser','pulse-turrets','pulse-laser',3),
        ('light-cruiser','particle-bay','particle-beam-bay',1),
        ('light-cruiser','missile-turrets','missile-rack',3),
        ('light-cruiser','beam-turrets','beam-laser',3),
        ('patrol-frigate','missile-turrets','missile-rack',3),
        ('patrol-frigate','beam-turret','beam-laser',3),
        ('raider','beam-turrets','beam-laser',3),
        ('survey-vessel','beam-turrets','beam-laser',3),
        ('system-defense-boat','missile-turrets','missile-rack',3),
        ('system-defense-boat','beam-turrets','beam-laser',3),
        ('system-monitor','particle-bay','particle-beam-bay',1),
        ('system-monitor','missile-turrets','missile-rack',3),
        ('system-monitor','pulse-turrets','pulse-laser',3),
        ('system-monitor','particle-turrets','particle-beam-turret',3),
        ('fighter','fixed-pulse-laser','pulse-laser',1)
) source(class_code,mount_identifier,weapon_code,slot_count)
  ON source.class_code=class.class_code
 AND source.mount_identifier=mount.mount_identifier
JOIN ship_weapon_definition weapon
  ON weapon.weapon_code=source.weapon_code
CROSS JOIN LATERAL generate_series(
    1,source.slot_count
) slot(weapon_slot);

INSERT INTO ship_class_missile_store (
    ship_class_rule_id,missile_code,missile_count,allocated_tons
)
SELECT class.ship_class_rule_id,'smart',source.missile_count,
       source.missile_count/12.0
FROM (
    VALUES
        ('corvette',120),('destroyer',360),('dreadnought',3600),
        ('heavy-cruiser',2160),('light-cruiser',540),
        ('patrol-frigate',120),('system-defense-boat',360),
        ('system-monitor',1080)
) source(class_code,missile_count)
JOIN ship_class class
  ON class.class_code=source.class_code;

INSERT INTO ship_class_sand_store (
    ship_class_rule_id,ammunition_code,barrel_count,allocated_tons
)
SELECT ship_class_rule_id,'sand-barrel',100,5
FROM ship_class
WHERE class_code='frontier-trader';

INSERT INTO ship_class_screen (
    ship_class_rule_id,screen_code,screen_count
)
SELECT class.ship_class_rule_id,source.screen_code,1
FROM (
    VALUES
        ('dreadnought','meson-screen'),
        ('dreadnought','nuclear-damper')
) source(class_code,screen_code)
JOIN ship_class class
  ON class.class_code=source.class_code;
