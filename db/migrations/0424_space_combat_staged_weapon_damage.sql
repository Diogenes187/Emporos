WITH p AS (SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine')
INSERT INTO rule_rule(content_package_id,rule_code,name,rule_category,rule_status,description)
SELECT content_package_id,'combat.space.damage-grouping','Space Combat Damage Grouping','combat','approved',
 'Per-weapon damage and armor resolution followed by one mount-attack screen reduction.' FROM p;
CREATE TABLE rule_space_combat_damage_grouping(
 rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),weapon_damage_rolled_separately boolean NOT NULL,
 armor_applied_per_weapon boolean NOT NULL,fire_sand_applied_per_beam boolean NOT NULL,
 screen_applied_once_per_mount_attack boolean NOT NULL,post_armor_damage_combined_before_screen boolean NOT NULL
);
INSERT INTO rule_space_combat_damage_grouping SELECT rule_id,true,true,true,true,true FROM rule_rule WHERE rule_code='combat.space.damage-grouping';
INSERT INTO rule_interpretation(rule_id,interpretation_type,decision_register_entry,rationale)
SELECT rule_id,'agreed_interpretation','CE-SC-007',
 'Raymond approved separate weapon damage and armor, separate Fire Sand per beam, then one Trigger Screens reduction against combined post-armor mount-attack damage.'
FROM rule_rule WHERE rule_code='combat.space.damage-grouping';
INSERT INTO src_record_provenance(rule_id,content_package_id,source_locator_id,provenance_class,is_primary_citation)
SELECT r.rule_id,r.content_package_id,l.source_locator_id,CASE w.work_code WHEN 'cepheus-engine.ogn' THEN 'direct' ELSE 'corroborating' END,w.work_code='cepheus-engine.ogn'
FROM rule_rule r CROSS JOIN src_locator l JOIN src_work w USING(source_work_id)
WHERE r.rule_code='combat.space.damage-grouping' AND l.heading_path='Space Combat > Damage > Space Combat Damage'
 AND w.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1');

