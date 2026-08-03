CREATE FUNCTION cmd_validate_actor_task_context() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE dice_total integer; expected_difficulty bigint; expected_frame bigint;
DECLARE expected_unit text; expected_skill integer; expected_characteristic integer;
BEGIN
 SELECT sum(result) INTO dice_total FROM cmd_random_draw
  WHERE command_id=NEW.command_id AND draw_group='task';
 IF NEW.check_total<>dice_total+NEW.skill_modifier+NEW.characteristic_modifier
      +NEW.difficulty_modifier+NEW.circumstance_modifier+NEW.fatigue_modifier
      +NEW.species_modifier+NEW.pace_modifier+NEW.simultaneous_action_modifier THEN
  RAISE EXCEPTION 'Task receipt total does not match its audited modifiers';
 END IF;
 IF NEW.law_level IS NOT NULL THEN
  SELECT difficulty_rule_id INTO STRICT expected_difficulty
   FROM rule_law_level_difficulty WHERE law_level_range @> NEW.law_level::integer;
  IF expected_difficulty<>NEW.difficulty_rule_id THEN
   RAISE EXCEPTION 'Task difficulty does not match Law Level';
  END IF;
 END IF;
 IF NEW.base_time_frame_rule_id IS NOT NULL THEN
  SELECT resolved.rule_id,resolved.increment_unit INTO STRICT expected_frame,expected_unit
   FROM rule_time_frame base JOIN rule_time_frame resolved
    ON resolved.display_order=base.display_order+NEW.time_frame_steps
   WHERE base.rule_id=NEW.base_time_frame_rule_id;
  IF expected_frame<>NEW.resolved_time_frame_rule_id OR expected_unit<>NEW.task_time_unit
     OR NOT EXISTS(SELECT 1 FROM cmd_random_draw WHERE command_id=NEW.command_id
       AND draw_group='task_time' AND draw_order=1 AND die_sides=6 AND result=NEW.task_time_roll) THEN
   RAISE EXCEPTION 'Task timing receipt does not match the published time-frame shift';
  END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER cmd_actor_task_context_validate BEFORE INSERT ON cmd_actor_task_receipt
 FOR EACH ROW EXECUTE FUNCTION cmd_validate_actor_task_context();

CREATE FUNCTION cmd_reject_actor_task_receipt_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Actor task receipts are immutable'; END $$;
CREATE TRIGGER cmd_actor_task_receipt_immutable BEFORE UPDATE OR DELETE ON cmd_actor_task_receipt
 FOR EACH ROW EXECUTE FUNCTION cmd_reject_actor_task_receipt_mutation();
