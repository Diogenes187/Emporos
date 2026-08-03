CREATE FUNCTION cmd_reject_mental_healing_history_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Mental-healing history is immutable'; END;
$$;
CREATE TRIGGER cmd_personal_mental_healing_receipt_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_mental_healing_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_mental_healing_history_mutation();
CREATE TRIGGER cmd_personal_mental_healing_allocation_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_mental_healing_allocation
FOR EACH ROW EXECUTE FUNCTION cmd_reject_mental_healing_history_mutation();

CREATE FUNCTION cmd_validate_mental_healing_receipt()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE allocation_count integer;
DECLARE legal_count integer;
BEGIN
 SELECT count(*),count(*) FILTER (
          WHERE rule.rule_code IN (
            'characteristic.intelligence','characteristic.education'))
   INTO allocation_count,legal_count
   FROM cmd_personal_mental_healing_allocation allocation
   JOIN rule_rule rule
     ON rule.rule_id=allocation.characteristic_rule_id
  WHERE allocation.command_id=NEW.command_id;
 IF allocation_count<>NEW.applied_point_count
    OR legal_count<>allocation_count
    OR EXISTS (
      SELECT 1
        FROM cmd_personal_mental_healing_allocation allocation
        JOIN actor_characteristic state
          ON state.actor_id=NEW.actor_id
         AND state.characteristic_rule_id=
             allocation.characteristic_rule_id
       WHERE allocation.command_id=NEW.command_id
         AND (allocation.value_after<>state.current_value
              OR allocation.value_after>state.maximum_value))
 THEN
   RAISE EXCEPTION 'Mental-healing receipt does not match actor state';
 END IF;
 RETURN NULL;
END;
$$;
CREATE CONSTRAINT TRIGGER cmd_personal_mental_healing_receipt_audit
AFTER INSERT ON cmd_personal_mental_healing_receipt
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION cmd_validate_mental_healing_receipt();
