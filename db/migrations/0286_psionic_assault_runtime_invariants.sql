ALTER TABLE cmd_psi_assault_receipt ADD CHECK (
    psionic_strength_damage=LEAST(
        COALESCE(psionic_strength_before,0),raw_damage
    )
);
ALTER TABLE cmd_psi_assault_receipt ADD CHECK (
    intelligence_damage=LEAST(
        intelligence_before,raw_damage-psionic_strength_damage
    )
);
ALTER TABLE cmd_psi_assault_receipt ADD CHECK (
    endurance_damage=LEAST(
        endurance_before,
        raw_damage-psionic_strength_damage-intelligence_damage
    )
);

CREATE OR REPLACE FUNCTION cmd_validate_psi_assault()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE activation cmd_psionic_activation_receipt%ROWTYPE;
DECLARE current_psi integer;
DECLARE current_intelligence integer;
DECLARE current_endurance integer;
BEGIN
 SELECT * INTO STRICT activation FROM cmd_psionic_activation_receipt
  WHERE command_id=NEW.activation_command_id;
 PERFORM 1 FROM rule_psi_assault
  WHERE power_rule_id=activation.power_rule_id;
 SELECT
   max(state.current_value) FILTER (
     WHERE rule.rule_code='characteristic.psionic-strength'),
   max(state.current_value) FILTER (
     WHERE rule.rule_code='characteristic.intelligence'),
   max(state.current_value) FILTER (
     WHERE rule.rule_code='characteristic.endurance')
 INTO current_psi,current_intelligence,current_endurance
 FROM actor_characteristic state
 JOIN rule_rule rule ON rule.rule_id=state.characteristic_rule_id
 WHERE state.actor_id=NEW.target_actor_id;
 IF NOT activation.succeeded OR activation.actor_id<>NEW.actor_id
    OR activation.target_actor_id<>NEW.target_actor_id
    OR activation.effect<>NEW.effect_snapshot
    OR activation.timing_total<>NEW.timing_seconds_snapshot
    OR activation.timing_unit<>'seconds'
    OR current_psi IS DISTINCT FROM NEW.psionic_strength_after
    OR current_intelligence IS DISTINCT FROM NEW.intelligence_after
    OR current_endurance IS DISTINCT FROM NEW.endurance_after THEN
   RAISE EXCEPTION 'Assault receipt does not match activation or target state';
 END IF;
 RETURN NEW;
END; $$;
