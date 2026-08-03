CREATE FUNCTION cmd_guard_ground_starship_volley_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE'
    OR OLD.volley_status<>'awaiting_primary'
    OR NEW.volley_status<>'finalized'
    OR ROW(NEW.command_id,NEW.target_ship_id,NEW.campaign_id,
           NEW.campaign_day_number,NEW.campaign_second_of_day,
           NEW.target_range_code,NEW.attack_modifier,
           NEW.successful_attack_count)
       IS DISTINCT FROM
       ROW(OLD.command_id,OLD.target_ship_id,OLD.campaign_id,
           OLD.campaign_day_number,OLD.campaign_second_of_day,
           OLD.target_range_code,OLD.attack_modifier,
           OLD.successful_attack_count) THEN
   RAISE EXCEPTION 'Ground-starship volley history is immutable';
 END IF;
 RETURN NEW;
END;
$$;
CREATE TRIGGER cmd_ground_starship_volley_guard
BEFORE UPDATE OR DELETE ON cmd_ground_starship_volley
FOR EACH ROW EXECUTE FUNCTION cmd_guard_ground_starship_volley_mutation();

CREATE OR REPLACE FUNCTION cmd_validate_ground_starship_volley()
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
    OR draw_count<>attack_count*2
    OR EXISTS (
      SELECT 1
        FROM cmd_ground_starship_volley_attack attack
        LEFT JOIN cmd_random_draw first_draw
          ON first_draw.command_id=attack.command_id
         AND first_draw.draw_group='attack'
         AND first_draw.draw_order=attack.attack_order*2-1
        LEFT JOIN cmd_random_draw second_draw
          ON second_draw.command_id=attack.command_id
         AND second_draw.draw_group='attack'
         AND second_draw.draw_order=attack.attack_order*2
       WHERE attack.command_id=NEW.command_id
         AND (first_draw.result IS DISTINCT FROM attack.attack_die_one
              OR second_draw.result IS DISTINCT FROM attack.attack_die_two))
    OR EXISTS (
      SELECT 1
        FROM gf_ground_weapon_battery battery
        JOIN (
          SELECT ground_weapon_battery_id,min(ammunition_after) AS final_ammo
            FROM cmd_ground_starship_volley_attack
           WHERE command_id=NEW.command_id
             AND ammunition_after IS NOT NULL
           GROUP BY ground_weapon_battery_id
        ) audit USING (ground_weapon_battery_id)
       WHERE battery.ammunition_remaining<>audit.final_ammo)
    OR EXISTS (
      SELECT 1
        FROM (
          SELECT attack.*,
                 lag(ammunition_after) OVER (
                   PARTITION BY ground_weapon_battery_id
                   ORDER BY weapon_unit_order) AS prior_after
            FROM cmd_ground_starship_volley_attack attack
           WHERE command_id=NEW.command_id
        ) chain
       WHERE chain.weapon_unit_order>1
         AND chain.ammunition_before IS DISTINCT FROM chain.prior_after)
 THEN
   RAISE EXCEPTION 'Ground-starship volley attack audit is incomplete';
 END IF;
 RETURN NULL;
END;
$$;

CREATE OR REPLACE FUNCTION cmd_validate_ground_starship_final()
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
DECLARE damage_matches boolean;
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
 SELECT CASE WHEN NEW.ship_damage_id IS NULL THEN NEW.hull_damage=0
             ELSE EXISTS (
               SELECT 1 FROM ship_damage damage
               JOIN cmd_ground_starship_volley volley
                 ON volley.command_id=NEW.volley_command_id
              WHERE damage.ship_damage_id=NEW.ship_damage_id
                AND damage.ship_id=volley.target_ship_id
                AND damage.campaign_id=volley.campaign_id
                AND damage.target_kind='hull'
                AND damage.damage_points=NEW.hull_damage
                AND damage.source_command_id=NEW.command_id)
        END INTO damage_matches;
 IF NOT primary_hit
    OR NEW.primary_damage_dice<>expected_primary
    OR NEW.additional_successful_damage_dice<>expected_additional
    OR die_count<>NEW.combined_damage_dice
    OR draw_count<>die_count OR draw_total<>die_total
    OR die_total<>NEW.personal_scale_damage
    OR ship_hull<>NEW.hull_after
    OR ship_version<>NEW.ship_version_after
    OR NOT damage_matches THEN
   RAISE EXCEPTION 'Ground-starship final receipt fails recomputation';
 END IF;
 RETURN NULL;
END;
$$;
