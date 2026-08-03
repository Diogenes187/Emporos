CREATE OR REPLACE FUNCTION senc_finalize_avoid_collision() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE h senc_collision_hazard%ROWTYPE; action_row record; task record; vessel_ship record; base_difficulty bigint; pilot bigint;
 armor integer; die_count integer; die_total integer; hull_damage integer; structure_damage integer; damage_id bigint;
BEGIN
 SELECT * INTO STRICT h FROM senc_collision_hazard WHERE collision_hazard_id=NEW.collision_hazard_id FOR UPDATE;
 SELECT action.action_code,turn.senc_vessel_id,assignment.actor_id,assignment.ship_id,assignment.duty_status,definition.position_code INTO action_row
 FROM senc_action action JOIN senc_crew_turn turn USING(crew_turn_id) JOIN ship_crew_assignment assignment USING(crew_assignment_id)
 JOIN ship_crew_position ps USING(ship_crew_position_id) JOIN ship_crew_position_definition definition USING(crew_position_rule_id)
 WHERE action.space_combat_action_id=NEW.action_id;
 SELECT actor_id,skill_rule_id,difficulty_rule_id,circumstance_modifier,effect,succeeded INTO task FROM cmd_actor_task_receipt WHERE command_id=NEW.task_command_id;
 SELECT difficulty_rule_id INTO base_difficulty FROM rule_space_collision_hazard WHERE hazard_code=h.hazard_code;
 SELECT rule_id INTO pilot FROM rule_rule WHERE rule_code='skill.piloting';
 SELECT vessel.ship_id,ship_state.ship_class_rule_id,ship_state.hull_current,ship_state.structure_current,ship_state.concurrency_version INTO vessel_ship
 FROM senc_vessel vessel JOIN ship_ship ship_state USING(ship_id) WHERE vessel.senc_vessel_id=h.senc_vessel_id FOR UPDATE OF ship_state;
 SELECT coalesce((SELECT armor_value FROM ship_class_published_armor WHERE ship_class_rule_id=vessel_ship.ship_class_rule_id),
  (SELECT hull.armor_increments*a.protection_per_increment FROM ship_class_design_hull hull JOIN rule_ship_armor_design a USING(armor_code) WHERE hull.ship_class_rule_id=vessel_ship.ship_class_rule_id),0) INTO armor;
 SELECT count(*),coalesce(sum(result),0) INTO die_count,die_total FROM senc_collision_damage_die WHERE collision_hazard_id=h.collision_hazard_id;
 IF action_row.action_code<>'avoid-collision' OR action_row.senc_vessel_id<>h.senc_vessel_id OR action_row.actor_id<>task.actor_id
  OR action_row.ship_id<>NEW.ship_id OR action_row.duty_status<>'active' OR action_row.position_code<>'pilot'
  OR task.skill_rule_id<>pilot OR task.difficulty_rule_id<>base_difficulty
  OR task.circumstance_modifier<>(CASE WHEN h.significant_speed_difference THEN -2 ELSE 0 END)
  OR task.effect<>NEW.task_effect OR task.succeeded<>NEW.task_succeeded
  OR die_count<>(CASE WHEN task.succeeded THEN 0 ELSE h.speed_snapshot END) OR die_total<>NEW.rolled_damage
  OR NEW.ship_id<>vessel_ship.ship_id OR NEW.armor_snapshot<>armor OR NEW.hull_before<>vessel_ship.hull_current
  OR NEW.structure_before<>vessel_ship.structure_current OR NEW.version_before<>vessel_ship.concurrency_version THEN
  RAISE EXCEPTION 'Avoid Collision receipt fails action, task, dice, or ship-state recomputation' USING ERRCODE='23514'; END IF;
 UPDATE ship_ship SET hull_current=NEW.hull_after,structure_current=NEW.structure_after,concurrency_version=NEW.version_after WHERE ship_id=NEW.ship_id;
 hull_damage:=NEW.hull_before-NEW.hull_after; structure_damage:=NEW.structure_before-NEW.structure_after;
 IF hull_damage>0 THEN INSERT INTO ship_damage(ship_id,campaign_id,target_kind,damage_points,description) VALUES(NEW.ship_id,h.campaign_id,'hull',hull_damage,'Collision hazard') RETURNING ship_damage_id INTO damage_id;
  INSERT INTO senc_collision_damage_allocation VALUES(NEW.avoid_collision_receipt_id,'hull',damage_id,hull_damage); END IF;
 IF structure_damage>0 THEN INSERT INTO ship_damage(ship_id,campaign_id,target_kind,damage_points,description) VALUES(NEW.ship_id,h.campaign_id,'structure',structure_damage,'Collision hazard overflow') RETURNING ship_damage_id INTO damage_id;
  INSERT INTO senc_collision_damage_allocation VALUES(NEW.avoid_collision_receipt_id,'structure',damage_id,structure_damage); END IF;
 RETURN NEW;
END $$;
