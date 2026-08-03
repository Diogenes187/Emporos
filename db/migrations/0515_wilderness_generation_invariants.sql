CREATE OR REPLACE FUNCTION enc_validate_animal_generation_receipt() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE d camp_animal_definition%ROWTYPE;t rule_animal_terrain%ROWTYPE;m rule_animal_terrain_movement%ROWTYPE;g rule_animal_subtype_generation%ROWTYPE;
 size_row rule_animal_size_band%ROWTYPE;num_row rule_animal_number_appearing%ROWTYPE;armor_row rule_animal_armor_band%ROWTYPE;damage_row rule_animal_damage_band%ROWTYPE;
 expected_subtype bigint;expected_weapon text;skill_sum integer;bad_weapons integer;expected_weapon_count integer;
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
 WITH expected AS(SELECT split_part(x,'+',1) code,coalesce(nullif(split_part(x,'+',2),''),'0')::smallint bonus FROM unnest(string_to_array(expected_weapon,',')) x
   UNION SELECT 'teeth',0 WHERE d.animal_type='scavenger'), actual AS(SELECT weapon_code,source_damage_bonus FROM camp_animal_definition_weapon WHERE animal_definition_id=d.animal_definition_id)
 SELECT (SELECT count(*) FROM expected),(SELECT count(*) FROM((SELECT * FROM expected EXCEPT SELECT * FROM actual) UNION ALL(SELECT * FROM actual EXCEPT SELECT * FROM expected)) q) INTO expected_weapon_count,bad_weapons;
 IF NEW.campaign_id<>d.campaign_id OR d.movement_code<>m.movement_code OR NEW.subtype_adjusted_total<>NEW.subtype_roll+t.subtype_modifier OR expected_subtype<>d.subtype_rule_id
 OR NEW.size_adjusted_total<>NEW.size_roll+t.size_modifier+m.additional_size_modifier OR d.weight_kg<>size_row.weight_kg
 OR d.strength<>NEW.strength_roll_total+g.strength_modifier+(CASE WHEN NEW.killer_modifier_choice='strength' THEN g.choice_strength_or_dexterity_modifier ELSE 0 END)
 OR d.dexterity<>NEW.dexterity_roll_total+g.dexterity_modifier+(CASE WHEN NEW.killer_modifier_choice='dexterity' THEN g.choice_strength_or_dexterity_modifier ELSE 0 END)
 OR d.endurance<>NEW.endurance_roll_total+g.endurance_modifier OR d.instinct<>greatest(0,NEW.instinct_roll+g.instinct_modifier) OR d.pack<>greatest(0,NEW.pack_roll+g.pack_modifier)
 OR (g.choice_strength_or_dexterity_modifier>0)<>(NEW.killer_modifier_choice IS NOT NULL) OR d.number_appearing_dice<>num_row.dice_count OR d.number_appearing_sides<>num_row.die_sides
 OR NEW.allocated_skill_ranks<>skill_sum OR NEW.allocated_skill_ranks<>coalesce(NEW.skill_pool_roll,0)
 OR NEW.weapon_adjusted_total<>NEW.weapon_roll+(CASE d.animal_type WHEN 'carnivore' THEN 8 WHEN 'omnivore' THEN 4 WHEN 'herbivore' THEN -6 ELSE 0 END) OR bad_weapons<>0
 OR EXISTS(SELECT 1 FROM camp_animal_definition_weapon WHERE animal_definition_id=d.animal_definition_id AND damage_dice<>damage_row.damage_dice+source_damage_bonus)
 OR NEW.armor_adjusted_total<>NEW.armor_roll-7+NEW.size_adjusted_total+(CASE d.animal_type WHEN 'herbivore' THEN 4 WHEN 'scavenger' THEN 2 WHEN 'carnivore' THEN -2 ELSE 0 END)+(CASE WHEN d.movement_code='F' THEN -2 ELSE 0 END)
 OR d.armor_rating<>armor_row.armor_rating OR NEW.speed_multiplier<>greatest(g.minimum_speed_multiplier,NEW.speed_roll+g.speed_roll_modifier) OR d.speed_meters<>NEW.speed_multiplier*6
 THEN RAISE EXCEPTION 'Animal generation receipt does not reproduce definition' USING ERRCODE='23514';END IF;
 IF NOT EXISTS(SELECT 1 FROM camp_animal_definition_skill WHERE animal_definition_id=d.animal_definition_id AND skill_code='athletics') OR NOT EXISTS(SELECT 1 FROM camp_animal_definition_skill WHERE animal_definition_id=d.animal_definition_id AND skill_code='recon') OR NOT EXISTS(SELECT 1 FROM camp_animal_definition_skill WHERE animal_definition_id=d.animal_definition_id AND skill_code='survival') THEN RAISE EXCEPTION 'Animal lacks baseline skills' USING ERRCODE='23514';END IF;
 RETURN NEW;END $$;

