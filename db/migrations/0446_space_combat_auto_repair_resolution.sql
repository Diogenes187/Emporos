CREATE TABLE senc_auto_repair_attempt(
 auto_repair_attempt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 repair_drone_round_allocation_id bigint NOT NULL REFERENCES senc_repair_drone_round_allocation(repair_drone_round_allocation_id),
 check_order smallint NOT NULL CHECK(check_order BETWEEN 1 AND 2),engagement_id bigint NOT NULL,campaign_id bigint NOT NULL,
 space_combat_round_id bigint NOT NULL,senc_vessel_id bigint NOT NULL,ship_id bigint NOT NULL,
 system_code text NOT NULL,system_instance smallint NOT NULL CHECK(system_instance>0),
 die_one smallint NOT NULL CHECK(die_one BETWEEN 1 AND 6),die_two smallint NOT NULL CHECK(die_two BETWEEN 1 AND 6),
 check_modifier smallint NOT NULL CHECK(check_modifier=1),check_total smallint NOT NULL,target_number smallint NOT NULL CHECK(target_number=8),
 effect smallint NOT NULL,succeeded boolean NOT NULL,hits_available smallint,hits_repaired smallint,
 system_hits_before smallint NOT NULL CHECK(system_hits_before BETWEEN 1 AND 3),system_hits_after smallint NOT NULL CHECK(system_hits_after BETWEEN 0 AND 3),
 system_version_before bigint NOT NULL,system_version_after bigint NOT NULL,
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(space_combat_round_id,engagement_id,campaign_id) REFERENCES senc_round(space_combat_round_id,engagement_id,campaign_id),
 FOREIGN KEY(senc_vessel_id,engagement_id,campaign_id) REFERENCES senc_vessel(senc_vessel_id,engagement_id,campaign_id),
 FOREIGN KEY(ship_id,system_code,system_instance) REFERENCES senc_ship_system_damage_state(ship_id,system_code,system_instance),
 UNIQUE(repair_drone_round_allocation_id,check_order),
 CHECK(check_total=die_one+die_two+check_modifier),CHECK(effect=check_total-target_number),CHECK(succeeded=(check_total>=target_number)),
 CHECK((succeeded AND hits_available BETWEEN 1 AND 3 AND hits_repaired BETWEEN 1 AND 3
   AND system_hits_after=system_hits_before-hits_repaired AND system_version_after=system_version_before+1)
  OR (NOT succeeded AND hits_available IS NULL AND hits_repaired IS NULL
   AND system_hits_after=system_hits_before AND system_version_after=system_version_before))
);
CREATE TABLE senc_auto_repair_temporary_state(
 auto_repair_attempt_id bigint PRIMARY KEY REFERENCES senc_auto_repair_attempt(auto_repair_attempt_id),
 engagement_id bigint NOT NULL,ship_id bigint NOT NULL,campaign_id bigint NOT NULL,system_code text NOT NULL,system_instance smallint NOT NULL,
 restored_hits smallint NOT NULL CHECK(restored_hits BETWEEN 1 AND 3),restoration_status text NOT NULL DEFAULT 'active' CHECK(restoration_status IN('active','expired','superseded')),
 applied_at timestamptz NOT NULL DEFAULT clock_timestamp(),ended_at timestamptz,
 FOREIGN KEY(ship_id,system_code,system_instance) REFERENCES senc_ship_system_damage_state(ship_id,system_code,system_instance),
 CHECK((restoration_status='active')=(ended_at IS NULL))
);
CREATE TABLE senc_auto_repair_expiration_receipt(
 auto_repair_attempt_id bigint PRIMARY KEY REFERENCES senc_auto_repair_attempt(auto_repair_attempt_id),
 engagement_id bigint NOT NULL,ship_id bigint NOT NULL,campaign_id bigint NOT NULL,system_code text NOT NULL,system_instance smallint NOT NULL,
 restored_hits_expired smallint NOT NULL CHECK(restored_hits_expired BETWEEN 1 AND 3),system_hits_before smallint NOT NULL CHECK(system_hits_before BETWEEN 0 AND 3),
 system_hits_after smallint NOT NULL CHECK(system_hits_after BETWEEN system_hits_before AND 3),system_version_before bigint NOT NULL,
 system_version_after bigint NOT NULL CHECK(system_version_after=system_version_before+1),expired_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(ship_id,system_code,system_instance) REFERENCES senc_ship_system_damage_state(ship_id,system_code,system_instance)
);

CREATE FUNCTION senc_apply_auto_repair_attempt() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE allocation senc_repair_drone_round_allocation%ROWTYPE; state senc_ship_system_damage_state%ROWTYPE; expected_hits smallint;
 new_hits smallint; new_status text; new_attack smallint; new_sensor smallint; expected_target integer;
