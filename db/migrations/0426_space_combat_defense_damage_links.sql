CREATE TABLE senc_fire_sand_weapon_reduction(
 fire_sand_attempt_receipt_id bigint NOT NULL,beam_order smallint NOT NULL,
 mount_weapon_attack_check_id bigint NOT NULL UNIQUE REFERENCES senc_mount_weapon_attack_check(mount_weapon_attack_check_id),
 reduction smallint NOT NULL CHECK(reduction BETWEEN 1 AND 6),
 PRIMARY KEY(fire_sand_attempt_receipt_id,beam_order),
 FOREIGN KEY(fire_sand_attempt_receipt_id,beam_order) REFERENCES senc_fire_sand_reduction_die(fire_sand_attempt_receipt_id,beam_order)
);
CREATE TABLE senc_screen_mount_reduction(
 screen_attempt_receipt_id bigint PRIMARY KEY REFERENCES senc_screen_final_receipt(screen_attempt_receipt_id),
 mount_attack_declaration_id bigint NOT NULL UNIQUE REFERENCES senc_mount_attack_declaration(mount_attack_declaration_id),
 reduction smallint NOT NULL CHECK(reduction>=2)
);
CREATE FUNCTION senc_validate_fire_sand_weapon_reduction() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE die_result integer; trigger_action bigint; declaration_action bigint; kind text; hit_value boolean;
BEGIN
 SELECT result INTO die_result FROM senc_fire_sand_reduction_die WHERE fire_sand_attempt_receipt_id=NEW.fire_sand_attempt_receipt_id AND beam_order=NEW.beam_order;
 SELECT reaction.triggering_action_id INTO trigger_action FROM senc_fire_sand_attempt_receipt attempt JOIN senc_reaction reaction USING(reaction_id)
  WHERE attempt.fire_sand_attempt_receipt_id=NEW.fire_sand_attempt_receipt_id;
 SELECT declaration.action_id,weapon.weapon_kind,check_row.hit INTO declaration_action,kind,hit_value
 FROM senc_mount_weapon_attack_check check_row JOIN senc_mount_attack_declaration declaration USING(mount_attack_declaration_id)
 JOIN ship_weapon_definition weapon USING(weapon_rule_id) WHERE check_row.mount_weapon_attack_check_id=NEW.mount_weapon_attack_check_id;
 IF die_result<>NEW.reduction OR trigger_action<>declaration_action OR kind IN('missile','sandcaster') OR NOT hit_value THEN
  RAISE EXCEPTION 'Fire Sand reduction must map one reaction die to one successful beam in its triggering mount attack' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER senc_fire_sand_weapon_reduction_valid BEFORE INSERT ON senc_fire_sand_weapon_reduction FOR EACH ROW EXECUTE FUNCTION senc_validate_fire_sand_weapon_reduction();
CREATE FUNCTION senc_validate_screen_mount_reduction() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE final_value integer; incoming text; trigger_action bigint; declaration_action bigint; compatible boolean;
BEGIN
 SELECT final.total_damage_reduction,attempt.incoming_weapon_kind,reaction.triggering_action_id
 INTO final_value,incoming,trigger_action FROM senc_screen_final_receipt final JOIN senc_screen_attempt_receipt attempt USING(screen_attempt_receipt_id)
 JOIN senc_reaction reaction USING(reaction_id) WHERE final.screen_attempt_receipt_id=NEW.screen_attempt_receipt_id;
 SELECT action_id INTO declaration_action FROM senc_mount_attack_declaration WHERE mount_attack_declaration_id=NEW.mount_attack_declaration_id;
 SELECT EXISTS(SELECT 1 FROM senc_mount_weapon_attack_check check_row JOIN ship_weapon_definition weapon USING(weapon_rule_id)
  WHERE check_row.mount_attack_declaration_id=NEW.mount_attack_declaration_id AND check_row.hit
   AND ((incoming='meson' AND weapon.weapon_kind='meson') OR (incoming='fusion' AND weapon.weapon_kind='fusion'))) INTO compatible;
 IF final_value<>NEW.reduction OR trigger_action<>declaration_action OR NOT compatible THEN
  RAISE EXCEPTION 'Screen reduction must map its final receipt to the compatible triggering mount attack' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER senc_screen_mount_reduction_valid BEFORE INSERT ON senc_screen_mount_reduction FOR EACH ROW EXECUTE FUNCTION senc_validate_screen_mount_reduction();

