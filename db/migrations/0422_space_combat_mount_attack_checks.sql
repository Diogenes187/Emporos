CREATE TABLE senc_mount_attack_declaration(
 mount_attack_declaration_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 action_id bigint NOT NULL UNIQUE,engagement_id bigint NOT NULL,campaign_id bigint NOT NULL,
 space_combat_round_id bigint NOT NULL,round_number integer NOT NULL CHECK(round_number>0),
 attacker_vessel_id bigint NOT NULL,target_vessel_id bigint NOT NULL,gunner_assignment_id bigint NOT NULL,gunner_ship_id bigint NOT NULL,
 class_weapon_mount_id bigint NOT NULL,ship_class_rule_id bigint NOT NULL,mount_instance smallint NOT NULL CHECK(mount_instance>0),
 mount_code text NOT NULL REFERENCES rule_ship_weapon_mount(mount_code),mount_kind text NOT NULL CHECK(mount_kind IN('turret','bay')),
 range_band_code text NOT NULL REFERENCES rule_space_range_band(range_band_code),recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(action_id,engagement_id,campaign_id) REFERENCES senc_action(space_combat_action_id,engagement_id,campaign_id),
 FOREIGN KEY(space_combat_round_id,engagement_id,campaign_id) REFERENCES senc_round(space_combat_round_id,engagement_id,campaign_id),
 FOREIGN KEY(attacker_vessel_id,engagement_id,campaign_id) REFERENCES senc_vessel(senc_vessel_id,engagement_id,campaign_id),
 FOREIGN KEY(target_vessel_id,engagement_id,campaign_id) REFERENCES senc_vessel(senc_vessel_id,engagement_id,campaign_id),
 FOREIGN KEY(gunner_assignment_id,gunner_ship_id,campaign_id) REFERENCES ship_crew_assignment(crew_assignment_id,ship_id,campaign_id),
 FOREIGN KEY(class_weapon_mount_id,ship_class_rule_id) REFERENCES ship_class_weapon_mount(class_weapon_mount_id,ship_class_rule_id),
 UNIQUE(space_combat_round_id,attacker_vessel_id,class_weapon_mount_id,mount_instance),CHECK(attacker_vessel_id<>target_vessel_id)
);
CREATE TABLE senc_mount_weapon_attack_check(
 mount_weapon_attack_check_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 mount_attack_declaration_id bigint NOT NULL REFERENCES senc_mount_attack_declaration(mount_attack_declaration_id),
 weapon_slot smallint NOT NULL CHECK(weapon_slot>0),weapon_rule_id bigint NOT NULL REFERENCES ship_weapon_definition(weapon_rule_id),
 weapon_profile_code text NOT NULL,task_command_id bigint NOT NULL UNIQUE REFERENCES cmd_actor_task_receipt(command_id),
 coordinate_crew_allocation_id bigint UNIQUE REFERENCES senc_coordinate_crew_allocation(coordinate_crew_allocation_id),
 difficulty_rule_id bigint NOT NULL REFERENCES rule_difficulty(rule_id),weapon_modifier smallint NOT NULL,
 coordinate_crew_modifier smallint NOT NULL DEFAULT 0 CHECK(coordinate_crew_modifier>=0),line_up_modifier smallint NOT NULL DEFAULT 0 CHECK(line_up_modifier BETWEEN 0 AND 2),
 sensor_targeting_modifier smallint NOT NULL DEFAULT 0 CHECK(sensor_targeting_modifier BETWEEN 0 AND 2),pursuit_modifier smallint NOT NULL DEFAULT 0 CHECK(pursuit_modifier BETWEEN 0 AND 4),
 evasive_modifier smallint NOT NULL DEFAULT 0 CHECK(evasive_modifier BETWEEN -2 AND 0),dodge_modifier smallint NOT NULL DEFAULT 0 CHECK(dodge_modifier IN(-2,0)),
 computer_targeting_modifier smallint NOT NULL DEFAULT 0 CHECK(computer_targeting_modifier=0),total_circumstance_modifier smallint NOT NULL,
 attack_total smallint NOT NULL,target_number smallint NOT NULL,effect smallint NOT NULL,hit boolean NOT NULL,
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(mount_attack_declaration_id,weapon_slot),
 CHECK(total_circumstance_modifier=weapon_modifier+coordinate_crew_modifier+line_up_modifier+sensor_targeting_modifier+pursuit_modifier+evasive_modifier+dodge_modifier+computer_targeting_modifier),
 CHECK(effect=attack_total-target_number AND hit=(attack_total>=target_number))
);
CREATE FUNCTION senc_validate_mount_attack_declaration() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE a record; mount record; actual_range text; actual_round integer; class_id bigint;
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
 IF a.action_code<>'attack' OR a.target_vessel_id<>NEW.target_vessel_id OR a.space_combat_round_id<>NEW.space_combat_round_id
  OR a.senc_vessel_id<>NEW.attacker_vessel_id OR a.crew_assignment_id<>NEW.gunner_assignment_id OR a.ship_id<>NEW.gunner_ship_id OR a.duty_status<>'active'
  OR class_id<>NEW.ship_class_rule_id OR mount.mount_code<>NEW.mount_code OR mount.mount_kind<>NEW.mount_kind OR NEW.mount_instance>mount.mount_count
  OR actual_range<>NEW.range_band_code OR actual_round<>NEW.round_number
  OR NOT EXISTS(SELECT 1 FROM senc_crew_role_assignment role WHERE role.engagement_id=NEW.engagement_id AND role.senc_vessel_id=NEW.attacker_vessel_id
   AND role.crew_assignment_id=NEW.gunner_assignment_id AND role.crew_role='gunner' AND role.ended_at IS NULL) THEN
  RAISE EXCEPTION 'Mount attack declaration requires matching action, active Gunner, installed mount instance, target, and current range' USING ERRCODE='23514';
 END IF; RETURN NEW;
