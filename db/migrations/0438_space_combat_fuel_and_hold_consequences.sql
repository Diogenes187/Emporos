INSERT INTO rule_interpretation(rule_id,interpretation_type,decision_register_entry,rationale)
SELECT rule_id,'agreed_interpretation','CE-SC-009',
 'Raymond approved applying Hold percentage losses proportionally across every stored cargo lot using exact fractional tonnage, avoiding an invented random-lot selection.'
FROM rule_rule WHERE rule_code='combat.space.hit-locations';

CREATE TABLE ship_cargo_lot(
 ship_cargo_lot_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
 ship_id bigint NOT NULL,campaign_id bigint NOT NULL,
 trade_good_rule_id bigint NOT NULL REFERENCES rule_trade_good(trade_good_rule_id),
 source_execution_id bigint REFERENCES mkt_execution(execution_id),
 lot_identifier text NOT NULL CHECK(btrim(lot_identifier)<>''),
 initial_quantity_tons numeric NOT NULL CHECK(initial_quantity_tons>0),
 current_quantity_tons numeric NOT NULL CHECK(current_quantity_tons>=0 AND current_quantity_tons<=initial_quantity_tons),
 custody_status text NOT NULL DEFAULT 'aboard' CHECK(custody_status IN('aboard','depleted','unloaded','destroyed')),
 concurrency_version bigint NOT NULL DEFAULT 1 CHECK(concurrency_version>0),
 loaded_at timestamptz NOT NULL DEFAULT clock_timestamp(),ended_at timestamptz,
 source_command_id bigint REFERENCES cmd_command(command_id),
 UNIQUE(ship_id,lot_identifier),UNIQUE(ship_cargo_lot_id,ship_id,campaign_id),
 FOREIGN KEY(ship_id,campaign_id) REFERENCES ship_ship(ship_id,campaign_id),
 CHECK((custody_status='aboard')=(current_quantity_tons>0)),
 CHECK((custody_status='aboard')=(ended_at IS NULL))
);

CREATE FUNCTION ship_validate_cargo_capacity() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE capacity numeric; loaded numeric;
BEGIN
 SELECT class.cargo_capacity_tons INTO STRICT capacity FROM ship_ship ship JOIN ship_class class USING(ship_class_rule_id)
 WHERE ship.ship_id=NEW.ship_id AND ship.campaign_id=NEW.campaign_id;
 SELECT coalesce(sum(current_quantity_tons),0) INTO loaded FROM ship_cargo_lot
 WHERE ship_id=NEW.ship_id AND custody_status='aboard' AND ship_cargo_lot_id<>coalesce(NEW.ship_cargo_lot_id,0);
 IF NEW.custody_status='aboard' THEN loaded:=loaded+NEW.current_quantity_tons; END IF;
 IF loaded>capacity THEN RAISE EXCEPTION 'Ship cargo exceeds authoritative hold capacity' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER ship_cargo_capacity_valid BEFORE INSERT OR UPDATE ON ship_cargo_lot
FOR EACH ROW EXECUTE FUNCTION ship_validate_cargo_capacity();

ALTER TABLE ship_resource_movement DROP CONSTRAINT ship_resource_movement_movement_kind_check,
 ADD CONSTRAINT ship_resource_movement_movement_kind_check CHECK(movement_kind IN(
  'load','consume','dump','transfer','production','correction','initial','damage'));

CREATE TABLE senc_ship_fuel_leak_state(
 ship_id bigint PRIMARY KEY,campaign_id bigint NOT NULL,
 leak_rate_tons_per_hour numeric NOT NULL CHECK(leak_rate_tons_per_hour>0),
 leak_status text NOT NULL DEFAULT 'active' CHECK(leak_status IN('active','sealed','tank-destroyed')),
 source_damage_location_hit_receipt_id bigint NOT NULL UNIQUE REFERENCES senc_damage_location_hit_receipt(damage_location_hit_receipt_id),
 concurrency_version bigint NOT NULL DEFAULT 1 CHECK(concurrency_version>0),updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(ship_id,campaign_id) REFERENCES ship_ship(ship_id,campaign_id)
);