CREATE OR REPLACE FUNCTION senc_validate_weapon_damage_final() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE a senc_weapon_damage_attempt%ROWTYPE; n integer; total integer; sand integer;
BEGIN SELECT * INTO STRICT a FROM senc_weapon_damage_attempt WHERE mount_weapon_attack_check_id=NEW.mount_weapon_attack_check_id FOR UPDATE;
 SELECT count(*),coalesce(sum(result),0) INTO n,total FROM senc_weapon_damage_die WHERE mount_weapon_attack_check_id=NEW.mount_weapon_attack_check_id;
 SELECT coalesce((SELECT reduction FROM senc_fire_sand_weapon_reduction WHERE mount_weapon_attack_check_id=NEW.mount_weapon_attack_check_id),0) INTO sand;
 IF n<>a.damage_dice_count OR NEW.rolled_damage<>total+a.damage_modifier OR NEW.fire_sand_reduction<>sand
  OR NEW.post_armor_damage<>greatest(0,NEW.rolled_damage-sand-CASE WHEN a.ignores_armor THEN 0 ELSE a.armor_snapshot END) THEN
  RAISE EXCEPTION 'Weapon damage final receipt fails dice, armor, or Fire Sand recomputation' USING ERRCODE='23514'; END IF; RETURN NEW; END $$;

CREATE OR REPLACE FUNCTION senc_validate_mount_damage_final() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE expected_count integer; actual_count integer; total integer; screen integer; singles integer; doubles integer; triples integer; excess integer;
BEGIN
 SELECT count(*) INTO expected_count FROM senc_mount_weapon_attack_check c JOIN ship_weapon_definition w USING(weapon_rule_id)
 WHERE c.mount_attack_declaration_id=NEW.mount_attack_declaration_id AND c.hit AND w.damage_dice_count IS NOT NULL;
 SELECT count(*),coalesce(sum(f.post_armor_damage),0) INTO actual_count,total FROM senc_mount_weapon_attack_check c
 JOIN senc_weapon_damage_final_receipt f USING(mount_weapon_attack_check_id) WHERE c.mount_attack_declaration_id=NEW.mount_attack_declaration_id;
 SELECT coalesce((SELECT reduction FROM senc_screen_mount_reduction WHERE mount_attack_declaration_id=NEW.mount_attack_declaration_id),0) INTO screen;
 IF NEW.net_damage<=44 THEN SELECT single_hit_groups,double_hit_groups,triple_hit_groups INTO singles,doubles,triples
  FROM rule_space_combat_damage_band WHERE damage_range @> NEW.net_damage::integer;
 ELSE excess:=NEW.net_damage-44; singles:=floor(excess/3); doubles:=floor(excess/6); triples:=2; END IF;
 IF expected_count<>actual_count OR total<>NEW.post_armor_damage_total OR NEW.screen_reduction<>screen
  OR NEW.single_hit_groups<>singles OR NEW.double_hit_groups<>doubles OR NEW.triple_hit_groups<>triples THEN
  RAISE EXCEPTION 'Mount damage final receipt fails complete weapon, screen, or damage-band recomputation' USING ERRCODE='23514'; END IF; RETURN NEW; END $$;
CREATE FUNCTION senc_reject_defense_damage_link_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Defense damage links are immutable'; END $$;
CREATE TRIGGER senc_fire_sand_weapon_reduction_immutable BEFORE UPDATE OR DELETE ON senc_fire_sand_weapon_reduction FOR EACH ROW EXECUTE FUNCTION senc_reject_defense_damage_link_mutation();
CREATE TRIGGER senc_screen_mount_reduction_immutable BEFORE UPDATE OR DELETE ON senc_screen_mount_reduction FOR EACH ROW EXECUTE FUNCTION senc_reject_defense_damage_link_mutation();
