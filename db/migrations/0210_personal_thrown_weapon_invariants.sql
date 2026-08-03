CREATE FUNCTION enc_validate_thrown_delivery_snapshot()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.attack_profile_code='thrown' AND NOT EXISTS (
   SELECT 1 FROM inv_thrown_delivery_capability capability
    WHERE capability.item_rule_id=NEW.weapon_rule_id
      AND capability.attack_profile_code=NEW.attack_profile_code
      AND capability.delivery_type=NEW.thrown_delivery_type
 ) THEN
   RAISE EXCEPTION 'Thrown attack lacks matching delivery capability';
 END IF;
 RETURN NEW;
END;
$$;
CREATE TRIGGER enc_personal_attack_thrown_delivery_validate
BEFORE INSERT ON enc_personal_attack
FOR EACH ROW EXECUTE FUNCTION enc_validate_thrown_delivery_snapshot();

CREATE FUNCTION enc_guard_thrown_attack_snapshot()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF ROW(NEW.thrown_delivery_type,NEW.thrown_target_point_reference)
    IS DISTINCT FROM
    ROW(OLD.thrown_delivery_type,OLD.thrown_target_point_reference) THEN
   RAISE EXCEPTION 'Thrown-delivery attack snapshots are immutable';
 END IF;
 RETURN NEW;
END;
$$;
CREATE TRIGGER enc_personal_attack_thrown_snapshot_immutable
BEFORE UPDATE ON enc_personal_attack
FOR EACH ROW EXECUTE FUNCTION enc_guard_thrown_attack_snapshot();

CREATE FUNCTION cmd_validate_thrown_weapon_receipt()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE attack enc_personal_attack%ROWTYPE;
DECLARE resolved cmd_attack_receipt%ROWTYPE;
DECLARE draw cmd_random_draw%ROWTYPE;
BEGIN
 SELECT * INTO STRICT attack FROM enc_personal_attack
  WHERE personal_attack_id=NEW.personal_attack_id;
 SELECT * INTO STRICT resolved FROM cmd_attack_receipt
  WHERE command_id=NEW.command_id;
 IF NEW.scatter_direction_draw IS NOT NULL THEN
   SELECT * INTO STRICT draw FROM cmd_random_draw
    WHERE command_id=NEW.command_id
      AND draw_group='thrown_scatter_direction' AND draw_order=1;
 END IF;
 IF resolved.personal_attack_id<>attack.personal_attack_id
    OR attack.attack_profile_code<>'thrown'
    OR NEW.delivery_type<>attack.thrown_delivery_type
    OR NEW.target_point_reference<>attack.thrown_target_point_reference
    OR NEW.attack_hit<>resolved.hit
    OR NEW.original_effect<>resolved.effect
    OR (NEW.attack_hit AND NEW.scatter_distance_metres<>0)
    OR (
      NOT NEW.attack_hit
      AND NEW.scatter_distance_metres<>greatest(0,6+resolved.effect)
    )
    OR (
      NEW.scatter_direction_draw IS NOT NULL
      AND (
        draw.die_sides<>360
        OR draw.result<>NEW.scatter_direction_draw
      )
    )
    OR (
      NEW.delivery_type='payload'
      AND (
        resolved.raw_damage<>0 OR resolved.penetrating_damage<>0
        OR resolved.rolled_damage<>0 OR resolved.effect_damage<>0
      )
    )
    OR (
      NEW.delivery_type='impact' AND NOT NEW.attack_hit
      AND (resolved.raw_damage<>0 OR resolved.penetrating_damage<>0)
    )
 THEN
   RAISE EXCEPTION 'Thrown-weapon receipt does not match frozen attack facts';
 END IF;
 RETURN NEW;
END;
$$;
CREATE TRIGGER cmd_personal_thrown_weapon_receipt_validate
BEFORE INSERT ON cmd_personal_thrown_weapon_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_validate_thrown_weapon_receipt();

CREATE FUNCTION cmd_validate_thrown_payload_link()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE delivery cmd_personal_thrown_weapon_receipt%ROWTYPE;
DECLARE payload cmd_command%ROWTYPE;
BEGIN
 SELECT * INTO STRICT delivery FROM cmd_personal_thrown_weapon_receipt
  WHERE command_id=NEW.delivery_attack_command_id;
 SELECT * INTO STRICT payload FROM cmd_command
  WHERE command_id=NEW.payload_command_id;
 IF delivery.delivery_type<>'payload'
    OR NEW.payload_command_id=NEW.delivery_attack_command_id
    OR payload.command_status<>'completed'
    OR ROW(NEW.target_point_reference,NEW.scatter_bearing_degrees,
           NEW.scatter_distance_metres)
       IS DISTINCT FROM
       ROW(delivery.target_point_reference,
           delivery.scatter_bearing_degrees,
           delivery.scatter_distance_metres)
 THEN
   RAISE EXCEPTION 'Payload link does not match thrown delivery receipt';
 END IF;
 RETURN NEW;
END;
$$;
CREATE TRIGGER cmd_personal_thrown_payload_link_validate
BEFORE INSERT ON cmd_personal_thrown_payload_link
FOR EACH ROW EXECUTE FUNCTION cmd_validate_thrown_payload_link();
