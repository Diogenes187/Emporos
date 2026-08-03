CREATE FUNCTION gf_validate_ground_weapon_battery()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE dice_count integer;
BEGIN
 SELECT damage_dice_count INTO dice_count
   FROM rule_vehicle_weapon_definition
  WHERE weapon_rule_id=NEW.weapon_rule_id;
 IF dice_count IS NULL THEN
   RAISE EXCEPTION 'Ground battery requires a direct-damage weapon';
 END IF;
 RETURN NEW;
END;
$$;
CREATE TRIGGER gf_ground_weapon_battery_valid
BEFORE INSERT OR UPDATE ON gf_ground_weapon_battery
FOR EACH ROW EXECUTE FUNCTION gf_validate_ground_weapon_battery();

CREATE FUNCTION cmd_validate_ground_starship_attack()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE battery gf_ground_weapon_battery%ROWTYPE;
DECLARE volley cmd_ground_starship_volley%ROWTYPE;
DECLARE expected_difficulty bigint;
DECLARE expected_dice integer;
BEGIN
 SELECT * INTO STRICT battery FROM gf_ground_weapon_battery
  WHERE ground_weapon_battery_id=NEW.ground_weapon_battery_id;
 SELECT * INTO STRICT volley FROM cmd_ground_starship_volley
  WHERE command_id=NEW.command_id;
 SELECT matrix.difficulty_rule_id,weapon.damage_dice_count
   INTO expected_difficulty,expected_dice
   FROM rule_vehicle_weapon_definition weapon
   JOIN rule_vehicle_weapon_range_difficulty matrix
     ON matrix.range_profile_code=weapon.range_profile_code
    AND matrix.target_range_code=volley.target_range_code
  WHERE weapon.weapon_rule_id=battery.weapon_rule_id;
 IF battery.campaign_id<>volley.campaign_id
    OR NOT battery.active
    OR NEW.weapon_rule_id<>battery.weapon_rule_id
    OR NEW.weapon_unit_order>battery.operational_weapon_count
    OR NEW.difficulty_rule_id<>expected_difficulty
    OR NEW.damage_dice_count<>expected_dice THEN
   RAISE EXCEPTION 'Ground-starship attack does not match battery facts';
 END IF;
 RETURN NEW;
END;
$$;
CREATE TRIGGER cmd_ground_starship_attack_valid
BEFORE INSERT ON cmd_ground_starship_volley_attack
FOR EACH ROW EXECUTE FUNCTION cmd_validate_ground_starship_attack();

CREATE FUNCTION cmd_reject_ground_starship_history_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Ground-starship volley history is immutable'; END;
$$;
CREATE TRIGGER cmd_ground_starship_volley_attack_immutable
BEFORE UPDATE OR DELETE ON cmd_ground_starship_volley_attack
FOR EACH ROW EXECUTE FUNCTION cmd_reject_ground_starship_history_mutation();
CREATE TRIGGER cmd_ground_starship_final_receipt_immutable
BEFORE UPDATE OR DELETE ON cmd_ground_starship_volley_final_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_ground_starship_history_mutation();
CREATE TRIGGER cmd_ground_starship_damage_die_immutable
BEFORE UPDATE OR DELETE ON cmd_ground_starship_volley_damage_die
FOR EACH ROW EXECUTE FUNCTION cmd_reject_ground_starship_history_mutation();

CREATE FUNCTION cmd_validate_ground_starship_volley()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE attack_count integer;
DECLARE hit_count integer;
DECLARE draw_count integer;
BEGIN
 SELECT count(*),count(*) FILTER (WHERE hit)
   INTO attack_count,hit_count
   FROM cmd_ground_starship_volley_attack
  WHERE command_id=NEW.command_id;
 SELECT count(*) INTO draw_count FROM cmd_random_draw
  WHERE command_id=NEW.command_id AND draw_group='attack';
 IF attack_count=0
    OR hit_count<>NEW.successful_attack_count
    OR draw_count<>attack_count*2 THEN
   RAISE EXCEPTION 'Ground-starship volley attack audit is incomplete';
 END IF;
 RETURN NULL;
END;
$$;
CREATE CONSTRAINT TRIGGER cmd_ground_starship_volley_audit
AFTER INSERT ON cmd_ground_starship_volley
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION cmd_validate_ground_starship_volley();

CREATE FUNCTION cmd_validate_ground_starship_final()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE primary_hit boolean;
DECLARE expected_primary integer;
DECLARE expected_additional integer;
DECLARE die_count integer;
DECLARE die_total integer;
DECLARE draw_count integer;
DECLARE draw_total integer;
DECLARE ship_hull integer;
DECLARE ship_version bigint;
BEGIN
 SELECT hit,damage_dice_count INTO STRICT primary_hit,expected_primary
   FROM cmd_ground_starship_volley_attack
  WHERE command_id=NEW.volley_command_id
    AND attack_order=NEW.primary_attack_order;
 SELECT COALESCE(sum(damage_dice_count),0)
   INTO expected_additional
   FROM cmd_ground_starship_volley_attack
  WHERE command_id=NEW.volley_command_id AND hit
    AND attack_order<>NEW.primary_attack_order;
 SELECT count(*),COALESCE(sum(result),0)
   INTO die_count,die_total
   FROM cmd_ground_starship_volley_damage_die
  WHERE command_id=NEW.command_id;
 SELECT count(*),COALESCE(sum(result),0)
   INTO draw_count,draw_total
   FROM cmd_random_draw
  WHERE command_id=NEW.command_id AND draw_group='damage';
 SELECT ship.hull_current,ship.concurrency_version
   INTO STRICT ship_hull,ship_version
   FROM cmd_ground_starship_volley volley
   JOIN ship_ship ship ON ship.ship_id=volley.target_ship_id
  WHERE volley.command_id=NEW.volley_command_id;
 IF NOT primary_hit
    OR NEW.primary_damage_dice<>expected_primary
    OR NEW.additional_successful_damage_dice<>expected_additional
    OR die_count<>NEW.combined_damage_dice
    OR draw_count<>die_count OR draw_total<>die_total
    OR die_total<>NEW.personal_scale_damage
    OR ship_hull<>NEW.hull_after
    OR ship_version<>NEW.ship_version_after THEN
   RAISE EXCEPTION 'Ground-starship final receipt fails recomputation';
 END IF;
 RETURN NULL;
END;
$$;
CREATE CONSTRAINT TRIGGER cmd_ground_starship_final_audit
AFTER INSERT ON cmd_ground_starship_volley_final_receipt
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION cmd_validate_ground_starship_final();
