CREATE FUNCTION senc_mount_global_system_instance(
 p_ship_class_rule_id bigint,p_class_weapon_mount_id bigint,p_mount_instance smallint
) RETURNS smallint LANGUAGE sql STABLE AS $$
 SELECT (coalesce(sum(prior.mount_count),0)+p_mount_instance)::smallint
 FROM ship_class_weapon_mount selected
 JOIN rule_ship_weapon_mount selected_definition USING(mount_code)
 LEFT JOIN ship_class_weapon_mount prior
   ON prior.ship_class_rule_id=selected.ship_class_rule_id
  AND prior.class_weapon_mount_id<selected.class_weapon_mount_id
 LEFT JOIN rule_ship_weapon_mount prior_definition
   ON prior_definition.mount_code=prior.mount_code
  AND prior_definition.mount_kind=selected_definition.mount_kind
 WHERE selected.ship_class_rule_id=p_ship_class_rule_id
   AND selected.class_weapon_mount_id=p_class_weapon_mount_id
 GROUP BY selected.class_weapon_mount_id
$$;

CREATE FUNCTION senc_guard_damaged_system_action() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE ship_value bigint; bridge_status text; sensor_status text;
BEGIN
 SELECT vessel.ship_id INTO STRICT ship_value FROM senc_crew_turn turn
 JOIN senc_vessel vessel ON vessel.senc_vessel_id=turn.senc_vessel_id
 WHERE turn.crew_turn_id=NEW.crew_turn_id AND turn.space_combat_round_id=NEW.space_combat_round_id
  AND turn.engagement_id=NEW.engagement_id AND turn.campaign_id=NEW.campaign_id;
 SELECT system_status INTO bridge_status FROM senc_ship_system_damage_state
  WHERE ship_id=ship_value AND system_code='bridge' AND system_instance=1;
 SELECT system_status INTO sensor_status FROM senc_ship_system_damage_state
  WHERE ship_id=ship_value AND system_code='sensors' AND system_instance=1;
 IF bridge_status IN('disabled','destroyed') AND NEW.action_code IN(
  'adjust-speed','maintain-course','avoid-collision','break-pursuit','dock','dodge',
  'evasive-maneuvers','line-up-shot','pursuit','ram','range-check','calculate-jump',
  'electronic-warfare','intercept-comms','maintain-comms','sensor-targeting') THEN
  RAISE EXCEPTION 'Disabled or destroyed Bridge prevents Pilot, Sensor, and jump actions' USING ERRCODE='23514';
 END IF;
 IF sensor_status IN('disabled','destroyed') AND NEW.action_code IN(
  'electronic-warfare','intercept-comms','maintain-comms','sensor-targeting') THEN
  RAISE EXCEPTION 'Disabled or destroyed Sensors prevent sensor actions' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER senc_action_damaged_system_guard BEFORE INSERT ON senc_action
FOR EACH ROW EXECUTE FUNCTION senc_guard_damaged_system_action();

ALTER TABLE senc_sensor_targeting_receipt
 ADD COLUMN sensor_damage_modifier smallint NOT NULL DEFAULT 0
 CHECK(sensor_damage_modifier IN(-2,0));

CREATE OR REPLACE FUNCTION senc_validate_sensor_targeting_receipt() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE a record; t cmd_actor_task_receipt%ROWTYPE; actual_round integer; comms bigint; education bigint;
 target_electronics record; expected_sensor_dm smallint;
BEGIN
 SELECT action.action_code,action.target_vessel_id action_target,action.space_combat_round_id,turn.senc_vessel_id,
  turn.crew_assignment_id,assignment.ship_id,assignment.actor_id,assignment.duty_status INTO a
 FROM senc_action action JOIN senc_crew_turn turn USING(crew_turn_id) JOIN ship_crew_assignment assignment USING(crew_assignment_id)
 WHERE action.space_combat_action_id=NEW.action_id;
 SELECT * INTO STRICT t FROM cmd_actor_task_receipt WHERE command_id=NEW.task_command_id;
 SELECT rule_id INTO STRICT comms FROM rule_rule WHERE rule_code='skill.comms';
 SELECT rule_id INTO STRICT education FROM rule_rule WHERE rule_code='characteristic.education';
 SELECT round_number INTO actual_round FROM senc_round WHERE space_combat_round_id=NEW.space_combat_round_id;
 SELECT selected.electronics_code,suite.communications_dm INTO target_electronics
 FROM senc_vessel vessel JOIN ship_ship ship USING(ship_id) JOIN ship_class_electronics selected USING(ship_class_rule_id)
 JOIN rule_ship_electronics_suite suite USING(electronics_code) WHERE vessel.senc_vessel_id=NEW.target_vessel_id;
 SELECT coalesce(state.sensor_dm,0) INTO expected_sensor_dm FROM senc_vessel vessel
 LEFT JOIN senc_ship_system_damage_state state ON state.ship_id=vessel.ship_id AND state.system_code='sensors' AND state.system_instance=1
 WHERE vessel.senc_vessel_id=NEW.senc_vessel_id;
 IF a.action_code<>'sensor-targeting' OR a.action_target<>NEW.target_vessel_id OR a.space_combat_round_id<>NEW.space_combat_round_id
  OR a.senc_vessel_id<>NEW.senc_vessel_id OR a.crew_assignment_id<>NEW.operator_assignment_id OR a.ship_id<>NEW.operator_ship_id
  OR a.duty_status<>'active' OR NOT EXISTS(SELECT 1 FROM senc_crew_role_assignment role WHERE role.engagement_id=NEW.engagement_id
    AND role.senc_vessel_id=NEW.senc_vessel_id AND role.crew_assignment_id=NEW.operator_assignment_id
    AND role.crew_role='sensors_operator' AND role.ended_at IS NULL)
  OR t.actor_id<>a.actor_id OR t.skill_rule_id<>comms OR t.characteristic_rule_id<>education OR t.effect<>NEW.task_effect
  OR t.succeeded<>NEW.task_succeeded OR t.circumstance_modifier<>expected_sensor_dm OR NEW.sensor_damage_modifier<>expected_sensor_dm
  OR actual_round<>NEW.round_number OR target_electronics.electronics_code<>NEW.target_electronics_code
  OR target_electronics.communications_dm<>NEW.target_sensor_jamming_rating THEN
  RAISE EXCEPTION 'Sensor Targeting receipt does not match active Sensors, damage DM, target, Comms check, and jamming snapshot' USING ERRCODE='23514';
 END IF; RETURN NEW;
