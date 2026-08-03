CREATE TABLE camp_animal_definition(
 animal_definition_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
 world_profile_id bigint REFERENCES loc_world_profile(world_profile_id),definition_code text NOT NULL,name text,
 terrain_code text NOT NULL REFERENCES rule_animal_terrain,animal_type text NOT NULL CHECK(animal_type IN('carnivore','herbivore','omnivore','scavenger')),
 subtype_rule_id bigint NOT NULL REFERENCES rule_animal_subtype,movement_code text NOT NULL CHECK(movement_code IN('A','F','S','W')),
 weight_kg integer NOT NULL CHECK(weight_kg>0),strength smallint NOT NULL CHECK(strength>0),dexterity smallint NOT NULL CHECK(dexterity>0),
 endurance smallint NOT NULL CHECK(endurance>0),intelligence smallint NOT NULL CHECK(intelligence IN(0,1)),instinct smallint NOT NULL CHECK(instinct>=0),pack smallint NOT NULL CHECK(pack>=0),
 number_appearing_dice smallint NOT NULL CHECK(number_appearing_dice>0),number_appearing_sides smallint NOT NULL CHECK(number_appearing_sides>0),
 armor_rating smallint NOT NULL CHECK(armor_rating BETWEEN 0 AND 7),speed_meters smallint NOT NULL CHECK(speed_meters>=0),description text,
 UNIQUE(campaign_id,definition_code),UNIQUE(animal_definition_id,campaign_id),UNIQUE(animal_definition_id,subtype_rule_id)
);
CREATE TABLE camp_animal_definition_skill(
 animal_definition_id bigint NOT NULL REFERENCES camp_animal_definition,skill_code text NOT NULL,skill_level smallint NOT NULL CHECK(skill_level>=0),
 allocation_kind text NOT NULL CHECK(allocation_kind IN('baseline','rolled','subtype')),PRIMARY KEY(animal_definition_id,skill_code)
);
CREATE TABLE camp_animal_definition_weapon(
 animal_definition_id bigint NOT NULL REFERENCES camp_animal_definition,weapon_code text NOT NULL REFERENCES rule_animal_weapon,
 damage_dice smallint NOT NULL CHECK(damage_dice>0),source_damage_bonus smallint NOT NULL DEFAULT 0,
 PRIMARY KEY(animal_definition_id,weapon_code)
);

CREATE TABLE cmd_animal_generation_receipt(
 animal_generation_receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,animal_definition_id bigint NOT NULL UNIQUE REFERENCES camp_animal_definition,
 campaign_id bigint NOT NULL,movement_roll smallint NOT NULL CHECK(movement_roll BETWEEN 1 AND 6),subtype_roll smallint NOT NULL CHECK(subtype_roll BETWEEN 2 AND 12),
 subtype_adjusted_total smallint NOT NULL,size_roll smallint NOT NULL CHECK(size_roll BETWEEN 2 AND 12),size_adjusted_total smallint NOT NULL,
 strength_roll_total smallint NOT NULL,dexterity_roll_total smallint NOT NULL,endurance_roll_total smallint NOT NULL,
 killer_modifier_choice text CHECK(killer_modifier_choice IN('strength','dexterity')),
 instinct_roll smallint NOT NULL CHECK(instinct_roll BETWEEN 2 AND 12),pack_roll smallint NOT NULL CHECK(pack_roll BETWEEN 2 AND 12),
 skill_pool_roll smallint CHECK(skill_pool_roll BETWEEN 1 AND 6),allocated_skill_ranks smallint NOT NULL CHECK(allocated_skill_ranks>=0),
 weapon_roll smallint NOT NULL CHECK(weapon_roll BETWEEN 2 AND 12),weapon_adjusted_total smallint NOT NULL,
 armor_roll smallint NOT NULL CHECK(armor_roll BETWEEN 2 AND 12),armor_adjusted_total smallint NOT NULL,
 speed_roll smallint NOT NULL CHECK(speed_roll BETWEEN 1 AND 6),speed_multiplier smallint NOT NULL CHECK(speed_multiplier>=0),
 source_command_id bigint REFERENCES cmd_command(command_id),generated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(animal_definition_id,campaign_id) REFERENCES camp_animal_definition(animal_definition_id,campaign_id)
);

ALTER TABLE actor_animal_profile ADD COLUMN animal_definition_id bigint REFERENCES camp_animal_definition(animal_definition_id);

