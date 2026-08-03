ALTER TABLE ship_ship ADD COLUMN armor_current smallint;

UPDATE ship_ship ship
SET armor_current=coalesce(
    (SELECT armor_value FROM ship_class_published_armor published
     WHERE published.ship_class_rule_id=ship.ship_class_rule_id),
    (SELECT hull.armor_increments*design.protection_per_increment
     FROM ship_class_design_hull hull
     JOIN rule_ship_armor_design design USING (armor_code)
     WHERE hull.ship_class_rule_id=ship.ship_class_rule_id),
    0
);

ALTER TABLE ship_ship
    ALTER COLUMN armor_current SET NOT NULL,
    ADD CHECK (armor_current>=0);

CREATE OR REPLACE FUNCTION ship_validate_instance_state()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE class_hull smallint; class_structure smallint; class_armor smallint;
BEGIN
    SELECT hull_points,structure_points INTO class_hull,class_structure
    FROM ship_class WHERE ship_class_rule_id=NEW.ship_class_rule_id;
    SELECT coalesce(
        (SELECT armor_value FROM ship_class_published_armor
         WHERE ship_class_rule_id=NEW.ship_class_rule_id),
        (SELECT hull.armor_increments*design.protection_per_increment
         FROM ship_class_design_hull hull
         JOIN rule_ship_armor_design design USING (armor_code)
         WHERE hull.ship_class_rule_id=NEW.ship_class_rule_id),0)
    INTO class_armor;
    IF NEW.armor_current IS NULL THEN NEW.armor_current:=class_armor; END IF;
    IF NEW.hull_current>class_hull OR NEW.structure_current>class_structure
       OR NEW.armor_current>class_armor THEN
        RAISE EXCEPTION 'Ship state exceeds class maxima' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;

DROP TRIGGER ship_instance_state_within_class ON ship_ship;
CREATE TRIGGER ship_instance_state_within_class
BEFORE INSERT OR UPDATE OF ship_class_rule_id,hull_current,structure_current,armor_current
ON ship_ship FOR EACH ROW EXECUTE FUNCTION ship_validate_instance_state();

CREATE OR REPLACE FUNCTION senc_validate_weapon_damage_attempt()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE c record; weapon record; ship_row record;
BEGIN
 SELECT check_row.hit,check_row.weapon_rule_id,declaration.target_vessel_id,declaration.campaign_id INTO c
 FROM senc_mount_weapon_attack_check check_row JOIN senc_mount_attack_declaration declaration USING(mount_attack_declaration_id)
 WHERE check_row.mount_weapon_attack_check_id=NEW.mount_weapon_attack_check_id;
 SELECT damage_dice_count,damage_die_sides,damage_modifier,ignores_armor INTO weapon
 FROM ship_weapon_definition WHERE weapon_rule_id=c.weapon_rule_id;
 SELECT vessel.ship_id,ship.armor_current INTO ship_row
 FROM senc_vessel vessel JOIN ship_ship ship USING(ship_id) WHERE vessel.senc_vessel_id=c.target_vessel_id;
 IF NOT c.hit OR weapon.damage_dice_count IS NULL OR NEW.target_ship_id<>ship_row.ship_id OR NEW.campaign_id<>c.campaign_id
  OR NEW.damage_dice_count<>weapon.damage_dice_count OR NEW.damage_die_sides<>weapon.damage_die_sides OR NEW.damage_modifier<>weapon.damage_modifier
  OR NEW.armor_snapshot<>ship_row.armor_current OR NEW.ignores_armor<>weapon.ignores_armor THEN
  RAISE EXCEPTION 'Weapon damage attempt does not match successful check, weapon profile, target, and current armor snapshot' USING ERRCODE='23514';
 END IF; RETURN NEW;
END $$;
