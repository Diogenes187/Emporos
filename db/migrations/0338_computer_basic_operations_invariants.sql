CREATE FUNCTION cmd_validate_computer_basic_operation() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE current_level integer;
BEGIN
 SELECT actor_skill.skill_level INTO current_level
  FROM actor_skill JOIN rule_computer_basic_use rule
    ON rule.skill_rule_id=actor_skill.skill_rule_id
  WHERE actor_skill.actor_id=NEW.actor_id;
 IF current_level IS NULL OR current_level<>NEW.computer_skill_level THEN
  RAISE EXCEPTION 'Computer basic operation requires current Computer-0 or better';
 END IF;
 IF EXISTS(SELECT 1 FROM cmd_random_draw WHERE command_id=NEW.command_id) THEN
  RAISE EXCEPTION 'Computer basic operation cannot contain a random draw';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER cmd_computer_basic_operation_valid BEFORE INSERT ON cmd_computer_basic_operation_receipt FOR EACH ROW EXECUTE FUNCTION cmd_validate_computer_basic_operation();