CREATE FUNCTION enc_validate_animal_definition() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE s rule_animal_subtype%ROWTYPE;w loc_world_profile%ROWTYPE;
BEGIN
 SELECT * INTO STRICT s FROM rule_animal_subtype WHERE rule_id=NEW.subtype_rule_id;
 IF s.animal_type<>NEW.animal_type THEN RAISE EXCEPTION 'Animal subtype does not belong to animal type' USING ERRCODE='23514';END IF;
 IF NEW.world_profile_id IS NOT NULL THEN SELECT * INTO STRICT w FROM loc_world_profile WHERE world_profile_id=NEW.world_profile_id;IF w.campaign_id<>NEW.campaign_id THEN RAISE EXCEPTION 'Animal definition crosses campaign scope' USING ERRCODE='23514';END IF;END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER camp_animal_definition_valid BEFORE INSERT OR UPDATE ON camp_animal_definition FOR EACH ROW EXECUTE FUNCTION enc_validate_animal_definition();

CREATE FUNCTION enc_validate_animal_generation_receipt() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE d camp_animal_definition%ROWTYPE;t rule_animal_terrain%ROWTYPE;m rule_animal_terrain_movement%ROWTYPE;g rule_animal_subtype_generation%ROWTYPE;
        size_row rule_animal_size_band%ROWTYPE;num_row rule_animal_number_appearing%ROWTYPE;armor_row rule_animal_armor_band%ROWTYPE;damage_row rule_animal_damage_band%ROWTYPE;
        expected_subtype bigint;expected_weapon text;weapon_count integer;skill_sum integer;
BEGIN
 SELECT * INTO STRICT d FROM camp_animal_definition WHERE animal_definition_id=NEW.animal_definition_id;
 SELECT * INTO STRICT t FROM rule_animal_terrain WHERE terrain_code=d.terrain_code;
 SELECT * INTO STRICT m FROM rule_animal_terrain_movement WHERE terrain_code=d.terrain_code AND roll_result=NEW.movement_roll;
 SELECT * INTO STRICT g FROM rule_animal_subtype_generation WHERE subtype_rule_id=d.subtype_rule_id;
 SELECT subtype_rule_id INTO STRICT expected_subtype FROM rule_animal_subtype_band WHERE animal_type=d.animal_type AND NEW.subtype_adjusted_total BETWEEN minimum_total AND maximum_total;
 SELECT * INTO STRICT size_row FROM rule_animal_size_band WHERE NEW.size_adjusted_total BETWEEN minimum_total AND maximum_total;
 SELECT * INTO STRICT num_row FROM rule_animal_number_appearing WHERE d.pack BETWEEN minimum_pack AND maximum_pack;
 SELECT weapon_spec INTO STRICT expected_weapon FROM rule_animal_weapon_band WHERE NEW.weapon_adjusted_total BETWEEN minimum_total AND maximum_total;
 SELECT * INTO STRICT armor_row FROM rule_animal_armor_band WHERE NEW.armor_adjusted_total BETWEEN minimum_total AND maximum_total;
 SELECT * INTO STRICT damage_row FROM rule_animal_damage_band WHERE d.strength BETWEEN minimum_strength AND maximum_strength;
 SELECT coalesce(sum(skill_level) FILTER(WHERE allocation_kind='rolled'),0) INTO skill_sum FROM camp_animal_definition_skill WHERE animal_definition_id=d.animal_definition_id;
 SELECT count(*) INTO weapon_count FROM camp_animal_definition_weapon WHERE animal_definition_id=d.animal_definition_id;
 IF NEW.campaign_id<>d.campaign_id OR d.movement_code<>m.movement_code OR NEW.subtype_adjusted_total<>NEW.subtype_roll+t.subtype_modifier OR expected_subtype<>d.subtype_rule_id
    OR NEW.size_adjusted_total<>NEW.size_roll+t.size_modifier+m.additional_size_modifier OR d.weight_kg<>size_row.weight_kg
    OR d.strength<>NEW.strength_roll_total+g.strength_modifier+(CASE WHEN NEW.killer_modifier_choice='strength' THEN g.choice_strength_or_dexterity_modifier ELSE 0 END)
    OR d.dexterity<>NEW.dexterity_roll_total+g.dexterity_modifier+(CASE WHEN NEW.killer_modifier_choice='dexterity' THEN g.choice_strength_or_dexterity_modifier ELSE 0 END)
    OR d.endurance<>NEW.endurance_roll_total+g.endurance_modifier OR d.instinct<>greatest(0,NEW.instinct_roll+g.instinct_modifier) OR d.pack<>greatest(0,NEW.pack_roll+g.pack_modifier)
    OR (g.choice_strength_or_dexterity_modifier>0)<>(NEW.killer_modifier_choice IS NOT NULL)
    OR d.number_appearing_dice<>num_row.dice_count OR d.number_appearing_sides<>num_row.die_sides
    OR NEW.allocated_skill_ranks<>skill_sum OR NEW.allocated_skill_ranks<>coalesce(NEW.skill_pool_roll,0)
    OR NEW.weapon_adjusted_total<>NEW.weapon_roll+(CASE d.animal_type WHEN 'carnivore' THEN 8 WHEN 'omnivore' THEN 4 WHEN 'herbivore' THEN -6 ELSE 0 END)
    OR weapon_count=0 OR NEW.armor_adjusted_total<>NEW.armor_roll-7+NEW.size_adjusted_total+(CASE d.animal_type WHEN 'herbivore' THEN 4 WHEN 'scavenger' THEN 2 WHEN 'carnivore' THEN -2 ELSE 0 END)+(CASE WHEN d.movement_code='F' THEN -2 ELSE 0 END)
    OR d.armor_rating<>armor_row.armor_rating OR NEW.speed_multiplier<>greatest(g.minimum_speed_multiplier,NEW.speed_roll+g.speed_roll_modifier)
    OR d.speed_meters<>NEW.speed_multiplier*6 THEN RAISE EXCEPTION 'Animal generation receipt does not reproduce definition' USING ERRCODE='23514';END IF;
 IF NOT EXISTS(SELECT 1 FROM camp_animal_definition_skill WHERE animal_definition_id=d.animal_definition_id AND skill_code='athletics')
 OR NOT EXISTS(SELECT 1 FROM camp_animal_definition_skill WHERE animal_definition_id=d.animal_definition_id AND skill_code='recon')
 OR NOT EXISTS(SELECT 1 FROM camp_animal_definition_skill WHERE animal_definition_id=d.animal_definition_id AND skill_code='survival') THEN RAISE EXCEPTION 'Animal lacks baseline skills' USING ERRCODE='23514';END IF;
 IF d.animal_type='scavenger' AND NOT EXISTS(SELECT 1 FROM camp_animal_definition_weapon WHERE animal_definition_id=d.animal_definition_id AND weapon_code='teeth') THEN RAISE EXCEPTION 'Scavenger lacks automatic teeth' USING ERRCODE='23514';END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER cmd_animal_generation_receipt_valid BEFORE INSERT ON cmd_animal_generation_receipt FOR EACH ROW EXECUTE FUNCTION enc_validate_animal_generation_receipt();

