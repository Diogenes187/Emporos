CREATE OR REPLACE FUNCTION senc_initialize_weapon_readiness(p_senc_vessel_id bigint) RETURNS void LANGUAGE plpgsql AS $$
BEGIN
 INSERT INTO senc_weapon_readiness_state(engagement_id,campaign_id,senc_vessel_id,ship_id,class_weapon_mount_id,ship_class_rule_id,mount_instance,weapon_slot,weapon_rule_id,resource_type_code,ammunition_per_attack)
 SELECT v.engagement_id,v.campaign_id,v.senc_vessel_id,v.ship_id,m.class_weapon_mount_id,m.ship_class_rule_id,instance.number,w.weapon_slot,w.weapon_rule_id,
  CASE d.weapon_kind WHEN 'sandcaster' THEN 'sand' ELSE 'missiles' END,d.ammunition_per_attack
 FROM senc_vessel v JOIN ship_ship s ON s.ship_id=v.ship_id JOIN ship_class_weapon_mount m ON m.ship_class_rule_id=s.ship_class_rule_id
 JOIN LATERAL generate_series(1,m.mount_count) instance(number) ON true
 JOIN ship_class_mount_weapon w ON w.class_weapon_mount_id=m.class_weapon_mount_id AND w.ship_class_rule_id=m.ship_class_rule_id
 JOIN ship_weapon_definition d ON d.weapon_rule_id=w.weapon_rule_id
 WHERE v.senc_vessel_id=p_senc_vessel_id AND d.ammunition_per_attack>0 ON CONFLICT DO NOTHING;
END $$;

CREATE OR REPLACE FUNCTION senc_consume_mount_attack_ammunition() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE declaration senc_mount_attack_declaration%ROWTYPE; state senc_weapon_readiness_state%ROWTYPE; balance numeric; movement bigint;
BEGIN
 SELECT * INTO STRICT declaration FROM senc_mount_attack_declaration WHERE mount_attack_declaration_id=NEW.mount_attack_declaration_id;
 IF EXISTS(SELECT 1 FROM ship_weapon_definition WHERE weapon_rule_id=NEW.weapon_rule_id AND ammunition_per_attack>0) THEN
  PERFORM senc_initialize_weapon_readiness(declaration.attacker_vessel_id);
  SELECT * INTO STRICT state FROM senc_weapon_readiness_state WHERE engagement_id=declaration.engagement_id AND senc_vessel_id=declaration.attacker_vessel_id
   AND class_weapon_mount_id=declaration.class_weapon_mount_id AND mount_instance=declaration.mount_instance AND weapon_slot=NEW.weapon_slot FOR UPDATE;
  SELECT current_quantity INTO STRICT balance FROM ship_resource WHERE ship_id=state.ship_id AND resource_type_code=state.resource_type_code FOR UPDATE;
  IF state.readiness_status<>'ready' OR balance<state.ammunition_per_attack THEN RAISE EXCEPTION 'Ammunition weapon system is spent or lacks reserve ammunition' USING ERRCODE='23514'; END IF;
  UPDATE ship_resource SET current_quantity=balance-state.ammunition_per_attack,updated_at=clock_timestamp() WHERE ship_id=state.ship_id AND resource_type_code=state.resource_type_code;
  INSERT INTO ship_resource_movement(ship_id,campaign_id,resource_type_code,quantity_delta,balance_after,movement_kind)
  VALUES(state.ship_id,state.campaign_id,state.resource_type_code,-state.ammunition_per_attack,balance-state.ammunition_per_attack,'consume') RETURNING resource_movement_id INTO movement;
  UPDATE senc_weapon_readiness_state SET readiness_status='spent',concurrency_version=state.concurrency_version+1,updated_at=clock_timestamp()
   WHERE engagement_id=state.engagement_id AND senc_vessel_id=state.senc_vessel_id AND class_weapon_mount_id=state.class_weapon_mount_id AND mount_instance=state.mount_instance AND weapon_slot=state.weapon_slot;
  INSERT INTO senc_weapon_ammunition_consumption_receipt(mount_weapon_attack_check_id,engagement_id,campaign_id,senc_vessel_id,ship_id,class_weapon_mount_id,mount_instance,weapon_slot,weapon_rule_id,resource_type_code,quantity_consumed,resource_movement_id,readiness_version_before,readiness_version_after)
  VALUES(NEW.mount_weapon_attack_check_id,state.engagement_id,state.campaign_id,state.senc_vessel_id,state.ship_id,state.class_weapon_mount_id,state.mount_instance,state.weapon_slot,state.weapon_rule_id,state.resource_type_code,state.ammunition_per_attack,movement,state.concurrency_version,state.concurrency_version+1);
 END IF; RETURN NEW;
END $$;

CREATE FUNCTION senc_spend_fire_sand_system() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE state senc_weapon_readiness_state%ROWTYPE; movement bigint;
BEGIN
 PERFORM senc_initialize_weapon_readiness(NEW.senc_vessel_id);
 SELECT * INTO state FROM senc_weapon_readiness_state WHERE engagement_id=NEW.engagement_id AND senc_vessel_id=NEW.senc_vessel_id
  AND resource_type_code='sand' AND readiness_status='ready' ORDER BY class_weapon_mount_id,mount_instance,weapon_slot LIMIT 1 FOR UPDATE;
 IF state.senc_vessel_id IS NULL THEN RAISE EXCEPTION 'Fire Sand requires a ready individual sandcaster' USING ERRCODE='23514'; END IF;
 SELECT resource_movement_id INTO STRICT movement FROM senc_fire_sand_ammo_receipt WHERE fire_sand_attempt_receipt_id=NEW.fire_sand_attempt_receipt_id;
 UPDATE senc_weapon_readiness_state SET readiness_status='spent',concurrency_version=state.concurrency_version+1,updated_at=clock_timestamp()
 WHERE engagement_id=state.engagement_id AND senc_vessel_id=state.senc_vessel_id AND class_weapon_mount_id=state.class_weapon_mount_id AND mount_instance=state.mount_instance AND weapon_slot=state.weapon_slot;
 INSERT INTO senc_weapon_ammunition_consumption_receipt(fire_sand_attempt_receipt_id,engagement_id,campaign_id,senc_vessel_id,ship_id,class_weapon_mount_id,mount_instance,weapon_slot,weapon_rule_id,resource_type_code,quantity_consumed,resource_movement_id,readiness_version_before,readiness_version_after)
 VALUES(NEW.fire_sand_attempt_receipt_id,state.engagement_id,state.campaign_id,state.senc_vessel_id,state.ship_id,state.class_weapon_mount_id,state.mount_instance,state.weapon_slot,state.weapon_rule_id,'sand',1,movement,state.concurrency_version,state.concurrency_version+1);
 RETURN NEW;
END $$;
CREATE TRIGGER senc_fire_sand_spend_system AFTER INSERT ON senc_fire_sand_attempt_receipt FOR EACH ROW EXECUTE FUNCTION senc_spend_fire_sand_system();
