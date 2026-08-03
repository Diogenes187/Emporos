CREATE TABLE senc_damage_location_group_roll(
 mount_attack_declaration_id bigint NOT NULL REFERENCES senc_mount_damage_final_receipt(mount_attack_declaration_id),
 group_order smallint NOT NULL CHECK(group_order>0),hit_multiplicity smallint NOT NULL CHECK(hit_multiplicity BETWEEN 1 AND 3),
 first_die smallint NOT NULL CHECK(first_die BETWEEN 1 AND 6),second_die smallint NOT NULL CHECK(second_die BETWEEN 1 AND 6),
 roll_total smallint NOT NULL CHECK(roll_total=first_die+second_die),recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY(mount_attack_declaration_id,group_order)
);
CREATE TABLE senc_damage_location_roll_set_receipt(
 mount_attack_declaration_id bigint PRIMARY KEY REFERENCES senc_mount_damage_final_receipt(mount_attack_declaration_id),
 single_groups smallint NOT NULL CHECK(single_groups>=0),double_groups smallint NOT NULL CHECK(double_groups>=0),
 triple_groups smallint NOT NULL CHECK(triple_groups>=0),total_groups smallint NOT NULL CHECK(total_groups=single_groups+double_groups+triple_groups),
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE FUNCTION senc_validate_damage_location_group_roll() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE final senc_mount_damage_final_receipt%ROWTYPE; existing integer;
BEGIN
 SELECT * INTO STRICT final FROM senc_mount_damage_final_receipt WHERE mount_attack_declaration_id=NEW.mount_attack_declaration_id FOR UPDATE;
 IF final.damage_status<>'queued' OR EXISTS(SELECT 1 FROM senc_damage_location_roll_set_receipt WHERE mount_attack_declaration_id=NEW.mount_attack_declaration_id) THEN
  RAISE EXCEPTION 'Damage location groups require queued, unfinalized mount damage' USING ERRCODE='23514'; END IF;
 SELECT count(*) INTO existing FROM senc_damage_location_group_roll WHERE mount_attack_declaration_id=NEW.mount_attack_declaration_id AND hit_multiplicity=NEW.hit_multiplicity;
 IF existing >= (CASE NEW.hit_multiplicity WHEN 1 THEN final.single_hit_groups WHEN 2 THEN final.double_hit_groups ELSE final.triple_hit_groups END)
  OR NEW.group_order<>(SELECT count(*)+1 FROM senc_damage_location_group_roll WHERE mount_attack_declaration_id=NEW.mount_attack_declaration_id) THEN
  RAISE EXCEPTION 'Damage location group exceeds its hit multiplicity count or sequence' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER senc_damage_location_group_roll_valid BEFORE INSERT ON senc_damage_location_group_roll FOR EACH ROW EXECUTE FUNCTION senc_validate_damage_location_group_roll();
CREATE FUNCTION senc_validate_damage_location_roll_set() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE final senc_mount_damage_final_receipt%ROWTYPE; singles integer; doubles integer; triples integer;
BEGIN
 SELECT * INTO STRICT final FROM senc_mount_damage_final_receipt WHERE mount_attack_declaration_id=NEW.mount_attack_declaration_id FOR UPDATE;
 SELECT count(*) FILTER(WHERE hit_multiplicity=1),count(*) FILTER(WHERE hit_multiplicity=2),count(*) FILTER(WHERE hit_multiplicity=3)
 INTO singles,doubles,triples FROM senc_damage_location_group_roll WHERE mount_attack_declaration_id=NEW.mount_attack_declaration_id;
 IF singles<>final.single_hit_groups OR doubles<>final.double_hit_groups OR triples<>final.triple_hit_groups
  OR NEW.single_groups<>singles OR NEW.double_groups<>doubles OR NEW.triple_groups<>triples THEN
  RAISE EXCEPTION 'Damage location roll set is incomplete or mismatches its damage-band groups' USING ERRCODE='23514'; END IF; RETURN NEW;
END $$;
CREATE TRIGGER senc_damage_location_roll_set_valid BEFORE INSERT ON senc_damage_location_roll_set_receipt FOR EACH ROW EXECUTE FUNCTION senc_validate_damage_location_roll_set();
CREATE FUNCTION senc_reject_damage_location_roll_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Damage location rolls and set receipts are immutable'; END $$;
CREATE TRIGGER senc_damage_location_group_roll_immutable BEFORE UPDATE OR DELETE ON senc_damage_location_group_roll FOR EACH ROW EXECUTE FUNCTION senc_reject_damage_location_roll_mutation();
CREATE TRIGGER senc_damage_location_roll_set_immutable BEFORE UPDATE OR DELETE ON senc_damage_location_roll_set_receipt FOR EACH ROW EXECUTE FUNCTION senc_reject_damage_location_roll_mutation();
