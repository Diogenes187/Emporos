CREATE OR REPLACE VIEW camp_current_psi_characteristic_enhancement AS
SELECT effect.actor_id,effect.activation_command_id,
       enhancement.characteristic_rule_id,
       enhancement.wounded_value_snapshot,
       enhancement.points_gained,
       CASE
         WHEN statement_timestamp()<enhancement.peak_ends_at
           THEN enhancement.points_gained
         ELSE greatest(
           0,enhancement.points_gained-
             floor(extract(epoch FROM (
               statement_timestamp()-enhancement.peak_ends_at
             ))/60)::integer
         )
       END AS current_bonus,
       enhancement.peak_ends_at,enhancement.decline_ends_at
  FROM cmd_psi_awareness_effect_receipt effect
  JOIN cmd_psi_characteristic_enhancement_receipt enhancement
    USING (activation_command_id)
 WHERE statement_timestamp()<enhancement.decline_ends_at;

CREATE FUNCTION cmd_validate_psi_awareness_specialized_receipt()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE effect cmd_psi_awareness_effect_receipt%ROWTYPE;
DECLARE activation cmd_psionic_activation_receipt%ROWTYPE;
DECLARE power psi_power%ROWTYPE;
DECLARE expected_characteristic bigint;
DECLARE actual_value integer;
DECLARE actual_maximum integer;
DECLARE actual_awareness integer;
DECLARE actual_racial_maximum integer;
BEGIN
 SELECT * INTO STRICT effect FROM cmd_psi_awareness_effect_receipt
  WHERE activation_command_id=NEW.activation_command_id;
 SELECT * INTO STRICT activation FROM cmd_psionic_activation_receipt
  WHERE command_id=NEW.activation_command_id;
 SELECT * INTO STRICT power FROM psi_power
  WHERE power_rule_id=activation.power_rule_id;
 IF TG_TABLE_NAME='cmd_psi_suspended_animation_receipt' THEN
   IF effect.effect_kind<>'suspended_animation'
      OR NEW.scheduled_end_at<>effect.activated_at+interval '7 days' THEN
     RAISE EXCEPTION 'Suspended-animation receipt is not canonical';
   END IF;
 ELSIF TG_TABLE_NAME='cmd_psi_characteristic_enhancement_receipt' THEN
   SELECT characteristic_rule_id INTO STRICT expected_characteristic
     FROM rule_psi_characteristic_enhancement
    WHERE power_rule_id=activation.power_rule_id;
   SELECT current_value INTO STRICT actual_value
     FROM actor_characteristic
    WHERE actor_id=effect.actor_id
      AND characteristic_rule_id=expected_characteristic;
   SELECT skill.skill_level INTO STRICT actual_awareness
     FROM actor_skill skill JOIN rule_rule rule
       ON rule.rule_id=skill.skill_rule_id
    WHERE skill.actor_id=effect.actor_id
      AND rule.rule_code='skill.psionic-awareness';
   SELECT 15+COALESCE(generation.racial_maximum_modifier,0)
     INTO actual_racial_maximum
     FROM actor_actor actor
     LEFT JOIN actor_current_species species ON species.actor_id=actor.actor_id
     LEFT JOIN rule_species_characteristic_generation generation
       ON generation.species_rule_id=species.species_rule_id
      AND generation.characteristic_rule_id=expected_characteristic
    WHERE actor.actor_id=effect.actor_id;
   IF effect.effect_kind<>'characteristic_enhancement'
      OR NEW.characteristic_rule_id<>expected_characteristic
      OR NEW.wounded_value_snapshot<>actual_value
      OR NEW.awareness_level_snapshot<>actual_awareness
      OR NEW.racial_maximum_snapshot<>actual_racial_maximum
      OR NEW.points_gained<>activation.variable_points
      OR NEW.peak_ends_at<>effect.activated_at+interval '10 minutes' THEN
     RAISE EXCEPTION 'Characteristic-enhancement snapshot is invalid';
   END IF;
 ELSE
   SELECT maximum_value INTO STRICT actual_maximum
     FROM actor_characteristic
    WHERE actor_id=effect.actor_id AND characteristic_rule_id=(
      SELECT characteristic_rule_id FROM psi_system);
   IF effect.effect_kind<>'regeneration'
      OR NEW.total_points_regenerated<>activation.variable_points
      OR NEW.psionic_maximum_snapshot<>actual_maximum
      OR EXISTS (
        SELECT 1 FROM camp_psi_regeneration_recovery_lock
         WHERE actor_id=effect.actor_id) THEN
     RAISE EXCEPTION 'Regeneration receipt or recovery lock is invalid';
   END IF;
 END IF;
 RETURN NEW;
END; $$;