CREATE TABLE senc_storage_damage_attempt(
 damage_location_hit_receipt_id bigint PRIMARY KEY REFERENCES senc_damage_location_hit_receipt(damage_location_hit_receipt_id),
 ship_id bigint NOT NULL,campaign_id bigint NOT NULL,location_code text NOT NULL CHECK(location_code IN('fuel','hold')),
 effect_code text NOT NULL,stored_quantity_snapshot numeric NOT NULL CHECK(stored_quantity_snapshot>=0),
 ship_version_snapshot bigint NOT NULL CHECK(ship_version_snapshot>0),declared_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(ship_id,campaign_id) REFERENCES ship_ship(ship_id,campaign_id)
);
CREATE FUNCTION senc_validate_storage_damage_attempt() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE hit senc_damage_location_hit_receipt%ROWTYPE; actual numeric; version bigint;
BEGIN
 SELECT * INTO STRICT hit FROM senc_damage_location_hit_receipt WHERE damage_location_hit_receipt_id=NEW.damage_location_hit_receipt_id;
 IF hit.target_ship_id<>NEW.ship_id OR hit.campaign_id<>NEW.campaign_id OR hit.applied_location<>NEW.location_code
  OR hit.effect_code<>NEW.effect_code OR hit.effect_code NOT IN('minor-leak-1d6-tons-hour','destroy-1d6-times-10-percent','tank-destroyed','hold-and-contents-destroyed') THEN
  RAISE EXCEPTION 'Storage damage attempt must match an unresolved Fuel or Hold hit' USING ERRCODE='23514'; END IF;
 SELECT concurrency_version INTO STRICT version FROM ship_ship WHERE ship_id=NEW.ship_id AND campaign_id=NEW.campaign_id;
 IF NEW.location_code='fuel' THEN SELECT coalesce(sum(current_quantity),0) INTO actual FROM ship_resource
  WHERE ship_id=NEW.ship_id AND resource_type_code IN('refined_fuel','unrefined_fuel');
 ELSE SELECT coalesce(sum(current_quantity_tons),0) INTO actual FROM ship_cargo_lot WHERE ship_id=NEW.ship_id AND custody_status='aboard'; END IF;
 IF NEW.stored_quantity_snapshot<>actual OR NEW.ship_version_snapshot<>version THEN
  RAISE EXCEPTION 'Storage damage snapshot is not current' USING ERRCODE='40001'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER senc_storage_damage_attempt_valid BEFORE INSERT ON senc_storage_damage_attempt
FOR EACH ROW EXECUTE FUNCTION senc_validate_storage_damage_attempt();

