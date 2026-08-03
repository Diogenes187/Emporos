CREATE FUNCTION cmd_reject_personal_condition_history_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Personal-condition history is immutable'; END;
$$;

CREATE TRIGGER actor_personal_condition_transition_immutable
BEFORE UPDATE OR DELETE ON actor_personal_condition_transition
FOR EACH ROW EXECUTE FUNCTION cmd_reject_personal_condition_history_mutation();
CREATE TRIGGER cmd_personal_fatigue_receipt_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_fatigue_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_personal_condition_history_mutation();
CREATE TRIGGER cmd_personal_fatigue_rest_receipt_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_fatigue_rest_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_personal_condition_history_mutation();
CREATE TRIGGER cmd_personal_unconscious_recovery_receipt_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_unconscious_recovery_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_personal_condition_history_mutation();

CREATE FUNCTION actor_guard_personal_condition_transition()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE history actor_personal_condition_transition%ROWTYPE;
BEGIN
 IF TG_OP='DELETE' THEN
   RAISE EXCEPTION 'Personal-condition current state cannot be deleted';
 END IF;
 SELECT * INTO STRICT history
   FROM actor_personal_condition_transition
  WHERE actor_id=OLD.actor_id AND version_before=OLD.condition_version
    AND version_after=NEW.condition_version;
 IF ROW(history.fatigued_before,history.fatigued_after,
        history.unconscious_before,history.unconscious_after,
        history.recovery_failures_before,history.recovery_failures_after,
        history.minutes_elapsed_before,history.minutes_elapsed_after)
    IS DISTINCT FROM
    ROW(OLD.fatigued,NEW.fatigued,
        OLD.unconscious,NEW.unconscious,
        OLD.unconscious_recovery_failures,
        NEW.unconscious_recovery_failures,
        OLD.unconscious_minutes_elapsed,
        NEW.unconscious_minutes_elapsed) THEN
   RAISE EXCEPTION 'Personal-condition state does not match transition';
 END IF;
 RETURN NEW;
END;
$$;
CREATE TRIGGER actor_personal_condition_transition_guard
BEFORE UPDATE OR DELETE ON actor_personal_condition
FOR EACH ROW EXECUTE FUNCTION actor_guard_personal_condition_transition();

CREATE FUNCTION cmd_validate_personal_condition_transition()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE command_type text;
BEGIN
 SELECT command.command_type INTO STRICT command_type
   FROM cmd_command command WHERE command.command_id=NEW.command_id;
 IF (NEW.transition_kind IN (
       'fatigue_started','fatigue_repeated_unconscious')
     AND command_type<>'apply_personal_fatigue')
    OR (NEW.transition_kind='fatigue_rest_completed'
        AND command_type<>'complete_personal_fatigue_rest')
    OR (NEW.transition_kind IN (
          'consciousness_recovered','consciousness_recovery_failed')
        AND command_type<>'resolve_personal_unconscious_recovery')
 THEN
   RAISE EXCEPTION 'Personal-condition transition has wrong command type';
 END IF;
 RETURN NEW;
END;
$$;
CREATE TRIGGER actor_personal_condition_transition_validate
BEFORE INSERT ON actor_personal_condition_transition
FOR EACH ROW EXECUTE FUNCTION cmd_validate_personal_condition_transition();

CREATE FUNCTION enc_guard_fatigue_attack_snapshot()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.fatigue_attack_modifier IS DISTINCT FROM
    OLD.fatigue_attack_modifier THEN
   RAISE EXCEPTION 'Fatigue attack snapshot is immutable';
 END IF;
 RETURN NEW;
END;
$$;
CREATE TRIGGER enc_personal_attack_fatigue_snapshot_immutable
BEFORE UPDATE ON enc_personal_attack
FOR EACH ROW EXECUTE FUNCTION enc_guard_fatigue_attack_snapshot();
