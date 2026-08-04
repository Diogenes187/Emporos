CREATE TRIGGER cmd_attack_armor_layer_immutable
BEFORE UPDATE OR DELETE ON cmd_attack_armor_layer_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_personal_armor_history_mutation();

CREATE FUNCTION cmd_validate_attack_armor_layers()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE receipt cmd_attack_receipt%ROWTYPE;
DECLARE layer_count integer;
DECLARE rating_total integer;
DECLARE first_damage integer;
DECLARE last_damage integer;
BEGIN
 SELECT * INTO STRICT receipt FROM cmd_attack_receipt
 WHERE command_id=NEW.command_id;
 SELECT count(*),sum(applicable_armor_rating),
        max(damage_before) FILTER(WHERE layer_order=1),
        max(damage_after) FILTER(WHERE layer_order=(
          SELECT max(last_layer.layer_order)
          FROM cmd_attack_armor_layer_receipt last_layer
          WHERE last_layer.command_id=NEW.command_id))
 INTO layer_count,rating_total,first_damage,last_damage
 FROM cmd_attack_armor_layer_receipt
 WHERE command_id=NEW.command_id;
 IF first_damage<>receipt.raw_damage
    OR receipt.armor_rating<>rating_total+receipt.natural_armor_rating
    OR last_damage<>greatest(receipt.raw_damage-rating_total,0)
    OR EXISTS(
      SELECT 1 FROM generate_series(1,layer_count) required(layer_order)
      WHERE NOT EXISTS(
        SELECT 1 FROM cmd_attack_armor_layer_receipt actual
        WHERE actual.command_id=NEW.command_id
          AND actual.layer_order=required.layer_order))
 THEN RAISE EXCEPTION 'Attack armor layers fail outside-in recomputation';
 END IF;
 RETURN NULL;
END;
$$;

CREATE CONSTRAINT TRIGGER cmd_attack_armor_layer_audit
AFTER INSERT ON cmd_attack_armor_layer_receipt
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION cmd_validate_attack_armor_layers();