CREATE FUNCTION enc_validate_wilderness_table_scope() RETURNS trigger LANGUAGE plpgsql AS $$DECLARE t camp_wilderness_encounter_table%ROWTYPE;d camp_animal_definition%ROWTYPE;w loc_world_profile%ROWTYPE;
BEGIN
 IF TG_TABLE_NAME='camp_wilderness_encounter_table' THEN IF NEW.world_profile_id IS NOT NULL THEN SELECT * INTO STRICT w FROM loc_world_profile WHERE world_profile_id=NEW.world_profile_id;IF w.campaign_id<>NEW.campaign_id THEN RAISE EXCEPTION 'Wilderness table crosses campaign scope' USING ERRCODE='23514';END IF;END IF;RETURN NEW;END IF;
 SELECT * INTO STRICT t FROM camp_wilderness_encounter_table WHERE wilderness_encounter_table_id=NEW.wilderness_encounter_table_id;
 IF NEW.animal_definition_id IS NOT NULL THEN SELECT * INTO STRICT d FROM camp_animal_definition WHERE animal_definition_id=NEW.animal_definition_id;IF d.campaign_id<>t.campaign_id OR d.terrain_code<>t.terrain_code THEN RAISE EXCEPTION 'Wilderness entry crosses campaign or terrain scope' USING ERRCODE='23514';END IF;END IF;RETURN NEW;
END $$;
CREATE TRIGGER camp_wilderness_encounter_table_scope BEFORE INSERT OR UPDATE ON camp_wilderness_encounter_table FOR EACH ROW EXECUTE FUNCTION enc_validate_wilderness_table_scope();
CREATE TRIGGER camp_wilderness_encounter_entry_scope BEFORE INSERT OR UPDATE ON camp_wilderness_encounter_entry FOR EACH ROW EXECUTE FUNCTION enc_validate_wilderness_table_scope();

CREATE OR REPLACE FUNCTION enc_validate_wilderness_table() RETURNS trigger LANGUAGE plpgsql AS $$DECLARE t camp_wilderness_encounter_table%ROWTYPE;expected_count integer;actual_count integer;bad_count integer;
BEGIN SELECT * INTO STRICT t FROM camp_wilderness_encounter_table WHERE wilderness_encounter_table_id=NEW.wilderness_encounter_table_id;expected_count:=CASE t.template_code WHEN '1d6' THEN 6 ELSE 11 END;
 SELECT count(*),count(*) FILTER(WHERE (template.result_kind='event')<>(entry.result_kind='event') OR(entry.result_kind='animal' AND subtype.animal_type<>template.result_kind)) INTO actual_count,bad_count
 FROM camp_wilderness_encounter_entry entry JOIN rule_wilderness_encounter_template template ON template.template_code=t.template_code AND template.roll_total=entry.roll_total
 LEFT JOIN camp_animal_definition animal ON animal.animal_definition_id=entry.animal_definition_id LEFT JOIN rule_animal_subtype subtype ON subtype.rule_id=animal.subtype_rule_id
 WHERE entry.wilderness_encounter_table_id=t.wilderness_encounter_table_id;
 IF NEW.campaign_id<>t.campaign_id OR NEW.entry_count<>expected_count OR actual_count<>expected_count OR bad_count<>0 THEN RAISE EXCEPTION 'Wilderness table is incomplete or violates its template' USING ERRCODE='23514';END IF;RETURN NEW;END $$;
