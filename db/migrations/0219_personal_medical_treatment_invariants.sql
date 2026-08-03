CREATE FUNCTION cmd_reject_medical_treatment_history_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Medical-treatment history is immutable'; END;
$$;
CREATE TRIGGER cmd_personal_medical_treatment_receipt_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_medical_treatment_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_medical_treatment_history_mutation();
CREATE TRIGGER cmd_personal_medical_treatment_allocation_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_medical_treatment_allocation
FOR EACH ROW EXECUTE FUNCTION cmd_reject_medical_treatment_history_mutation();
CREATE TRIGGER cmd_personal_first_aid_link_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_first_aid_link
FOR EACH ROW EXECUTE FUNCTION cmd_reject_medical_treatment_history_mutation();
CREATE TRIGGER cmd_personal_surgery_link_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_surgery_link
FOR EACH ROW EXECUTE FUNCTION cmd_reject_medical_treatment_history_mutation();
CREATE TRIGGER cmd_personal_medical_care_link_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_medical_care_link
FOR EACH ROW EXECUTE FUNCTION cmd_reject_medical_treatment_history_mutation();

CREATE FUNCTION cmd_validate_medical_treatment_receipt()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE allocated integer;
DECLARE physical_count integer;
DECLARE draw_count integer;
DECLARE draw_total integer;
BEGIN
 SELECT COALESCE(sum(abs(allocation.point_change)),0),
        count(*) FILTER (
          WHERE rule.rule_code IN (
            'characteristic.strength','characteristic.dexterity',
            'characteristic.endurance'))
   INTO allocated,physical_count
   FROM cmd_personal_medical_treatment_allocation allocation
   LEFT JOIN rule_rule rule
     ON rule.rule_id=allocation.characteristic_rule_id
  WHERE allocation.command_id=NEW.command_id;
 IF NEW.procedure_code<>'medical_care' THEN
   SELECT count(*),sum(result) INTO draw_count,draw_total
     FROM cmd_random_draw
    WHERE command_id=NEW.command_id AND draw_group='task';
 END IF;
 IF allocated<>NEW.applied_point_magnitude
    OR physical_count<>(
      SELECT count(*) FROM cmd_personal_medical_treatment_allocation
       WHERE command_id=NEW.command_id)
    OR (NEW.signed_points>0 AND EXISTS (
      SELECT 1 FROM cmd_personal_medical_treatment_allocation
       WHERE command_id=NEW.command_id AND point_change<0))
    OR (NEW.signed_points<0 AND EXISTS (
      SELECT 1 FROM cmd_personal_medical_treatment_allocation
       WHERE command_id=NEW.command_id AND point_change>0))
    OR (NEW.procedure_code<>'medical_care' AND (
        draw_count<>2
        OR NEW.check_total<>draw_total+NEW.medicine_skill_modifier
          +NEW.self_treatment_modifier+NEW.cross_species_modifier))
 THEN
   RAISE EXCEPTION 'Medical-treatment receipt does not match audit facts';
 END IF;
 IF NEW.procedure_code='first_aid' AND NOT EXISTS (
      SELECT 1 FROM cmd_personal_first_aid_link link
       WHERE link.command_id=NEW.command_id)
    OR NEW.procedure_code='surgery' AND NOT EXISTS (
      SELECT 1 FROM cmd_personal_surgery_link link
       WHERE link.command_id=NEW.command_id)
    OR NEW.procedure_code='medical_care' AND NOT EXISTS (
      SELECT 1 FROM cmd_personal_medical_care_link link
       WHERE link.command_id=NEW.command_id) THEN
   RAISE EXCEPTION 'Medical-treatment receipt lacks procedure link';
 END IF;
 RETURN NULL;
END;
$$;
CREATE CONSTRAINT TRIGGER cmd_personal_medical_treatment_receipt_audit
AFTER INSERT ON cmd_personal_medical_treatment_receipt
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION cmd_validate_medical_treatment_receipt();

CREATE FUNCTION cmd_validate_first_aid_link()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE receipt cmd_personal_medical_treatment_receipt%ROWTYPE;
DECLARE damage health_damage_instance%ROWTYPE;
BEGIN
 SELECT * INTO STRICT receipt FROM cmd_personal_medical_treatment_receipt
  WHERE command_id=NEW.command_id;
 SELECT * INTO STRICT damage FROM health_damage_instance
  WHERE damage_instance_id=NEW.damage_instance_id;
 IF receipt.procedure_code<>'first_aid'
    OR receipt.patient_actor_id<>damage.target_actor_id
    OR damage.allocation_status<>'applied'
    OR NEW.elapsed_seconds<>(
      (receipt.campaign_day_number-damage.applied_campaign_day)*86400
      +receipt.campaign_second_of_day-damage.applied_campaign_second)
    OR NEW.effect_multiplier<>(CASE NEW.effectiveness_tier
         WHEN 'full' THEN 2 WHEN 'late' THEN 1 ELSE 0 END) THEN
   RAISE EXCEPTION 'First Aid link does not match injury timing';
 END IF;
 RETURN NEW;
END;
$$;
CREATE TRIGGER cmd_personal_first_aid_link_validate
BEFORE INSERT ON cmd_personal_first_aid_link
FOR EACH ROW EXECUTE FUNCTION cmd_validate_first_aid_link();

CREATE FUNCTION cmd_validate_treatment_facility()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE receipt cmd_personal_medical_treatment_receipt%ROWTYPE;
DECLARE facility health_medical_facility%ROWTYPE;
BEGIN
 SELECT * INTO STRICT receipt FROM cmd_personal_medical_treatment_receipt
  WHERE command_id=NEW.command_id;
 SELECT * INTO STRICT facility FROM health_medical_facility
  WHERE medical_facility_id=receipt.medical_facility_id;
 IF NOT facility.active OR facility.campaign_id<>(
      SELECT campaign_id FROM actor_actor
       WHERE actor_id=receipt.patient_actor_id) THEN
   RAISE EXCEPTION 'Medical facility is not active in patient campaign';
 END IF;
 RETURN NEW;
END;
$$;
CREATE TRIGGER cmd_personal_surgery_facility_validate
BEFORE INSERT ON cmd_personal_surgery_link
FOR EACH ROW EXECUTE FUNCTION cmd_validate_treatment_facility();
CREATE TRIGGER cmd_personal_medical_care_facility_validate
BEFORE INSERT ON cmd_personal_medical_care_link
FOR EACH ROW EXECUTE FUNCTION cmd_validate_treatment_facility();