CREATE TABLE senc_storage_damage_die(
 damage_location_hit_receipt_id bigint PRIMARY KEY REFERENCES senc_storage_damage_attempt(damage_location_hit_receipt_id),
 die_result smallint NOT NULL CHECK(die_result BETWEEN 1 AND 6),recorded_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE senc_storage_damage_final_receipt(
 damage_location_hit_receipt_id bigint PRIMARY KEY REFERENCES senc_storage_damage_attempt(damage_location_hit_receipt_id),
 die_result smallint,loss_percent smallint CHECK(loss_percent BETWEEN 10 AND 60),
 leak_rate_tons_per_hour numeric CHECK(leak_rate_tons_per_hour BETWEEN 1 AND 6),
 quantity_before numeric NOT NULL CHECK(quantity_before>=0),quantity_lost numeric NOT NULL CHECK(quantity_lost>=0 AND quantity_lost<=quantity_before),
 quantity_after numeric NOT NULL CHECK(quantity_after=quantity_before-quantity_lost),
 ship_version_before bigint NOT NULL,ship_version_after bigint NOT NULL CHECK(ship_version_after=ship_version_before+1),
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE senc_storage_damage_allocation_receipt(
 storage_damage_allocation_receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 damage_location_hit_receipt_id bigint NOT NULL REFERENCES senc_storage_damage_final_receipt(damage_location_hit_receipt_id),
 allocation_kind text NOT NULL CHECK(allocation_kind IN('fuel-resource','cargo-lot')),
 resource_type_code text,ship_cargo_lot_id bigint REFERENCES ship_cargo_lot(ship_cargo_lot_id),
 quantity_before numeric NOT NULL CHECK(quantity_before>0),quantity_lost numeric NOT NULL CHECK(quantity_lost>0 AND quantity_lost<=quantity_before),
 quantity_after numeric NOT NULL CHECK(quantity_after=quantity_before-quantity_lost),
 CHECK((resource_type_code IS NOT NULL)::integer+(ship_cargo_lot_id IS NOT NULL)::integer=1),
 UNIQUE(damage_location_hit_receipt_id,resource_type_code),UNIQUE(damage_location_hit_receipt_id,ship_cargo_lot_id)
);

CREATE FUNCTION senc_apply_storage_damage() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE attempt senc_storage_damage_attempt%ROWTYPE; die smallint; ship_version bigint; expected_percent smallint;
 expected_leak numeric; expected_loss numeric; row_record record;
BEGIN
 SELECT * INTO STRICT attempt FROM senc_storage_damage_attempt WHERE damage_location_hit_receipt_id=NEW.damage_location_hit_receipt_id FOR UPDATE;
 SELECT die_result INTO die FROM senc_storage_damage_die WHERE damage_location_hit_receipt_id=NEW.damage_location_hit_receipt_id;
 IF attempt.effect_code IN('minor-leak-1d6-tons-hour','destroy-1d6-times-10-percent') AND die IS NULL THEN
  RAISE EXCEPTION 'Fuel and Hold variable consequences require exactly one D6' USING ERRCODE='23514'; END IF;
 IF attempt.effect_code IN('tank-destroyed','hold-and-contents-destroyed') AND die IS NOT NULL THEN
  RAISE EXCEPTION 'Destroyed storage consequences do not roll a die' USING ERRCODE='23514'; END IF;
 SELECT concurrency_version INTO STRICT ship_version FROM ship_ship WHERE ship_id=attempt.ship_id AND campaign_id=attempt.campaign_id FOR UPDATE;
 IF ship_version<>attempt.ship_version_snapshot THEN RAISE EXCEPTION 'Ship changed after storage damage snapshot' USING ERRCODE='40001'; END IF;
 expected_percent:=CASE WHEN attempt.effect_code='destroy-1d6-times-10-percent' THEN die*10 END;
 expected_leak:=CASE WHEN attempt.effect_code='minor-leak-1d6-tons-hour' THEN die END;
 expected_loss:=CASE WHEN attempt.effect_code IN('tank-destroyed','hold-and-contents-destroyed') THEN attempt.stored_quantity_snapshot
                     WHEN expected_percent IS NOT NULL THEN attempt.stored_quantity_snapshot*expected_percent/100 ELSE 0 END;
 IF NEW.die_result IS DISTINCT FROM die OR NEW.loss_percent IS DISTINCT FROM expected_percent
  OR NEW.leak_rate_tons_per_hour IS DISTINCT FROM expected_leak OR NEW.quantity_before<>attempt.stored_quantity_snapshot
  OR NEW.quantity_lost<>expected_loss OR NEW.quantity_after<>attempt.stored_quantity_snapshot-expected_loss
  OR NEW.ship_version_before<>ship_version OR NEW.ship_version_after<>ship_version+1 THEN
  RAISE EXCEPTION 'Storage damage final receipt does not match authoritative consequence' USING ERRCODE='23514'; END IF;

 IF attempt.location_code='fuel' AND expected_loss>0 AND attempt.stored_quantity_snapshot>0 THEN
  FOR row_record IN SELECT resource_type_code,current_quantity FROM ship_resource WHERE ship_id=attempt.ship_id
   AND resource_type_code IN('refined_fuel','unrefined_fuel') AND current_quantity>0 ORDER BY resource_type_code FOR UPDATE LOOP
   INSERT INTO senc_storage_damage_allocation_receipt(damage_location_hit_receipt_id,allocation_kind,resource_type_code,quantity_before,quantity_lost,quantity_after)
   VALUES(NEW.damage_location_hit_receipt_id,'fuel-resource',row_record.resource_type_code,row_record.current_quantity,
    row_record.current_quantity*expected_loss/attempt.stored_quantity_snapshot,row_record.current_quantity-row_record.current_quantity*expected_loss/attempt.stored_quantity_snapshot);
   INSERT INTO ship_resource_movement(ship_id,campaign_id,resource_type_code,quantity_delta,balance_after,movement_kind)
   VALUES(attempt.ship_id,attempt.campaign_id,row_record.resource_type_code,-row_record.current_quantity*expected_loss/attempt.stored_quantity_snapshot,0,'damage');
  END LOOP;
 ELSIF attempt.location_code='hold' AND expected_loss>0 AND attempt.stored_quantity_snapshot>0 THEN
  FOR row_record IN SELECT * FROM ship_cargo_lot WHERE ship_id=attempt.ship_id AND custody_status='aboard' ORDER BY ship_cargo_lot_id FOR UPDATE LOOP
   INSERT INTO senc_storage_damage_allocation_receipt(damage_location_hit_receipt_id,allocation_kind,ship_cargo_lot_id,quantity_before,quantity_lost,quantity_after)
   VALUES(NEW.damage_location_hit_receipt_id,'cargo-lot',row_record.ship_cargo_lot_id,row_record.current_quantity_tons,
    row_record.current_quantity_tons*expected_loss/attempt.stored_quantity_snapshot,row_record.current_quantity_tons-row_record.current_quantity_tons*expected_loss/attempt.stored_quantity_snapshot);
   UPDATE ship_cargo_lot SET current_quantity_tons=current_quantity_tons-current_quantity_tons*expected_loss/attempt.stored_quantity_snapshot,
    custody_status=CASE WHEN current_quantity_tons-current_quantity_tons*expected_loss/attempt.stored_quantity_snapshot=0 THEN 'destroyed' ELSE 'aboard' END,
    ended_at=CASE WHEN current_quantity_tons-current_quantity_tons*expected_loss/attempt.stored_quantity_snapshot=0 THEN clock_timestamp() ELSE NULL END,
    concurrency_version=concurrency_version+1 WHERE ship_cargo_lot_id=row_record.ship_cargo_lot_id;
  END LOOP;
 END IF;
 IF expected_leak IS NOT NULL THEN
  INSERT INTO senc_ship_fuel_leak_state(ship_id,campaign_id,leak_rate_tons_per_hour,source_damage_location_hit_receipt_id)
  VALUES(attempt.ship_id,attempt.campaign_id,expected_leak,NEW.damage_location_hit_receipt_id);
 ELSIF attempt.effect_code='tank-destroyed' THEN
  UPDATE senc_ship_fuel_leak_state SET leak_status='tank-destroyed',concurrency_version=concurrency_version+1,updated_at=clock_timestamp()
  WHERE ship_id=attempt.ship_id AND leak_status='active';
 END IF;
 UPDATE ship_ship SET concurrency_version=concurrency_version+1 WHERE ship_id=attempt.ship_id;
 RETURN NEW;
END $$;
CREATE TRIGGER senc_storage_damage_final_apply BEFORE INSERT ON senc_storage_damage_final_receipt
FOR EACH ROW EXECUTE FUNCTION senc_apply_storage_damage();

CREATE FUNCTION senc_reject_storage_damage_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Storage damage state, dice, allocations, and receipts are immutable'; END $$;
CREATE TRIGGER senc_storage_damage_attempt_immutable BEFORE UPDATE OR DELETE ON senc_storage_damage_attempt FOR EACH ROW EXECUTE FUNCTION senc_reject_storage_damage_mutation();
CREATE TRIGGER senc_storage_damage_die_immutable BEFORE UPDATE OR DELETE ON senc_storage_damage_die FOR EACH ROW EXECUTE FUNCTION senc_reject_storage_damage_mutation();
CREATE TRIGGER senc_storage_damage_final_immutable BEFORE UPDATE OR DELETE ON senc_storage_damage_final_receipt FOR EACH ROW EXECUTE FUNCTION senc_reject_storage_damage_mutation();
CREATE TRIGGER senc_storage_damage_allocation_immutable BEFORE UPDATE OR DELETE ON senc_storage_damage_allocation_receipt FOR EACH ROW EXECUTE FUNCTION senc_reject_storage_damage_mutation();

DO $$ DECLARE definition text; BEGIN
 definition:=pg_get_functiondef('senc_apply_next_damage_location_hit(bigint,smallint)'::regprocedure);
 definition:=replace(definition,
  $old$'destroy-1d6-times-10-percent'::text]$old$,
  $new$'destroy-1d6-times-10-percent'::text, 'tank-destroyed'::text, 'hold-and-contents-destroyed'::text]$new$);
 EXECUTE definition;