CREATE TABLE senc_weapon_damage_attempt(
 mount_weapon_attack_check_id bigint PRIMARY KEY REFERENCES senc_mount_weapon_attack_check(mount_weapon_attack_check_id),
 target_ship_id bigint NOT NULL,campaign_id bigint NOT NULL,damage_dice_count smallint NOT NULL CHECK(damage_dice_count>0),
 damage_die_sides smallint NOT NULL CHECK(damage_die_sides>1),damage_modifier smallint NOT NULL,
 armor_snapshot smallint NOT NULL CHECK(armor_snapshot>=0),ignores_armor boolean NOT NULL,
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),FOREIGN KEY(target_ship_id,campaign_id) REFERENCES ship_ship(ship_id,campaign_id)
);
CREATE TABLE senc_weapon_damage_die(
 mount_weapon_attack_check_id bigint NOT NULL REFERENCES senc_weapon_damage_attempt(mount_weapon_attack_check_id),
 die_order smallint NOT NULL CHECK(die_order>0),result smallint NOT NULL CHECK(result>0),PRIMARY KEY(mount_weapon_attack_check_id,die_order)
);
CREATE TABLE senc_weapon_damage_final_receipt(
 mount_weapon_attack_check_id bigint PRIMARY KEY REFERENCES senc_weapon_damage_attempt(mount_weapon_attack_check_id),
 rolled_damage smallint NOT NULL CHECK(rolled_damage>0),fire_sand_reduction smallint NOT NULL DEFAULT 0 CHECK(fire_sand_reduction>=0),
 post_armor_damage smallint NOT NULL CHECK(post_armor_damage>=0),recorded_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE senc_mount_damage_final_receipt(
 mount_attack_declaration_id bigint PRIMARY KEY REFERENCES senc_mount_attack_declaration(mount_attack_declaration_id),
 post_armor_damage_total smallint NOT NULL CHECK(post_armor_damage_total>=0),screen_reduction smallint NOT NULL DEFAULT 0 CHECK(screen_reduction>=0),
 net_damage smallint NOT NULL CHECK(net_damage>=0),single_hit_groups smallint NOT NULL CHECK(single_hit_groups>=0),
 double_hit_groups smallint NOT NULL CHECK(double_hit_groups>=0),triple_hit_groups smallint NOT NULL CHECK(triple_hit_groups>=0),
 damage_status text NOT NULL DEFAULT 'queued' CHECK(damage_status IN('queued','applied')),
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),CHECK(net_damage=greatest(0,post_armor_damage_total-screen_reduction))
);
CREATE FUNCTION senc_validate_weapon_damage_attempt() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE c record; weapon record; ship_row record; armor integer;
BEGIN
 SELECT check_row.hit,check_row.weapon_rule_id,declaration.target_vessel_id,declaration.campaign_id INTO c
 FROM senc_mount_weapon_attack_check check_row JOIN senc_mount_attack_declaration declaration USING(mount_attack_declaration_id)
 WHERE check_row.mount_weapon_attack_check_id=NEW.mount_weapon_attack_check_id;
 SELECT damage_dice_count,damage_die_sides,damage_modifier,ignores_armor INTO weapon FROM ship_weapon_definition WHERE weapon_rule_id=c.weapon_rule_id;
 SELECT vessel.ship_id,ship.ship_class_rule_id INTO ship_row FROM senc_vessel vessel JOIN ship_ship ship USING(ship_id) WHERE vessel.senc_vessel_id=c.target_vessel_id;
 SELECT coalesce((SELECT armor_value FROM ship_class_published_armor WHERE ship_class_rule_id=ship_row.ship_class_rule_id),
  (SELECT hull.armor_increments*design.protection_per_increment FROM ship_class_design_hull hull JOIN rule_ship_armor_design design USING(armor_code) WHERE hull.ship_class_rule_id=ship_row.ship_class_rule_id),0) INTO armor;
 IF NOT c.hit OR weapon.damage_dice_count IS NULL OR NEW.target_ship_id<>ship_row.ship_id OR NEW.campaign_id<>c.campaign_id
  OR NEW.damage_dice_count<>weapon.damage_dice_count OR NEW.damage_die_sides<>weapon.damage_die_sides OR NEW.damage_modifier<>weapon.damage_modifier
  OR NEW.armor_snapshot<>armor OR NEW.ignores_armor<>weapon.ignores_armor THEN
  RAISE EXCEPTION 'Weapon damage attempt does not match successful check, weapon profile, target, and armor snapshot' USING ERRCODE='23514';
 END IF; RETURN NEW;
END $$;
CREATE TRIGGER senc_weapon_damage_attempt_valid BEFORE INSERT ON senc_weapon_damage_attempt FOR EACH ROW EXECUTE FUNCTION senc_validate_weapon_damage_attempt();
CREATE FUNCTION senc_guard_weapon_damage_die() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE a senc_weapon_damage_attempt%ROWTYPE;
BEGIN SELECT * INTO STRICT a FROM senc_weapon_damage_attempt WHERE mount_weapon_attack_check_id=NEW.mount_weapon_attack_check_id FOR UPDATE;
 IF EXISTS(SELECT 1 FROM senc_weapon_damage_final_receipt WHERE mount_weapon_attack_check_id=NEW.mount_weapon_attack_check_id)
  OR NEW.die_order>a.damage_dice_count OR NEW.result>a.damage_die_sides THEN RAISE EXCEPTION 'Weapon damage die exceeds unfinalized weapon profile' USING ERRCODE='23514'; END IF; RETURN NEW; END $$;
