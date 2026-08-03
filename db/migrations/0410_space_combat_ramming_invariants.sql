CREATE FUNCTION senc_validate_ram_attempt_snapshots() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE actual_round integer; actual_range text; ram_speed numeric; target_speed numeric;
 a record; b record; ram_value smallint; target_value smallint;
BEGIN
 SELECT round_number INTO actual_round FROM senc_round WHERE space_combat_round_id=NEW.space_combat_round_id;
 SELECT range_band_code INTO actual_range FROM senc_vessel_range WHERE engagement_id=NEW.engagement_id
  AND first_vessel_id=least(NEW.ramming_vessel_id,NEW.target_vessel_id)
  AND second_vessel_id=greatest(NEW.ramming_vessel_id,NEW.target_vessel_id);
 SELECT speed_current INTO ram_speed FROM senc_vessel WHERE senc_vessel_id=NEW.ramming_vessel_id;
 SELECT speed_current INTO target_speed FROM senc_vessel WHERE senc_vessel_id=NEW.target_vessel_id;
 SELECT actor_id,characteristic_rule_id INTO a FROM cmd_actor_task_receipt WHERE command_id=NEW.ramming_task_command_id;
 SELECT actor_id,characteristic_rule_id INTO b FROM cmd_actor_task_receipt WHERE command_id=NEW.target_task_command_id;
 SELECT current_value INTO ram_value FROM actor_characteristic WHERE actor_id=a.actor_id AND characteristic_rule_id=a.characteristic_rule_id;
 SELECT current_value INTO target_value FROM actor_characteristic WHERE actor_id=b.actor_id AND characteristic_rule_id=b.characteristic_rule_id;
 IF actual_round<>NEW.round_number OR actual_range<>NEW.range_band_snapshot
  OR ram_speed<>NEW.ramming_speed_snapshot OR target_speed<>NEW.target_speed_snapshot
  OR ram_speed<=target_speed OR ram_speed-target_speed<>NEW.speed_difference
  OR a.characteristic_rule_id<>b.characteristic_rule_id
  OR ram_value<>NEW.ramming_characteristic_value OR target_value<>NEW.target_characteristic_value THEN
  RAISE EXCEPTION 'Ram attempt round, range, speed, or characteristic snapshot is inconsistent' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER senc_ram_attempt_00_snapshots_valid BEFORE INSERT ON senc_ram_attempt_receipt
FOR EACH ROW EXECUTE FUNCTION senc_validate_ram_attempt_snapshots();

CREATE FUNCTION senc_guard_ram_die_insert() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE attempt senc_ram_attempt_receipt%ROWTYPE;
BEGIN
 SELECT * INTO STRICT attempt FROM senc_ram_attempt_receipt WHERE ram_attempt_receipt_id=NEW.ram_attempt_receipt_id FOR UPDATE;
 IF attempt.resolution_status<>'succeeded' OR EXISTS(
  SELECT 1 FROM senc_ram_final_receipt WHERE ram_attempt_receipt_id=NEW.ram_attempt_receipt_id
 ) OR NEW.die_order>attempt.speed_difference THEN
  RAISE EXCEPTION 'Ram damage dice require an unfinalized successful collision and exact die order' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER senc_ram_die_insert_valid BEFORE INSERT ON senc_ram_damage_die
FOR EACH ROW EXECUTE FUNCTION senc_guard_ram_die_insert();

CREATE FUNCTION senc_validate_ram_allocation_insert() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE receipt senc_ram_final_receipt%ROWTYPE; attempt senc_ram_attempt_receipt%ROWTYPE;
 expected_ship bigint; expected_points integer; damage record;
BEGIN
 SELECT * INTO STRICT receipt FROM senc_ram_final_receipt WHERE ram_attempt_receipt_id=NEW.ram_attempt_receipt_id;
 SELECT * INTO STRICT attempt FROM senc_ram_attempt_receipt WHERE ram_attempt_receipt_id=NEW.ram_attempt_receipt_id;
 expected_ship:=CASE NEW.affected_vessel WHEN 'rammer' THEN receipt.rammer_ship_id ELSE receipt.target_ship_id END;
 expected_points:=CASE
  WHEN NEW.affected_vessel='rammer' AND NEW.damage_kind='hull' THEN receipt.rammer_hull_before-receipt.rammer_hull_after
  WHEN NEW.affected_vessel='rammer' THEN receipt.rammer_structure_before-receipt.rammer_structure_after
  WHEN NEW.damage_kind='hull' THEN receipt.target_hull_before-receipt.target_hull_after
  ELSE receipt.target_structure_before-receipt.target_structure_after END;
 SELECT ship_id,campaign_id,target_kind,damage_points INTO damage FROM ship_damage WHERE ship_damage_id=NEW.ship_damage_id;
 IF expected_points<=0 OR NEW.damage_points<>expected_points OR damage.ship_id<>expected_ship
  OR damage.campaign_id<>attempt.campaign_id OR damage.target_kind<>NEW.damage_kind
  OR damage.damage_points<>NEW.damage_points THEN
  RAISE EXCEPTION 'Ram damage allocation is inconsistent with final receipt and ship damage' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER senc_ram_allocation_insert_valid BEFORE INSERT ON senc_ram_damage_allocation
FOR EACH ROW EXECUTE FUNCTION senc_validate_ram_allocation_insert();