BEGIN
 SELECT * INTO STRICT allocation FROM senc_repair_drone_round_allocation WHERE repair_drone_round_allocation_id=NEW.repair_drone_round_allocation_id;
 SELECT check_rule.target_number INTO STRICT expected_target FROM rule_check_system check_rule CROSS JOIN rule_difficulty difficulty WHERE difficulty.is_default;
 SELECT * INTO STRICT state FROM senc_ship_system_damage_state WHERE ship_id=NEW.ship_id AND system_code=NEW.system_code
  AND system_instance=NEW.system_instance FOR UPDATE;
 IF allocation.allocation_mode<>'autonomous' OR NEW.check_order>allocation.autonomous_check_capacity
  OR allocation.engagement_id<>NEW.engagement_id OR allocation.campaign_id<>NEW.campaign_id
  OR allocation.space_combat_round_id<>NEW.space_combat_round_id OR allocation.senc_vessel_id<>NEW.senc_vessel_id OR allocation.ship_id<>NEW.ship_id
  OR NEW.check_modifier<>1 OR expected_target<>NEW.target_number OR NEW.check_total<>NEW.die_one+NEW.die_two+1
  OR NEW.effect<>NEW.check_total-NEW.target_number OR NEW.succeeded<>(NEW.check_total>=NEW.target_number)
  OR NEW.system_hits_before<>state.hit_count OR NEW.system_version_before<>state.concurrency_version THEN
  RAISE EXCEPTION 'Auto-Repair attempt must match its autonomous allocation, default task check, and current damaged system' USING ERRCODE='23514'; END IF;
 IF NEW.check_order>1 AND NOT EXISTS(SELECT 1 FROM senc_auto_repair_attempt prior
   WHERE prior.repair_drone_round_allocation_id=NEW.repair_drone_round_allocation_id AND prior.check_order=NEW.check_order-1) THEN
  RAISE EXCEPTION 'Auto-Repair checks must be recorded in order' USING ERRCODE='23514'; END IF;
 IF NEW.succeeded THEN
  SELECT least(band.hits_repaired,state.hit_count) INTO STRICT expected_hits FROM rule_space_combat_repair_effect_band band
   JOIN rule_rule rule ON rule.rule_id=band.rule_id WHERE rule.rule_code='combat.space.battlefield-repair'
   AND NEW.effect>=band.effect_min AND (band.effect_max IS NULL OR NEW.effect<=band.effect_max);
  IF NEW.hits_available<>state.hit_count OR NEW.hits_repaired<>expected_hits OR NEW.system_hits_after<>state.hit_count-expected_hits
   OR NEW.system_version_after<>state.concurrency_version+1 THEN RAISE EXCEPTION 'Successful Auto-Repair outcome does not match its Effect band' USING ERRCODE='23514'; END IF;
  new_hits:=state.hit_count-expected_hits;
  new_status:=CASE new_hits WHEN 0 THEN 'operational' WHEN 1 THEN 'damaged' WHEN 2 THEN 'disabled' ELSE 'destroyed' END;
  new_attack:=CASE WHEN NEW.system_code IN('turret','bay') AND new_hits=1 THEN -2 WHEN NEW.system_code='bridge' AND new_hits>=2 THEN -2 ELSE 0 END;
  new_sensor:=CASE WHEN NEW.system_code='sensors' AND new_hits>=1 THEN -2 ELSE 0 END;
  UPDATE senc_ship_system_damage_state SET hit_count=new_hits,system_status=new_status,attack_dm=new_attack,sensor_dm=new_sensor,
   concurrency_version=state.concurrency_version+1,updated_at=clock_timestamp()
   WHERE ship_id=NEW.ship_id AND system_code=NEW.system_code AND system_instance=NEW.system_instance;
  PERFORM senc_recompute_damaged_system_runtime(NEW.ship_id,NEW.system_code);
 ELSE
  IF NEW.hits_available IS NOT NULL OR NEW.hits_repaired IS NOT NULL OR NEW.system_hits_after<>state.hit_count
   OR NEW.system_version_after<>state.concurrency_version THEN RAISE EXCEPTION 'Failed Auto-Repair attempt cannot change system state' USING ERRCODE='23514'; END IF;
 END IF; RETURN NEW;
END $$;
CREATE TRIGGER senc_auto_repair_attempt_valid BEFORE INSERT ON senc_auto_repair_attempt FOR EACH ROW EXECUTE FUNCTION senc_apply_auto_repair_attempt();
CREATE FUNCTION senc_record_auto_repair_temporary_state() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN IF NEW.succeeded THEN INSERT INTO senc_auto_repair_temporary_state(auto_repair_attempt_id,engagement_id,ship_id,campaign_id,system_code,system_instance,restored_hits)
 VALUES(NEW.auto_repair_attempt_id,NEW.engagement_id,NEW.ship_id,NEW.campaign_id,NEW.system_code,NEW.system_instance,NEW.hits_repaired); END IF; RETURN NEW; END $$;
