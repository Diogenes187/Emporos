CREATE FUNCTION inv_validate_armor_instance_state()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE expected_laser integer;
DECLARE expected_life integer;
BEGIN
 SELECT COALESCE(armor.laser_armor_rating,armor.general_armor_rating),
        support.duration_seconds
   INTO expected_laser,expected_life
   FROM inv_item_instance item
   JOIN inv_armor_definition armor
     ON armor.item_rule_id=item.item_rule_id
   LEFT JOIN rule_armor_life_support support
     ON support.armor_rule_id=item.item_rule_id
  WHERE item.item_instance_id=NEW.item_instance_id
    AND item.campaign_id=NEW.campaign_id AND item.item_status='active';
 IF expected_laser IS NULL
    OR (TG_OP='INSERT' AND (
        NEW.current_laser_armor_rating<>expected_laser
        OR NEW.life_support_seconds_remaining
           IS DISTINCT FROM expected_life
        OR NEW.concurrency_version<>1)) THEN
   RAISE EXCEPTION 'Armor instance state does not match active item definition';
 END IF;
 RETURN NEW;
END;
$$;
CREATE TRIGGER inv_armor_instance_state_valid
BEFORE INSERT OR UPDATE ON inv_armor_instance_state
FOR EACH ROW EXECUTE FUNCTION inv_validate_armor_instance_state();

CREATE FUNCTION inv_validate_actor_armor_layers()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE layer_count integer;
DECLARE reflec_count integer;
DECLARE expected_orders integer;
DECLARE affected_actor bigint;
BEGIN
 affected_actor := COALESCE(NEW.actor_id,OLD.actor_id);
 SELECT count(*),count(*) FILTER (
          WHERE exception.armor_rule_id IS NOT NULL),
        count(DISTINCT layer.layer_order)
   INTO layer_count,reflec_count,expected_orders
   FROM inv_actor_armor_layer layer
   JOIN inv_item_instance item
     ON item.item_instance_id=layer.item_instance_id
   LEFT JOIN rule_armor_layer_exception exception
     ON exception.armor_rule_id=item.item_rule_id
  WHERE layer.actor_id=affected_actor;
 IF layer_count NOT BETWEEN 0 AND 2
    OR expected_orders<>layer_count
    OR (layer_count=2 AND reflec_count<>1)
    OR EXISTS (
      SELECT 1 FROM generate_series(1,layer_count) required(order_number)
      WHERE NOT EXISTS (
        SELECT 1 FROM inv_actor_armor_layer actual
        WHERE actual.actor_id=affected_actor
          AND actual.layer_order=required.order_number))
    OR EXISTS (
      SELECT 1 FROM inv_actor_armor_layer layer
      JOIN inv_item_owner owner USING (item_instance_id,campaign_id)
      JOIN inv_item_instance item USING (item_instance_id,campaign_id)
      WHERE layer.actor_id=affected_actor
        AND (owner.actor_id<>affected_actor OR item.item_status<>'active'))
 THEN RAISE EXCEPTION 'Personal armor layer state is invalid';
 END IF;
 RETURN NULL;
END;
$$;
CREATE CONSTRAINT TRIGGER inv_actor_armor_layers_valid
AFTER INSERT OR UPDATE OR DELETE ON inv_actor_armor_layer
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION inv_validate_actor_armor_layers();

CREATE FUNCTION cmd_reject_personal_armor_history_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Personal armor command history is immutable'; END;
$$;
CREATE TRIGGER cmd_personal_armor_equip_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_armor_equip_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_personal_armor_history_mutation();
CREATE TRIGGER cmd_personal_armor_layer_receipt_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_armor_layer_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_personal_armor_history_mutation();
CREATE TRIGGER cmd_personal_armor_usage_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_armor_usage_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_personal_armor_history_mutation();

CREATE FUNCTION cmd_validate_personal_armor_usage()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE loss integer;
DECLARE state inv_armor_instance_state%ROWTYPE;
BEGIN
 SELECT COALESCE(degradation.armor_rating_loss_per_hit,0)
   INTO loss
   FROM inv_item_instance item
   LEFT JOIN rule_armor_degradation degradation
     ON degradation.armor_rule_id=item.item_rule_id
    AND degradation.damage_type='laser'
  WHERE item.item_instance_id=NEW.item_instance_id;
 SELECT * INTO STRICT state FROM inv_armor_instance_state
  WHERE item_instance_id=NEW.item_instance_id;
 IF NEW.laser_rating_after<>
      greatest(NEW.laser_rating_before-NEW.laser_hits*loss,0)
    OR state.current_laser_armor_rating<>NEW.laser_rating_after
    OR state.life_support_seconds_remaining
       IS DISTINCT FROM NEW.life_support_after
    OR state.concurrency_version<>NEW.state_version_after
 THEN RAISE EXCEPTION 'Armor usage receipt fails state recomputation';
 END IF;
 RETURN NULL;
END;
$$;
CREATE CONSTRAINT TRIGGER cmd_personal_armor_usage_audit
AFTER INSERT ON cmd_personal_armor_usage_receipt
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION cmd_validate_personal_armor_usage();
