CREATE TABLE senc_system_repair_expiration_receipt(
 battlefield_repair_receipt_id bigint PRIMARY KEY REFERENCES senc_system_battlefield_repair_receipt(battlefield_repair_receipt_id),
 engagement_id bigint NOT NULL,ship_id bigint NOT NULL,campaign_id bigint NOT NULL,system_code text NOT NULL,system_instance smallint NOT NULL,
 restored_hits_expired smallint NOT NULL CHECK(restored_hits_expired BETWEEN 1 AND 3),system_hits_before smallint NOT NULL CHECK(system_hits_before BETWEEN 0 AND 3),
 system_hits_after smallint NOT NULL CHECK(system_hits_after BETWEEN system_hits_before AND 3),system_version_before bigint NOT NULL,
 system_version_after bigint NOT NULL CHECK(system_version_after=system_version_before+1),expired_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(ship_id,system_code,system_instance) REFERENCES senc_ship_system_damage_state(ship_id,system_code,system_instance)
);

CREATE OR REPLACE FUNCTION senc_recompute_damaged_system_runtime(p_ship_id bigint,p_system_code text) RETURNS void LANGUAGE plpgsql AS $$
DECLARE hits smallint; class_thrust smallint; effective_thrust smallint;
BEGIN
 SELECT hit_count INTO hits FROM senc_ship_system_damage_state WHERE ship_id=p_ship_id AND system_code=p_system_code AND system_instance=1;
 IF p_system_code='m-drive' THEN
  SELECT class.maneuver_rating INTO class_thrust FROM ship_ship ship JOIN ship_class class USING(ship_class_rule_id) WHERE ship.ship_id=p_ship_id;
  effective_thrust:=CASE hits WHEN 0 THEN class_thrust WHEN 1 THEN greatest(0,class_thrust-1)
   WHEN 2 THEN floor(greatest(0,class_thrust-1)::numeric/2)::smallint ELSE 0 END;
  UPDATE senc_vessel vessel SET thrust_current=effective_thrust FROM senc_engagement engagement
   WHERE vessel.engagement_id=engagement.engagement_id AND vessel.ship_id=p_ship_id AND engagement.engagement_status='active';
 ELSIF p_system_code='power-plant' THEN
  UPDATE senc_vessel vessel SET vessel_status=CASE WHEN hits>=3 THEN 'disabled' ELSE 'engaged' END FROM senc_engagement engagement
   WHERE vessel.engagement_id=engagement.engagement_id AND vessel.ship_id=p_ship_id
    AND engagement.engagement_status='active' AND vessel.vessel_status IN('engaged','disabled');
 ELSIF p_system_code='fuel' THEN
  UPDATE senc_ship_fuel_leak_state SET leak_status=CASE WHEN hits=0 THEN 'sealed' WHEN hits>=3 THEN 'tank-destroyed' ELSE 'active' END,
   concurrency_version=concurrency_version+1,updated_at=clock_timestamp() WHERE ship_id=p_ship_id;
 END IF;
END $$;

CREATE FUNCTION senc_expire_battlefield_repairs() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE repair record; state senc_ship_system_damage_state%ROWTYPE; after_hits smallint; after_status text; after_attack smallint; after_sensor smallint;
BEGIN
 IF OLD.engagement_status='active' AND NEW.engagement_status IN('resolved','escaped','aborted') THEN
  FOR repair IN SELECT temporary.* FROM senc_system_temporary_repair_state temporary
   WHERE temporary.engagement_id=NEW.engagement_id AND temporary.restoration_status='active'
   ORDER BY temporary.battlefield_repair_receipt_id FOR UPDATE LOOP
   SELECT * INTO STRICT state FROM senc_ship_system_damage_state WHERE ship_id=repair.ship_id
    AND system_code=repair.system_code AND system_instance=repair.system_instance FOR UPDATE;
   after_hits:=least(3,state.hit_count+repair.restored_hits);
   after_status:=CASE after_hits WHEN 0 THEN 'operational' WHEN 1 THEN 'damaged' WHEN 2 THEN 'disabled' ELSE 'destroyed' END;
   after_attack:=CASE WHEN repair.system_code IN('turret','bay') AND after_hits=1 THEN -2
    WHEN repair.system_code='bridge' AND after_hits>=2 THEN -2 ELSE 0 END;
   after_sensor:=CASE WHEN repair.system_code='sensors' AND after_hits>=1 THEN -2 ELSE 0 END;
   UPDATE senc_ship_system_damage_state SET hit_count=after_hits,system_status=after_status,attack_dm=after_attack,sensor_dm=after_sensor,
    concurrency_version=state.concurrency_version+1,updated_at=clock_timestamp()
   WHERE ship_id=repair.ship_id AND system_code=repair.system_code AND system_instance=repair.system_instance;
   INSERT INTO senc_system_repair_expiration_receipt(battlefield_repair_receipt_id,engagement_id,ship_id,campaign_id,
    system_code,system_instance,restored_hits_expired,system_hits_before,system_hits_after,system_version_before,system_version_after)
   VALUES(repair.battlefield_repair_receipt_id,repair.engagement_id,repair.ship_id,repair.campaign_id,repair.system_code,
    repair.system_instance,repair.restored_hits,state.hit_count,after_hits,state.concurrency_version,state.concurrency_version+1);
   UPDATE senc_system_temporary_repair_state SET restoration_status='expired',ended_at=clock_timestamp()
    WHERE battlefield_repair_receipt_id=repair.battlefield_repair_receipt_id;
   PERFORM senc_recompute_damaged_system_runtime(repair.ship_id,repair.system_code);
  END LOOP;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER senc_engagement_expire_battlefield_repairs AFTER UPDATE OF engagement_status ON senc_engagement
FOR EACH ROW EXECUTE FUNCTION senc_expire_battlefield_repairs();
CREATE FUNCTION senc_reject_repair_expiration_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Battlefield repair expiration receipts are immutable'; END $$;
CREATE TRIGGER senc_system_repair_expiration_immutable BEFORE UPDATE OR DELETE ON senc_system_repair_expiration_receipt
FOR EACH ROW EXECUTE FUNCTION senc_reject_repair_expiration_mutation();
