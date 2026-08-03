CREATE OR REPLACE FUNCTION senc_apply_weapon_reload() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE action_row record; state senc_weapon_readiness_state%ROWTYPE; reserve_quantity numeric;
BEGIN
 SELECT a.action_code,a.space_combat_round_id,t.senc_vessel_id,t.crew_assignment_id,ca.ship_id,ca.duty_status INTO STRICT action_row
 FROM senc_action a JOIN senc_crew_turn t USING(crew_turn_id) JOIN ship_crew_assignment ca USING(crew_assignment_id) WHERE a.space_combat_action_id=NEW.action_id;
 SELECT * INTO STRICT state FROM senc_weapon_readiness_state WHERE engagement_id=NEW.engagement_id AND senc_vessel_id=NEW.senc_vessel_id
  AND class_weapon_mount_id=NEW.class_weapon_mount_id AND mount_instance=NEW.mount_instance AND weapon_slot=NEW.weapon_slot FOR UPDATE;
 SELECT current_quantity INTO reserve_quantity FROM ship_resource WHERE ship_id=state.ship_id AND resource_type_code=state.resource_type_code FOR UPDATE;
 IF action_row.action_code<>'reload-weapons' OR action_row.space_combat_round_id<>NEW.space_combat_round_id OR action_row.senc_vessel_id<>NEW.senc_vessel_id
  OR action_row.crew_assignment_id<>NEW.reloader_assignment_id OR action_row.ship_id<>NEW.ship_id OR action_row.duty_status<>'active'
  OR state.ship_id<>NEW.ship_id OR state.weapon_rule_id<>NEW.weapon_rule_id OR state.readiness_status<>'spent'
  OR reserve_quantity IS NULL OR reserve_quantity<state.ammunition_per_attack
  OR state.concurrency_version<>NEW.readiness_version_before OR NEW.readiness_version_after<>state.concurrency_version+1 THEN
  RAISE EXCEPTION 'Reload Weapons System must target one matching spent system with sufficient reserve ammunition' USING ERRCODE='23514'; END IF;
 UPDATE senc_weapon_readiness_state SET readiness_status='ready',concurrency_version=state.concurrency_version+1,updated_at=clock_timestamp()
 WHERE engagement_id=state.engagement_id AND senc_vessel_id=state.senc_vessel_id AND class_weapon_mount_id=state.class_weapon_mount_id AND mount_instance=state.mount_instance AND weapon_slot=state.weapon_slot;
 RETURN NEW;
END $$;