CREATE TRIGGER senc_auto_repair_attempt_state AFTER INSERT ON senc_auto_repair_attempt FOR EACH ROW EXECUTE FUNCTION senc_record_auto_repair_temporary_state();
CREATE FUNCTION senc_reject_auto_repair_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Auto-Repair receipts are immutable'; END $$;
CREATE TRIGGER senc_auto_repair_attempt_immutable BEFORE UPDATE OR DELETE ON senc_auto_repair_attempt FOR EACH ROW EXECUTE FUNCTION senc_reject_auto_repair_mutation();
CREATE TRIGGER senc_auto_repair_expiration_immutable BEFORE UPDATE OR DELETE ON senc_auto_repair_expiration_receipt FOR EACH ROW EXECUTE FUNCTION senc_reject_auto_repair_mutation();

CREATE OR REPLACE FUNCTION senc_expire_battlefield_repairs() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE repair record; state senc_ship_system_damage_state%ROWTYPE; after_hits smallint; after_status text; after_attack smallint; after_sensor smallint;
BEGIN
 IF OLD.engagement_status='active' AND NEW.engagement_status IN('resolved','escaped','aborted') THEN
  FOR repair IN
   SELECT 'manual' origin,temporary.battlefield_repair_receipt_id origin_id,temporary.engagement_id,temporary.ship_id,temporary.campaign_id,temporary.system_code,temporary.system_instance,temporary.restored_hits
   FROM senc_system_temporary_repair_state temporary WHERE temporary.engagement_id=NEW.engagement_id AND temporary.restoration_status='active'
   UNION ALL SELECT 'auto',temporary.auto_repair_attempt_id,temporary.engagement_id,temporary.ship_id,temporary.campaign_id,temporary.system_code,temporary.system_instance,temporary.restored_hits
   FROM senc_auto_repair_temporary_state temporary WHERE temporary.engagement_id=NEW.engagement_id AND temporary.restoration_status='active'
   ORDER BY origin,origin_id LOOP
   SELECT * INTO STRICT state FROM senc_ship_system_damage_state WHERE ship_id=repair.ship_id AND system_code=repair.system_code AND system_instance=repair.system_instance FOR UPDATE;
   after_hits:=least(3,state.hit_count+repair.restored_hits); after_status:=CASE after_hits WHEN 0 THEN 'operational' WHEN 1 THEN 'damaged' WHEN 2 THEN 'disabled' ELSE 'destroyed' END;
   after_attack:=CASE WHEN repair.system_code IN('turret','bay') AND after_hits=1 THEN -2 WHEN repair.system_code='bridge' AND after_hits>=2 THEN -2 ELSE 0 END;
   after_sensor:=CASE WHEN repair.system_code='sensors' AND after_hits>=1 THEN -2 ELSE 0 END;
   UPDATE senc_ship_system_damage_state SET hit_count=after_hits,system_status=after_status,attack_dm=after_attack,sensor_dm=after_sensor,
    concurrency_version=state.concurrency_version+1,updated_at=clock_timestamp() WHERE ship_id=repair.ship_id AND system_code=repair.system_code AND system_instance=repair.system_instance;
   IF repair.origin='manual' THEN
    INSERT INTO senc_system_repair_expiration_receipt VALUES(repair.origin_id,repair.engagement_id,repair.ship_id,repair.campaign_id,repair.system_code,repair.system_instance,
     repair.restored_hits,state.hit_count,after_hits,state.concurrency_version,state.concurrency_version+1,clock_timestamp());
    UPDATE senc_system_temporary_repair_state SET restoration_status='expired',ended_at=clock_timestamp() WHERE battlefield_repair_receipt_id=repair.origin_id;
   ELSE
    INSERT INTO senc_auto_repair_expiration_receipt VALUES(repair.origin_id,repair.engagement_id,repair.ship_id,repair.campaign_id,repair.system_code,repair.system_instance,
     repair.restored_hits,state.hit_count,after_hits,state.concurrency_version,state.concurrency_version+1,clock_timestamp());
    UPDATE senc_auto_repair_temporary_state SET restoration_status='expired',ended_at=clock_timestamp() WHERE auto_repair_attempt_id=repair.origin_id;
   END IF;
   PERFORM senc_recompute_damaged_system_runtime(repair.ship_id,repair.system_code);
  END LOOP;
 END IF; RETURN NEW;
END $$;
