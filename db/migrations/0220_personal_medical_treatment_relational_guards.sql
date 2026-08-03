CREATE FUNCTION cmd_validate_surgery_link()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE surgery cmd_personal_medical_treatment_receipt%ROWTYPE;
DECLARE first_aid cmd_personal_medical_treatment_receipt%ROWTYPE;
DECLARE surgery_created_at timestamptz;
DECLARE first_aid_created_at timestamptz;
BEGIN
 SELECT * INTO STRICT surgery
   FROM cmd_personal_medical_treatment_receipt
  WHERE command_id=NEW.command_id;
 SELECT created_at INTO STRICT surgery_created_at
   FROM cmd_command WHERE command_id=NEW.command_id;
 SELECT * INTO STRICT first_aid
   FROM cmd_personal_medical_treatment_receipt
  WHERE command_id=NEW.first_aid_command_id;
 SELECT created_at INTO STRICT first_aid_created_at
   FROM cmd_command WHERE command_id=NEW.first_aid_command_id;
 IF surgery.procedure_code<>'surgery'
    OR first_aid.procedure_code<>'first_aid'
    OR surgery.patient_actor_id<>first_aid.patient_actor_id
    OR first_aid_created_at>surgery_created_at THEN
   RAISE EXCEPTION
     'Surgery must reference prior First Aid for the same patient';
 END IF;
 RETURN NEW;
END;
$$;
CREATE TRIGGER cmd_personal_surgery_link_validate
BEFORE INSERT ON cmd_personal_surgery_link
FOR EACH ROW EXECUTE FUNCTION cmd_validate_surgery_link();

CREATE FUNCTION cmd_validate_medical_care_link()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE receipt cmd_personal_medical_treatment_receipt%ROWTYPE;
DECLARE damaged_count integer;
DECLARE unfair boolean;
BEGIN
 SELECT * INTO STRICT receipt
   FROM cmd_personal_medical_treatment_receipt
  WHERE command_id=NEW.command_id;
 WITH physical AS (
   SELECT state.characteristic_rule_id,state.maximum_value,
          COALESCE(allocation.value_before,state.current_value) AS value_before,
          COALESCE(allocation.point_change,0) AS point_change,
          COALESCE(allocation.value_after,state.current_value) AS value_after
     FROM actor_characteristic state
     JOIN rule_rule rule
       ON rule.rule_id=state.characteristic_rule_id
     LEFT JOIN cmd_personal_medical_treatment_allocation allocation
       ON allocation.command_id=NEW.command_id
      AND allocation.characteristic_rule_id=state.characteristic_rule_id
    WHERE state.actor_id=receipt.patient_actor_id
      AND rule.rule_code IN (
        'characteristic.strength','characteristic.dexterity',
        'characteristic.endurance')
 ), damaged AS (
   SELECT * FROM physical WHERE value_before<maximum_value
 )
 SELECT count(*),EXISTS (
          SELECT 1 FROM damaged greater
          CROSS JOIN damaged lesser
          WHERE greater.point_change>lesser.point_change+1
            AND lesser.value_after<lesser.maximum_value
        )
   INTO damaged_count,unfair
   FROM damaged;
 IF receipt.procedure_code<>'medical_care'
    OR receipt.self_treatment_modifier<>0
    OR receipt.cross_species_modifier<>0
    OR receipt.signed_points<>GREATEST(
         0,2+receipt.endurance_modifier+receipt.medicine_skill_modifier)
    OR NEW.even_base_share<>COALESCE(
         receipt.signed_points/NULLIF(damaged_count,0),0)
    OR NEW.remainder_points<>COALESCE(
         mod(receipt.signed_points,damaged_count),0)
    OR unfair THEN
   RAISE EXCEPTION
     'Medical Care does not match daily recovery allocation rules';
 END IF;
 RETURN NEW;
END;
$$;
CREATE TRIGGER cmd_personal_medical_care_link_validate
BEFORE INSERT ON cmd_personal_medical_care_link
FOR EACH ROW EXECUTE FUNCTION cmd_validate_medical_care_link();

CREATE OR REPLACE FUNCTION cmd_validate_medical_treatment_receipt()
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
    OR (NEW.unapplied_point_magnitude>0 AND EXISTS (
      SELECT 1
        FROM actor_characteristic state
        JOIN rule_rule rule
          ON rule.rule_id=state.characteristic_rule_id
       WHERE state.actor_id=NEW.patient_actor_id
         AND rule.rule_code IN (
           'characteristic.strength','characteristic.dexterity',
           'characteristic.endurance')
         AND ((NEW.signed_points>0
               AND state.current_value<state.maximum_value)
              OR (NEW.signed_points<0 AND state.current_value>0))))
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