CREATE TRIGGER senc_weapon_damage_die_valid BEFORE INSERT ON senc_weapon_damage_die FOR EACH ROW EXECUTE FUNCTION senc_guard_weapon_damage_die();
CREATE FUNCTION senc_validate_weapon_damage_final() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE a senc_weapon_damage_attempt%ROWTYPE; n integer; total integer;
BEGIN SELECT * INTO STRICT a FROM senc_weapon_damage_attempt WHERE mount_weapon_attack_check_id=NEW.mount_weapon_attack_check_id FOR UPDATE;
 SELECT count(*),coalesce(sum(result),0) INTO n,total FROM senc_weapon_damage_die WHERE mount_weapon_attack_check_id=NEW.mount_weapon_attack_check_id;
 IF n<>a.damage_dice_count OR NEW.rolled_damage<>total+a.damage_modifier OR NEW.fire_sand_reduction<>0
  OR NEW.post_armor_damage<>greatest(0,NEW.rolled_damage-NEW.fire_sand_reduction-CASE WHEN a.ignores_armor THEN 0 ELSE a.armor_snapshot END) THEN
  RAISE EXCEPTION 'Weapon damage final receipt fails dice, armor, or reduction recomputation' USING ERRCODE='23514'; END IF; RETURN NEW; END $$;
CREATE TRIGGER senc_weapon_damage_final_valid BEFORE INSERT ON senc_weapon_damage_final_receipt FOR EACH ROW EXECUTE FUNCTION senc_validate_weapon_damage_final();
CREATE FUNCTION senc_validate_mount_damage_final() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE expected_count integer; actual_count integer; total integer; singles integer; doubles integer; triples integer; excess integer;
BEGIN
 SELECT count(*) INTO expected_count FROM senc_mount_weapon_attack_check c JOIN ship_weapon_definition w USING(weapon_rule_id)
 WHERE c.mount_attack_declaration_id=NEW.mount_attack_declaration_id AND c.hit AND w.damage_dice_count IS NOT NULL;
 SELECT count(*),coalesce(sum(f.post_armor_damage),0) INTO actual_count,total FROM senc_mount_weapon_attack_check c
 JOIN senc_weapon_damage_final_receipt f USING(mount_weapon_attack_check_id) WHERE c.mount_attack_declaration_id=NEW.mount_attack_declaration_id;
 IF NEW.net_damage<=44 THEN SELECT single_hit_groups,double_hit_groups,triple_hit_groups INTO singles,doubles,triples FROM rule_space_combat_damage_band WHERE damage_range @> NEW.net_damage;
 ELSE excess:=NEW.net_damage-44; singles:=floor(excess/3); doubles:=floor(excess/6); triples:=2; END IF;
 IF expected_count<>actual_count OR total<>NEW.post_armor_damage_total OR NEW.screen_reduction<>0
  OR NEW.single_hit_groups<>singles OR NEW.double_hit_groups<>doubles OR NEW.triple_hit_groups<>triples THEN
  RAISE EXCEPTION 'Mount damage final receipt fails complete weapon aggregation or damage-band recomputation' USING ERRCODE='23514'; END IF; RETURN NEW; END $$;
CREATE TRIGGER senc_mount_damage_final_valid BEFORE INSERT ON senc_mount_damage_final_receipt FOR EACH ROW EXECUTE FUNCTION senc_validate_mount_damage_final();
CREATE FUNCTION senc_reject_staged_damage_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Staged weapon damage receipts and dice are immutable'; END $$;
CREATE TRIGGER senc_weapon_damage_attempt_immutable BEFORE UPDATE OR DELETE ON senc_weapon_damage_attempt FOR EACH ROW EXECUTE FUNCTION senc_reject_staged_damage_mutation();
CREATE TRIGGER senc_weapon_damage_die_immutable BEFORE UPDATE OR DELETE ON senc_weapon_damage_die FOR EACH ROW EXECUTE FUNCTION senc_reject_staged_damage_mutation();
CREATE TRIGGER senc_weapon_damage_final_immutable BEFORE UPDATE OR DELETE ON senc_weapon_damage_final_receipt FOR EACH ROW EXECUTE FUNCTION senc_reject_staged_damage_mutation();
CREATE TRIGGER senc_mount_damage_final_immutable BEFORE UPDATE OR DELETE ON senc_mount_damage_final_receipt FOR EACH ROW EXECUTE FUNCTION senc_reject_staged_damage_mutation();