CREATE FUNCTION enc_reject_wilderness_mutation() RETURNS trigger LANGUAGE plpgsql AS $$BEGIN RAISE EXCEPTION 'Wilderness generation records are immutable' USING ERRCODE='55000';END$$;
CREATE FUNCTION enc_reject_generated_animal_mutation() RETURNS trigger LANGUAGE plpgsql AS $$BEGIN IF EXISTS(SELECT 1 FROM cmd_animal_generation_receipt r WHERE r.animal_definition_id=OLD.animal_definition_id) THEN RAISE EXCEPTION 'Wilderness generation records are immutable' USING ERRCODE='55000';END IF;RETURN OLD;END$$;
CREATE TRIGGER cmd_animal_generation_receipt_immutable BEFORE UPDATE OR DELETE ON cmd_animal_generation_receipt FOR EACH ROW EXECUTE FUNCTION enc_reject_wilderness_mutation();
CREATE TRIGGER camp_generated_animal_immutable BEFORE UPDATE OR DELETE ON camp_animal_definition FOR EACH ROW EXECUTE FUNCTION enc_reject_generated_animal_mutation();
CREATE TRIGGER camp_generated_animal_skill_immutable BEFORE UPDATE OR DELETE ON camp_animal_definition_skill FOR EACH ROW EXECUTE FUNCTION enc_reject_generated_animal_mutation();
CREATE TRIGGER camp_generated_animal_weapon_immutable BEFORE UPDATE OR DELETE ON camp_animal_definition_weapon FOR EACH ROW EXECUTE FUNCTION enc_reject_generated_animal_mutation();

CREATE VIEW camp_generated_animal_summary AS
SELECT d.*,s.subtype_code,string_agg(DISTINCT sk.skill_code||'-'||sk.skill_level,', ' ORDER BY sk.skill_code||'-'||sk.skill_level) skills,
       string_agg(DISTINCT w.weapon_code||' ('||w.damage_dice||'D6)',', ' ORDER BY w.weapon_code||' ('||w.damage_dice||'D6)') weapons
FROM camp_animal_definition d JOIN rule_animal_subtype s ON s.rule_id=d.subtype_rule_id
LEFT JOIN camp_animal_definition_skill sk USING(animal_definition_id) LEFT JOIN camp_animal_definition_weapon w USING(animal_definition_id)
GROUP BY d.animal_definition_id,s.subtype_code;