CREATE TRIGGER cmd_psi_suspension_canonical
BEFORE INSERT ON cmd_psi_suspended_animation_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_validate_psi_awareness_specialized_receipt();
CREATE TRIGGER cmd_psi_enhancement_canonical
BEFORE INSERT ON cmd_psi_characteristic_enhancement_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_validate_psi_awareness_specialized_receipt();
CREATE TRIGGER cmd_psi_regeneration_canonical
BEFORE INSERT ON cmd_psi_regeneration_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_validate_psi_awareness_specialized_receipt();

CREATE FUNCTION cmd_validate_psi_regeneration_allocations()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE receipt cmd_psi_regeneration_receipt%ROWTYPE;
DECLARE effect cmd_psi_awareness_effect_receipt%ROWTYPE;
DECLARE allocated integer;
DECLARE invalid_count integer;
BEGIN
 SELECT * INTO STRICT receipt FROM cmd_psi_regeneration_receipt
  WHERE activation_command_id=NEW.activation_command_id;
 SELECT * INTO STRICT effect FROM cmd_psi_awareness_effect_receipt
  WHERE activation_command_id=NEW.activation_command_id;
 SELECT COALESCE(sum(allocation.points_regenerated),0),
        count(*) FILTER (
          WHERE permitted.characteristic_rule_id IS NULL
             OR state.current_value<>allocation.value_after
             OR state.maximum_value<>allocation.maximum_value_snapshot)
   INTO allocated,invalid_count
   FROM cmd_psi_regeneration_allocation allocation
   LEFT JOIN rule_psi_regeneration_characteristic permitted
     ON permitted.power_rule_id=(
       SELECT power_rule_id FROM cmd_psionic_activation_receipt
        WHERE command_id=NEW.activation_command_id)
    AND permitted.characteristic_rule_id=allocation.characteristic_rule_id
   LEFT JOIN actor_characteristic state
     ON state.actor_id=effect.actor_id
    AND state.characteristic_rule_id=allocation.characteristic_rule_id
  WHERE allocation.activation_command_id=NEW.activation_command_id;
 IF allocated<>receipt.total_points_regenerated OR invalid_count<>0 THEN
   RAISE EXCEPTION 'Regeneration allocations do not match campaign state';
 END IF;
 RETURN NULL;
END; $$;

CREATE CONSTRAINT TRIGGER cmd_psi_regeneration_allocation_audit
AFTER INSERT ON cmd_psi_regeneration_receipt
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION cmd_validate_psi_regeneration_allocations();

CREATE FUNCTION cmd_validate_psi_suspension_end()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE suspension cmd_psi_suspended_animation_receipt%ROWTYPE;
DECLARE started_at timestamptz;
BEGIN
 SELECT * INTO STRICT suspension FROM cmd_psi_suspended_animation_receipt
  WHERE activation_command_id=NEW.activation_command_id;
 SELECT activated_at INTO STRICT started_at
  FROM cmd_psi_awareness_effect_receipt
  WHERE activation_command_id=NEW.activation_command_id;
 IF NEW.ended_at<started_at
    OR (NEW.ending_kind='duration_elapsed'
        AND NEW.ended_at<suspension.scheduled_end_at)
    OR (NEW.ending_kind='external_stimulus'
        AND NEW.ended_at>=suspension.scheduled_end_at) THEN
   RAISE EXCEPTION 'Suspended-animation ending is invalid';
 END IF;
 RETURN NEW;
END; $$;

CREATE TRIGGER cmd_psi_suspension_end_valid
BEFORE INSERT ON cmd_psi_suspended_animation_end_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_validate_psi_suspension_end();

CREATE FUNCTION cmd_validate_psi_regeneration_release()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE recovery cmd_psionic_recovery_receipt%ROWTYPE;
DECLARE effect cmd_psi_awareness_effect_receipt%ROWTYPE;
BEGIN
 SELECT * INTO STRICT recovery FROM cmd_psionic_recovery_receipt
  WHERE command_id=NEW.recovery_command_id;
 SELECT * INTO STRICT effect FROM cmd_psi_awareness_effect_receipt
  WHERE activation_command_id=NEW.regeneration_activation_command_id;
 IF recovery.actor_id<>NEW.actor_id OR effect.actor_id<>NEW.actor_id
    OR recovery.psionic_strength_after<>NEW.psionic_strength_after
    OR NEW.psionic_strength_after<>NEW.psionic_maximum_snapshot THEN
   RAISE EXCEPTION 'Regeneration release does not match recovery';
 END IF;
 RETURN NEW;
END; $$;

CREATE TRIGGER cmd_psi_regeneration_release_valid
BEFORE INSERT ON cmd_psi_regeneration_release_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_validate_psi_regeneration_release();
