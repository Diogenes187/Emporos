ALTER TABLE cmd_actor_task_receipt
    ADD COLUMN fatigue_modifier integer NOT NULL DEFAULT 0 CHECK (
        fatigue_modifier IN (0,-2)
    );

ALTER TABLE actor_personal_condition_transition
    ADD CONSTRAINT actor_personal_condition_transition_version_before_unique
        UNIQUE (actor_id,version_before),
    ADD CONSTRAINT actor_personal_condition_transition_version_after_unique
        UNIQUE (actor_id,version_after);

CREATE FUNCTION cmd_validate_personal_condition_receipts()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE history actor_personal_condition_transition%ROWTYPE;
DECLARE draw_count integer;
DECLARE draw_total integer;
BEGIN
 SELECT * INTO STRICT history
   FROM actor_personal_condition_transition
  WHERE command_id=NEW.command_id;
 IF history.actor_id<>NEW.actor_id THEN
   RAISE EXCEPTION 'Personal-condition receipt actor mismatch';
 END IF;
 IF TG_TABLE_NAME='cmd_personal_fatigue_receipt' THEN
   IF history.transition_kind<>NEW.transition_kind
      OR NEW.rest_required_hours<>greatest(0,3+(-NEW.endurance_modifier))
         AND NOT NEW.already_fatigued THEN
     RAISE EXCEPTION 'Fatigue receipt does not match transition or rest rule';
   END IF;
 ELSIF TG_TABLE_NAME='cmd_personal_fatigue_rest_receipt' THEN
   IF history.transition_kind<>'fatigue_rest_completed'
      OR history.fatigued_before<>true
      OR history.fatigued_after<>false THEN
     RAISE EXCEPTION 'Fatigue-rest receipt does not match transition';
   END IF;
 ELSE
   SELECT count(*),sum(result) INTO draw_count,draw_total
     FROM cmd_random_draw
    WHERE command_id=NEW.command_id AND draw_group='task';
   IF draw_count<>2
      OR NEW.check_total<>draw_total+NEW.endurance_modifier
                         +NEW.prior_failure_modifier
      OR NEW.target_number<>8
      OR NEW.attempt_number<>NEW.prior_failure_modifier+1
      OR history.transition_kind<>(
         CASE WHEN NEW.succeeded THEN 'consciousness_recovered'
              ELSE 'consciousness_recovery_failed' END) THEN
     RAISE EXCEPTION 'Unconscious-recovery receipt does not match audit facts';
   END IF;
 END IF;
 RETURN NULL;
END;
$$;

CREATE CONSTRAINT TRIGGER cmd_personal_fatigue_receipt_audit
AFTER INSERT ON cmd_personal_fatigue_receipt
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION cmd_validate_personal_condition_receipts();
CREATE CONSTRAINT TRIGGER cmd_personal_fatigue_rest_receipt_audit
AFTER INSERT ON cmd_personal_fatigue_rest_receipt
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION cmd_validate_personal_condition_receipts();
CREATE CONSTRAINT TRIGGER cmd_personal_unconscious_recovery_receipt_audit
AFTER INSERT ON cmd_personal_unconscious_recovery_receipt
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION cmd_validate_personal_condition_receipts();

CREATE FUNCTION enc_validate_fatigue_attack_snapshot()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE expected integer;
BEGIN
 SELECT CASE WHEN condition.fatigued THEN -2 ELSE 0 END INTO expected
   FROM actor_personal_condition condition
  WHERE condition.actor_id=NEW.attacker_actor_id;
 expected := COALESCE(expected,0);
 IF NEW.fatigue_attack_modifier<>expected THEN
   RAISE EXCEPTION 'Fatigue attack snapshot does not match actor condition';
 END IF;
 RETURN NEW;
END;
$$;
CREATE TRIGGER enc_personal_attack_fatigue_snapshot_validate
BEFORE INSERT ON enc_personal_attack
FOR EACH ROW EXECUTE FUNCTION enc_validate_fatigue_attack_snapshot();

CREATE FUNCTION cmd_validate_actor_task_fatigue()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE expected integer;
BEGIN
 SELECT CASE WHEN condition.fatigued THEN -2 ELSE 0 END INTO expected
   FROM actor_personal_condition condition
  WHERE condition.actor_id=NEW.actor_id;
 expected := COALESCE(expected,0);
 IF NEW.fatigue_modifier<>expected THEN
   RAISE EXCEPTION 'Task fatigue modifier does not match actor condition';
 END IF;
 RETURN NEW;
END;
$$;
CREATE TRIGGER cmd_actor_task_fatigue_validate
BEFORE INSERT ON cmd_actor_task_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_validate_actor_task_fatigue();
