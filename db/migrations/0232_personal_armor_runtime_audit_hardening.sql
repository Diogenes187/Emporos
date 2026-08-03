CREATE FUNCTION inv_audit_armor_state_update()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS (
   SELECT 1 FROM cmd_personal_armor_usage_receipt receipt
   WHERE receipt.item_instance_id=NEW.item_instance_id
     AND receipt.state_version_before=OLD.concurrency_version
     AND receipt.state_version_after=NEW.concurrency_version
     AND receipt.laser_rating_before=OLD.current_laser_armor_rating
     AND receipt.laser_rating_after=NEW.current_laser_armor_rating
     AND receipt.life_support_before
         IS NOT DISTINCT FROM OLD.life_support_seconds_remaining
     AND receipt.life_support_after
         IS NOT DISTINCT FROM NEW.life_support_seconds_remaining
 ) THEN RAISE EXCEPTION 'Armor state update lacks an immutable usage receipt';
 END IF;
 RETURN NULL;
END;
$$;
CREATE CONSTRAINT TRIGGER inv_armor_state_update_audit
AFTER UPDATE ON inv_armor_instance_state
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION inv_audit_armor_state_update();

CREATE FUNCTION inv_audit_actor_armor_layers()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE affected_actor bigint;
DECLARE latest_command bigint;
DECLARE expected_count integer;
BEGIN
 affected_actor := COALESCE(NEW.actor_id,OLD.actor_id);
 SELECT command_id,layer_count_after
   INTO latest_command,expected_count
   FROM cmd_personal_armor_equip_receipt
  WHERE actor_id=affected_actor
  ORDER BY command_id DESC LIMIT 1;
 IF latest_command IS NULL
    OR expected_count<>(
      SELECT count(*) FROM inv_actor_armor_layer
      WHERE actor_id=affected_actor)
    OR EXISTS (
      (SELECT item_instance_id,layer_order
         FROM inv_actor_armor_layer WHERE actor_id=affected_actor
       EXCEPT
       SELECT item_instance_id,layer_order
         FROM cmd_personal_armor_layer_receipt
        WHERE command_id=latest_command)
      UNION ALL
      (SELECT item_instance_id,layer_order
         FROM cmd_personal_armor_layer_receipt
        WHERE command_id=latest_command
       EXCEPT
       SELECT item_instance_id,layer_order
         FROM inv_actor_armor_layer WHERE actor_id=affected_actor)
    )
 THEN RAISE EXCEPTION 'Armor layers lack a matching immutable receipt';
 END IF;
 RETURN NULL;
END;
$$;
CREATE CONSTRAINT TRIGGER inv_actor_armor_layer_audit
AFTER INSERT OR UPDATE OR DELETE ON inv_actor_armor_layer
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION inv_audit_actor_armor_layers();

CREATE FUNCTION inv_reject_equipped_armor_custody_change()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE affected_item bigint;
BEGIN
 affected_item := COALESCE(NEW.item_instance_id,OLD.item_instance_id);
 IF EXISTS (
   SELECT 1 FROM inv_actor_armor_layer
   WHERE item_instance_id=affected_item
 ) THEN RAISE EXCEPTION
   'Equipped armor must be unequipped before ownership or status changes';
 END IF;
 IF TG_OP='DELETE' THEN RETURN OLD; END IF;
 RETURN NEW;
END;
$$;
CREATE TRIGGER inv_equipped_armor_owner_guard
BEFORE UPDATE OR DELETE ON inv_item_owner
FOR EACH ROW EXECUTE FUNCTION inv_reject_equipped_armor_custody_change();
CREATE TRIGGER inv_equipped_armor_status_guard
BEFORE UPDATE OF item_status ON inv_item_instance
FOR EACH ROW
WHEN (NEW.item_status IS DISTINCT FROM OLD.item_status)
EXECUTE FUNCTION inv_reject_equipped_armor_custody_change();