END $$;

ALTER TABLE senc_mount_weapon_attack_check
 ADD COLUMN system_damage_modifier smallint NOT NULL DEFAULT 0
 CHECK(system_damage_modifier BETWEEN -4 AND 0),
 DROP CONSTRAINT senc_mount_weapon_attack_check_check,
 ADD CONSTRAINT senc_mount_weapon_attack_check_total_modifier_check CHECK(
  total_circumstance_modifier=weapon_modifier+coordinate_crew_modifier+line_up_modifier+
  sensor_targeting_modifier+pursuit_modifier+evasive_modifier+dodge_modifier+
  computer_targeting_modifier+system_damage_modifier);

CREATE OR REPLACE FUNCTION senc_validate_mount_attack_declaration() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE a record; mount record; actual_range text; actual_round integer; class_id bigint; global_instance smallint; damage_status text;
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
 IF a.action_code<>'attack' OR a.target_vessel_id<>NEW.target_vessel_id OR a.space_combat_round_id<>NEW.space_combat_round_id
  OR a.senc_vessel_id<>NEW.attacker_vessel_id OR a.crew_assignment_id<>NEW.gunner_assignment_id OR a.ship_id<>NEW.gunner_ship_id OR a.duty_status<>'active'
  OR class_id<>NEW.ship_class_rule_id OR mount.mount_code<>NEW.mount_code OR mount.mount_kind<>NEW.mount_kind OR NEW.mount_instance>mount.mount_count
  OR damage_status IN('disabled','destroyed') OR actual_range<>NEW.range_band_code OR actual_round<>NEW.round_number
  OR NOT EXISTS(SELECT 1 FROM senc_crew_role_assignment role WHERE role.engagement_id=NEW.engagement_id AND role.senc_vessel_id=NEW.attacker_vessel_id
   AND role.crew_assignment_id=NEW.gunner_assignment_id AND role.crew_role='gunner' AND role.ended_at IS NULL) THEN
  RAISE EXCEPTION 'Mount attack requires matching action, active Gunner, operational mount instance, target, and current range' USING ERRCODE='23514';
 END IF; RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION senc_validate_mount_weapon_attack_check() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE d senc_mount_attack_declaration%ROWTYPE; t cmd_actor_task_receipt%ROWTYPE; actor bigint; expected_weapon bigint; profile text; expected_difficulty bigint;
 expected_skill bigint; weapon_dm integer; coord integer; line_dm integer; sensor_dm integer; pursuit_dm integer; evade_dm integer; dodge_dm integer;
 global_instance smallint; mount_damage integer; bridge_damage integer; system_damage integer;
