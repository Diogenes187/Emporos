CREATE FUNCTION cmd_validate_skill_training_week_receipt() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE p camp_skill_training_project%ROWTYPE;
BEGIN
 SELECT * INTO STRICT p FROM camp_skill_training_project WHERE training_project_id=NEW.training_project_id;
 IF p.actor_id<>NEW.actor_id OR p.skill_rule_id<>NEW.skill_rule_id OR p.required_weeks<>NEW.required_weeks
    OR NEW.week_number<>p.completed_weeks
    OR (p.training_status='completed')<>(NEW.week_number=NEW.required_weeks) THEN
   RAISE EXCEPTION 'Skill training receipt does not match its active project';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER cmd_skill_training_week_receipt_valid BEFORE INSERT ON cmd_skill_training_week_receipt
 FOR EACH ROW EXECUTE FUNCTION cmd_validate_skill_training_week_receipt();
CREATE FUNCTION cmd_reject_skill_training_receipt_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Skill training receipts are immutable'; END $$;
CREATE TRIGGER cmd_skill_training_week_receipt_immutable BEFORE UPDATE OR DELETE ON cmd_skill_training_week_receipt
 FOR EACH ROW EXECUTE FUNCTION cmd_reject_skill_training_receipt_mutation();
