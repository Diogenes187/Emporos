CREATE OR REPLACE FUNCTION senc_validate_mount_attack_declaration() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE a record; mount record; actual_range text; actual_round integer; class_id bigint; global_instance smallint;
 damage_status text; sensor_status text;
BEGIN
 SELECT action.action_code,action.target_vessel_id,action.space_combat_round_id,turn.senc_vessel_id,turn.crew_assignment_id,
  assignment.ship_id,assignment.duty_status INTO a FROM senc_action action JOIN senc_crew_turn turn USING(crew_turn_id)
 JOIN ship_crew_assignment assignment USING(crew_assignment_id) WHERE action.space_combat_action_id=NEW.action_id;
 SELECT selected.mount_code,selected.mount_count,definition.mount_kind INTO mount FROM ship_class_weapon_mount selected
 JOIN rule_ship_weapon_mount definition USING(mount_code) WHERE selected.class_weapon_mount_id=NEW.class_weapon_mount_id AND selected.ship_class_rule_id=NEW.ship_class_rule_id;
 SELECT ship_class_rule_id INTO class_id FROM ship_ship WHERE ship_id=NEW.gunner_ship_id;
 SELECT range_band_code INTO actual_range FROM senc_vessel_range WHERE engagement_id=NEW.engagement_id
  AND first_vessel_id=least(NEW.attacker_vessel_id,NEW.target_vessel_id) AND second_vessel_id=greatest(NEW.attacker_vessel_id,NEW.target_vessel_id);
 SELECT round_number INTO actual_round FROM senc_round WHERE space_combat_round_id=NEW.space_combat_round_id;
 global_instance:=senc_mount_global_system_instance(NEW.ship_class_rule_id,NEW.class_weapon_mount_id,NEW.mount_instance);
 SELECT system_status INTO damage_status FROM senc_ship_system_damage_state
  WHERE ship_id=NEW.gunner_ship_id AND system_code=NEW.mount_kind AND system_instance=global_instance;
 SELECT system_status INTO sensor_status FROM senc_ship_system_damage_state
  WHERE ship_id=NEW.gunner_ship_id AND system_code='sensors' AND system_instance=1;
 IF a.action_code<>'attack' OR a.target_vessel_id<>NEW.target_vessel_id OR a.space_combat_round_id<>NEW.space_combat_round_id
  OR a.senc_vessel_id<>NEW.attacker_vessel_id OR a.crew_assignment_id<>NEW.gunner_assignment_id OR a.ship_id<>NEW.gunner_ship_id OR a.duty_status<>'active'
  OR class_id<>NEW.ship_class_rule_id OR mount.mount_code<>NEW.mount_code OR mount.mount_kind<>NEW.mount_kind OR NEW.mount_instance>mount.mount_count
  OR damage_status IN('disabled','destroyed') OR (sensor_status IN('disabled','destroyed') AND actual_range<>'adjacent')
  OR actual_range<>NEW.range_band_code OR actual_round<>NEW.round_number
  OR NOT EXISTS(SELECT 1 FROM senc_crew_role_assignment role WHERE role.engagement_id=NEW.engagement_id AND role.senc_vessel_id=NEW.attacker_vessel_id
   AND role.crew_assignment_id=NEW.gunner_assignment_id AND role.crew_role='gunner' AND role.ended_at IS NULL) THEN
  RAISE EXCEPTION 'Mount attack requires matching action, active Gunner, usable Sensors and mount, target, and current range' USING ERRCODE='23514';
 END IF; RETURN NEW;
END $$;