BEGIN
 SELECT * INTO STRICT d FROM senc_mount_attack_declaration WHERE mount_attack_declaration_id=NEW.mount_attack_declaration_id FOR UPDATE;
 SELECT weapon_rule_id INTO expected_weapon FROM ship_class_mount_weapon WHERE class_weapon_mount_id=d.class_weapon_mount_id AND ship_class_rule_id=d.ship_class_rule_id AND weapon_slot=NEW.weapon_slot;
 SELECT weapon_profile_code INTO profile FROM rule_space_combat_weapon_profile WHERE weapon_rule_id=NEW.weapon_rule_id;
 SELECT difficulty_rule_id INTO expected_difficulty FROM rule_space_combat_attack_range WHERE weapon_profile_code=profile AND range_band_code=d.range_band_code AND available;
 SELECT rule_id INTO expected_skill FROM rule_rule WHERE rule_code=CASE d.mount_kind WHEN 'turret' THEN 'skill.turret-weapons' ELSE 'skill.bay-weapons' END;
 SELECT actor_id INTO actor FROM ship_crew_assignment WHERE crew_assignment_id=d.gunner_assignment_id;
 SELECT * INTO STRICT t FROM cmd_actor_task_receipt WHERE command_id=NEW.task_command_id;
 SELECT attack_modifier INTO weapon_dm FROM ship_weapon_definition WHERE weapon_rule_id=NEW.weapon_rule_id;
 SELECT coalesce((SELECT allocation.points FROM senc_coordinate_crew_allocation allocation JOIN senc_coordinate_crew_receipt receipt USING(coordinate_crew_receipt_id)
  WHERE allocation.coordinate_crew_allocation_id=NEW.coordinate_crew_allocation_id AND allocation.recipient_assignment_id=d.gunner_assignment_id
   AND receipt.space_combat_round_id=d.space_combat_round_id AND receipt.senc_vessel_id=d.attacker_vessel_id),0) INTO coord;
 SELECT coalesce((SELECT attack_bonus FROM senc_line_up_shot_receipt WHERE space_combat_round_id=d.space_combat_round_id AND senc_vessel_id=d.attacker_vessel_id),0) INTO line_dm;
 SELECT coalesce((SELECT attack_bonus FROM senc_sensor_targeting_receipt WHERE space_combat_round_id=d.space_combat_round_id AND senc_vessel_id=d.attacker_vessel_id AND target_vessel_id=d.target_vessel_id),0) INTO sensor_dm;
 SELECT coalesce((SELECT attack_modifier FROM senc_pursuit WHERE engagement_id=d.engagement_id AND pursuing_vessel_id=d.attacker_vessel_id AND target_vessel_id=d.target_vessel_id AND pursuit_status='active' AND last_maintained_round=d.round_number),0) INTO pursuit_dm;
 SELECT coalesce((SELECT attack_penalty FROM senc_evasive_maneuver_receipt WHERE space_combat_round_id=d.space_combat_round_id AND senc_vessel_id=d.target_vessel_id),0) INTO evade_dm;
 SELECT coalesce((SELECT sum(receipt.attack_modifier) FROM senc_dodge_receipt receipt JOIN senc_reaction reaction USING(reaction_id) WHERE reaction.triggering_action_id=d.action_id),0) INTO dodge_dm;
 global_instance:=senc_mount_global_system_instance(d.ship_class_rule_id,d.class_weapon_mount_id,d.mount_instance);
 SELECT coalesce((SELECT attack_dm FROM senc_ship_system_damage_state WHERE ship_id=d.gunner_ship_id AND system_code=d.mount_kind AND system_instance=global_instance),0) INTO mount_damage;
 SELECT coalesce((SELECT attack_dm FROM senc_ship_system_damage_state WHERE ship_id=d.gunner_ship_id AND system_code='bridge' AND system_instance=1),0) INTO bridge_damage;
 system_damage:=mount_damage+bridge_damage;
 IF expected_weapon IS NULL OR expected_weapon<>NEW.weapon_rule_id OR profile IS NULL OR expected_difficulty IS NULL
  OR t.actor_id<>actor OR t.skill_rule_id<>expected_skill OR t.difficulty_rule_id<>expected_difficulty OR t.circumstance_modifier<>NEW.total_circumstance_modifier
  OR t.check_total<>NEW.attack_total OR t.target_number<>NEW.target_number OR t.effect<>NEW.effect OR t.succeeded<>NEW.hit
  OR NEW.weapon_profile_code<>profile OR NEW.difficulty_rule_id<>expected_difficulty OR NEW.weapon_modifier<>weapon_dm
  OR NEW.coordinate_crew_modifier<>coord OR NEW.line_up_modifier<>line_dm OR NEW.sensor_targeting_modifier<>sensor_dm
  OR NEW.pursuit_modifier<>pursuit_dm OR NEW.evasive_modifier<>evade_dm OR NEW.dodge_modifier<>dodge_dm
  OR NEW.system_damage_modifier<>system_damage THEN
  RAISE EXCEPTION 'Mount weapon attack check does not recompute from installed weapon, system damage, range, skill, task, and current-round modifiers' USING ERRCODE='23514';
 END IF; RETURN NEW;
END $$;

CREATE FUNCTION senc_apply_terminal_system_damage() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.applied_location='bridge' AND coalesce(NEW.system_hits_after,0)>=2 THEN
  UPDATE senc_ship_system_damage_state SET attack_dm=-2 WHERE ship_id=NEW.target_ship_id AND system_code='bridge' AND system_instance=1;
 END IF;
 IF NEW.applied_location='power-plant' AND NEW.effect_code='destroyed-disable-ship' THEN
  UPDATE senc_vessel SET vessel_status='disabled'
  WHERE ship_id=NEW.target_ship_id AND campaign_id=NEW.campaign_id AND vessel_status='engaged';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER senc_damage_location_terminal_system_effects
AFTER INSERT ON senc_damage_location_hit_receipt
FOR EACH ROW EXECUTE FUNCTION senc_apply_terminal_system_damage();