END $$;
CREATE TRIGGER senc_mount_attack_declaration_valid BEFORE INSERT ON senc_mount_attack_declaration FOR EACH ROW EXECUTE FUNCTION senc_validate_mount_attack_declaration();
CREATE FUNCTION senc_validate_mount_weapon_attack_check() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE d senc_mount_attack_declaration%ROWTYPE; t cmd_actor_task_receipt%ROWTYPE; actor bigint; expected_weapon bigint; profile text; expected_difficulty bigint;
 expected_skill bigint; weapon_dm integer; coord integer; line_dm integer; sensor_dm integer; pursuit_dm integer; evade_dm integer; dodge_dm integer;
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
 IF expected_weapon IS NULL OR expected_weapon<>NEW.weapon_rule_id OR profile IS NULL OR expected_difficulty IS NULL
  OR t.actor_id<>actor OR t.skill_rule_id<>expected_skill OR t.difficulty_rule_id<>expected_difficulty OR t.circumstance_modifier<>NEW.total_circumstance_modifier
  OR t.check_total<>NEW.attack_total OR t.target_number<>NEW.target_number OR t.effect<>NEW.effect OR t.succeeded<>NEW.hit
  OR NEW.weapon_profile_code<>profile OR NEW.difficulty_rule_id<>expected_difficulty OR NEW.weapon_modifier<>weapon_dm
  OR NEW.coordinate_crew_modifier<>coord OR NEW.line_up_modifier<>line_dm OR NEW.sensor_targeting_modifier<>sensor_dm
  OR NEW.pursuit_modifier<>pursuit_dm OR NEW.evasive_modifier<>evade_dm OR NEW.dodge_modifier<>dodge_dm THEN
  RAISE EXCEPTION 'Mount weapon attack check does not recompute from installed weapon, range, skill, task, and current-round modifiers' USING ERRCODE='23514';
 END IF; RETURN NEW;
END $$;
CREATE TRIGGER senc_mount_weapon_attack_check_valid BEFORE INSERT ON senc_mount_weapon_attack_check FOR EACH ROW EXECUTE FUNCTION senc_validate_mount_weapon_attack_check();
CREATE FUNCTION senc_reject_mount_attack_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Mount attack declarations and checks are immutable'; END $$;
CREATE TRIGGER senc_mount_attack_declaration_immutable BEFORE UPDATE OR DELETE ON senc_mount_attack_declaration FOR EACH ROW EXECUTE FUNCTION senc_reject_mount_attack_mutation();
CREATE TRIGGER senc_mount_weapon_attack_check_immutable BEFORE UPDATE OR DELETE ON senc_mount_weapon_attack_check FOR EACH ROW EXECUTE FUNCTION senc_reject_mount_attack_mutation();
