ALTER TABLE health_deprivation_recovery_lock DROP CONSTRAINT health_deprivation_recovery_l_deprivation_check_receipt_id_fkey,
 ADD CONSTRAINT health_deprivation_lock_check_fk FOREIGN KEY(deprivation_check_receipt_id) REFERENCES env_deprivation_check_receipt(deprivation_check_receipt_id) DEFERRABLE INITIALLY DEFERRED;
CREATE FUNCTION health_enforce_deprivation_recovery_lock() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE actor bigint;missing integer;locked integer;
BEGIN IF NEW.point_change<0 THEN RETURN NEW;END IF;
 IF TG_TABLE_NAME='cmd_personal_natural_healing_allocation' THEN SELECT receipt.actor_id INTO STRICT actor FROM cmd_personal_natural_healing_receipt receipt WHERE receipt.command_id=NEW.command_id;
 ELSE SELECT receipt.patient_actor_id INTO STRICT actor FROM cmd_personal_medical_treatment_receipt receipt WHERE receipt.command_id=NEW.command_id;END IF;
 SELECT maximum_value-current_value INTO STRICT missing FROM actor_characteristic WHERE actor_id=actor AND characteristic_rule_id=NEW.characteristic_rule_id;
 SELECT coalesce(sum(allocation.allocated_damage),0) INTO locked FROM health_deprivation_recovery_lock lock JOIN health_damage_allocation allocation USING(damage_instance_id)
 WHERE lock.released_at IS NULL AND allocation.characteristic_rule_id=NEW.characteristic_rule_id;
 IF NEW.point_change>greatest(0,missing-locked) THEN RAISE EXCEPTION 'Healing cannot recover deprivation damage until the actor receives the required food or water' USING ERRCODE='23514';END IF;RETURN NEW;END $$;
CREATE TRIGGER cmd_natural_healing_deprivation_lock BEFORE INSERT ON cmd_personal_natural_healing_allocation FOR EACH ROW EXECUTE FUNCTION health_enforce_deprivation_recovery_lock();
CREATE TRIGGER cmd_medical_healing_deprivation_lock BEFORE INSERT ON cmd_personal_medical_treatment_allocation FOR EACH ROW EXECUTE FUNCTION health_enforce_deprivation_recovery_lock();
