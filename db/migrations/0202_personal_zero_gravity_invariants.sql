CREATE FUNCTION cmd_validate_zero_gravity_receipt()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE attack enc_personal_attack%ROWTYPE;
DECLARE resolved cmd_attack_receipt%ROWTYPE;
BEGIN
 SELECT * INTO STRICT attack FROM enc_personal_attack
  WHERE personal_attack_id=NEW.personal_attack_id;
 SELECT * INTO STRICT resolved FROM cmd_attack_receipt
  WHERE command_id=NEW.command_id;
 IF NOT attack.zero_gravity
    OR resolved.personal_attack_id<>attack.personal_attack_id
    OR ROW(NEW.weapon_skill_level,NEW.zero_g_trained,NEW.zero_g_skill_level,
           NEW.effective_skill_level,NEW.weapon_has_recoil,NEW.recoil_modifier)
       IS DISTINCT FROM
       ROW(attack.zero_gravity_weapon_skill_level,
           attack.zero_gravity_trained,attack.zero_gravity_skill_level,
           attack.zero_gravity_effective_skill_level,
           attack.zero_gravity_weapon_has_recoil,
           attack.zero_gravity_recoil_modifier)
    OR resolved.skill_modifier<>NEW.effective_skill_level THEN
   RAISE EXCEPTION 'Zero-gravity receipt does not match frozen attack facts';
 END IF;
 RETURN NEW;
END;
$$;
CREATE TRIGGER cmd_personal_zero_gravity_receipt_validate
BEFORE INSERT ON cmd_personal_zero_gravity_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_validate_zero_gravity_receipt();

CREATE FUNCTION enc_guard_zero_gravity_attack_snapshot()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF ROW(NEW.zero_gravity,NEW.zero_gravity_weapon_skill_level,
        NEW.zero_gravity_trained,NEW.zero_gravity_skill_level,
        NEW.zero_gravity_effective_skill_level,
        NEW.zero_gravity_weapon_has_recoil,
        NEW.zero_gravity_recoil_modifier)
    IS DISTINCT FROM
    ROW(OLD.zero_gravity,OLD.zero_gravity_weapon_skill_level,
        OLD.zero_gravity_trained,OLD.zero_gravity_skill_level,
        OLD.zero_gravity_effective_skill_level,
        OLD.zero_gravity_weapon_has_recoil,
        OLD.zero_gravity_recoil_modifier) THEN
   RAISE EXCEPTION 'Zero-gravity attack snapshots are immutable';
 END IF;
 RETURN NEW;
END;
$$;
CREATE TRIGGER enc_personal_attack_zero_gravity_snapshot_immutable
BEFORE UPDATE ON enc_personal_attack
FOR EACH ROW EXECUTE FUNCTION enc_guard_zero_gravity_attack_snapshot();
