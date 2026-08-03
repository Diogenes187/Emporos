CREATE FUNCTION cmd_validate_personal_grapple_check()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE grapple enc_personal_grapple%ROWTYPE;
DECLARE command cmd_command%ROWTYPE;
DECLARE challenger_dice integer;
DECLARE opponent_dice integer;
BEGIN
 SELECT * INTO STRICT grapple FROM enc_personal_grapple
  WHERE grapple_id=NEW.grapple_id;
 SELECT * INTO STRICT command FROM cmd_command
  WHERE command_id=NEW.command_id;
 SELECT sum(result) INTO challenger_dice FROM cmd_random_draw
  WHERE command_id=NEW.command_id
    AND draw_group='grapple_challenger';
 SELECT sum(result) INTO opponent_dice FROM cmd_random_draw
  WHERE command_id=NEW.command_id
    AND draw_group='grapple_opponent';
 IF command.command_type<>'resolve_personal_grapple_check'
    OR NOT EXISTS (
      SELECT 1 FROM actor_actor
       WHERE actor_id=NEW.challenger_actor_id
         AND controller_reference=command.initiator_reference)
    OR NEW.encounter_id<>grapple.encounter_id
    OR NEW.check_sequence<>grapple.check_sequence
    OR NEW.challenger_actor_id NOT IN (
        grapple.participant_a_actor_id,grapple.participant_b_actor_id)
    OR NEW.opponent_actor_id NOT IN (
        grapple.participant_a_actor_id,grapple.participant_b_actor_id)
    OR challenger_dice IS NULL OR opponent_dice IS NULL
    OR NEW.challenger_total<>challenger_dice+
       NEW.challenger_skill_modifier+
       NEW.challenger_characteristic_modifier+
       NEW.challenger_circumstance_modifier
    OR NEW.opponent_total<>opponent_dice+
       NEW.opponent_skill_modifier+
       NEW.opponent_characteristic_modifier+
       NEW.opponent_circumstance_modifier
    OR NEW.significant_after<>NEW.significant_before-1
    OR (
      NEW.winner_actor_id IS NOT NULL
      AND (
        grapple.grapple_status<>'pending_option'
        OR grapple.pending_check_command_id<>NEW.command_id
        OR grapple.pending_winner_actor_id<>NEW.winner_actor_id
      )
    )
    OR (
      NEW.winner_actor_id IS NULL
      AND (
        (NEW.initial_attempt AND grapple.grapple_status<>'ended')
        OR (NOT NEW.initial_attempt AND grapple.grapple_status<>'active')
      )
    ) THEN
   RAISE EXCEPTION 'Grapple check receipt does not match frozen state';
 END IF;
 RETURN NEW;
END;
$$;
CREATE TRIGGER cmd_personal_grapple_check_receipt_validate
BEFORE INSERT ON cmd_personal_grapple_check_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_validate_personal_grapple_check();

CREATE FUNCTION enc_guard_grapple_active_actor_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE status text;
BEGIN
 IF TG_OP='UPDATE' THEN
   RAISE EXCEPTION 'Active grapple participant rows cannot be reassigned';
 END IF;
 IF TG_OP='DELETE' THEN
   SELECT grapple_status INTO STRICT status FROM enc_personal_grapple
    WHERE grapple_id=OLD.grapple_id;
   IF status<>'ended' THEN
     RAISE EXCEPTION 'Active grapple participants remain until grapple ends';
   END IF;
 END IF;
 RETURN CASE WHEN TG_OP='DELETE' THEN OLD ELSE NEW END;
END;
$$;
CREATE TRIGGER enc_personal_grapple_active_actor_guard
BEFORE UPDATE OR DELETE ON enc_personal_grapple_active_actor
FOR EACH ROW EXECUTE FUNCTION enc_guard_grapple_active_actor_mutation();