END $$;

CREATE OR REPLACE FUNCTION senc_finalize_mount_damage_application() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE expected integer; applied integer; required integer; resolved integer; target record;
BEGIN
 SELECT sum(hit_multiplicity) INTO expected FROM senc_damage_location_group_roll WHERE mount_attack_declaration_id=NEW.mount_attack_declaration_id;
 SELECT count(*),count(*) FILTER(WHERE secondary_resolution_required) INTO applied,required FROM senc_damage_location_hit_receipt WHERE mount_attack_declaration_id=NEW.mount_attack_declaration_id;
 SELECT count(*) INTO resolved FROM senc_damage_location_hit_receipt hit
 LEFT JOIN senc_crew_damage_application_receipt crew ON crew.damage_location_hit_receipt_id=hit.damage_location_hit_receipt_id
 LEFT JOIN senc_storage_damage_final_receipt storage ON storage.damage_location_hit_receipt_id=hit.damage_location_hit_receipt_id
 WHERE hit.mount_attack_declaration_id=NEW.mount_attack_declaration_id AND hit.secondary_resolution_required
  AND ((hit.effect_code IN('roll-crew-damage','crew-normal-hit','crew-radiation-hit') AND crew.damage_location_hit_receipt_id IS NOT NULL)
    OR (hit.effect_code IN('minor-leak-1d6-tons-hour','destroy-1d6-times-10-percent','tank-destroyed','hold-and-contents-destroyed') AND storage.damage_location_hit_receipt_id IS NOT NULL));
 SELECT ship.ship_id,ship.campaign_id,ship.concurrency_version INTO STRICT target FROM senc_mount_attack_declaration declaration
 JOIN senc_vessel vessel ON vessel.senc_vessel_id=declaration.target_vessel_id JOIN ship_ship ship ON ship.ship_id=vessel.ship_id
 WHERE declaration.mount_attack_declaration_id=NEW.mount_attack_declaration_id FOR UPDATE OF ship;
 IF NEW.expected_hit_count<>expected OR NEW.applied_hit_count<>applied OR applied<>expected OR NEW.required_secondary_count<>required
  OR NEW.resolved_secondary_count<>resolved OR resolved<>required OR NEW.target_ship_id<>target.ship_id OR NEW.campaign_id<>target.campaign_id
  OR NEW.target_ship_version_after<>target.concurrency_version THEN
  RAISE EXCEPTION 'Mount damage application requires every ordered hit and secondary consequence' USING ERRCODE='23514'; END IF;
 UPDATE senc_mount_damage_final_receipt SET damage_status='applied' WHERE mount_attack_declaration_id=NEW.mount_attack_declaration_id;
 RETURN NEW;
END $$;
