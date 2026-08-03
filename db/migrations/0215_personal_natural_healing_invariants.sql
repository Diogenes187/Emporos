CREATE FUNCTION cmd_reject_natural_healing_history_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Natural-healing history is immutable'; END;
$$;
CREATE TRIGGER cmd_personal_natural_healing_receipt_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_natural_healing_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_natural_healing_history_mutation();
CREATE TRIGGER cmd_personal_natural_healing_allocation_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_natural_healing_allocation
FOR EACH ROW EXECUTE FUNCTION cmd_reject_natural_healing_history_mutation();

CREATE FUNCTION cmd_validate_natural_healing_receipt()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE draw cmd_random_draw%ROWTYPE;
DECLARE allocated integer;
DECLARE physical_count integer;
BEGIN
 IF NEW.healing_die_result IS NOT NULL THEN
   SELECT * INTO STRICT draw FROM cmd_random_draw
    WHERE command_id=NEW.command_id AND draw_group='task'
      AND draw_order=1;
   IF draw.die_sides<>6 OR draw.result<>NEW.healing_die_result THEN
     RAISE EXCEPTION 'Natural-healing die does not match random audit';
   END IF;
 END IF;
 SELECT COALESCE(sum(abs(point_change)),0),
        count(*) FILTER (
          WHERE rule.rule_code IN (
            'characteristic.strength','characteristic.dexterity',
            'characteristic.endurance'))
   INTO allocated,physical_count
   FROM cmd_personal_natural_healing_allocation allocation
   LEFT JOIN rule_rule rule
     ON rule.rule_id=allocation.characteristic_rule_id
  WHERE allocation.command_id=NEW.command_id;
 IF allocated<>NEW.applied_point_magnitude
    OR physical_count<>(
      SELECT count(*) FROM cmd_personal_natural_healing_allocation
       WHERE command_id=NEW.command_id)
    OR (NEW.signed_points>0 AND EXISTS (
      SELECT 1 FROM cmd_personal_natural_healing_allocation
       WHERE command_id=NEW.command_id AND point_change<0))
    OR (NEW.signed_points<0 AND EXISTS (
      SELECT 1 FROM cmd_personal_natural_healing_allocation
       WHERE command_id=NEW.command_id AND point_change>0))
 THEN
   RAISE EXCEPTION 'Natural-healing receipt does not match allocations';
 END IF;
 RETURN NULL;
END;
$$;
CREATE CONSTRAINT TRIGGER cmd_personal_natural_healing_receipt_audit
AFTER INSERT ON cmd_personal_natural_healing_receipt
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION cmd_validate_natural_healing_receipt();
