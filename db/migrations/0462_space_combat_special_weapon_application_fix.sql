CREATE OR REPLACE FUNCTION senc_validate_mount_damage_final() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE expected_count integer; actual_count integer; total integer; singles integer; doubles integer; triples integer; excess integer;
BEGIN
 SELECT count(*) INTO expected_count FROM senc_mount_weapon_attack_check check_row
 JOIN ship_weapon_definition weapon USING(weapon_rule_id)
 WHERE check_row.mount_attack_declaration_id=NEW.mount_attack_declaration_id AND check_row.hit
  AND (weapon.damage_dice_count IS NOT NULL OR weapon.weapon_kind='sandcaster');
 SELECT count(*),coalesce(sum(source.post_armor_damage),0) INTO actual_count,total FROM (
  SELECT final.post_armor_damage FROM senc_mount_weapon_attack_check check_row
  JOIN senc_weapon_damage_final_receipt final USING(mount_weapon_attack_check_id)
  WHERE check_row.mount_attack_declaration_id=NEW.mount_attack_declaration_id
  UNION ALL
  SELECT sand.post_armor_damage FROM senc_mount_weapon_attack_check check_row
  JOIN senc_offensive_sand_damage_receipt sand USING(mount_weapon_attack_check_id)
  WHERE check_row.mount_attack_declaration_id=NEW.mount_attack_declaration_id
 ) source;
 IF NEW.net_damage<=44 THEN SELECT single_hit_groups,double_hit_groups,triple_hit_groups INTO singles,doubles,triples
  FROM rule_space_combat_damage_band WHERE damage_range @> NEW.net_damage::integer;
 ELSE excess:=NEW.net_damage-44; singles:=floor(excess/3); doubles:=floor(excess/6); triples:=2; END IF;
 IF expected_count<>actual_count OR total<>NEW.post_armor_damage_total OR NEW.screen_reduction<>0
  OR NEW.single_hit_groups<>singles OR NEW.double_hit_groups<>doubles OR NEW.triple_hit_groups<>triples THEN
  RAISE EXCEPTION 'Mount damage final receipt fails complete weapon aggregation or damage-band recomputation' USING ERRCODE='23514';
 END IF; RETURN NEW;
END $$;
