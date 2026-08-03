CREATE TABLE rule_personal_stance_change (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    minor_action_cost smallint NOT NULL CHECK (minor_action_cost=1),
    may_choose_any_stance boolean NOT NULL CHECK (may_choose_any_stance),
    must_change_stance boolean NOT NULL CHECK (must_change_stance)
);

CREATE FUNCTION cmd_validate_personal_stance_receipt()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE cost smallint;
BEGIN
 SELECT minor_action_cost INTO STRICT cost
   FROM rule_personal_stance_change;
 IF NEW.stance_before_rule_id=NEW.stance_after_rule_id
    OR NEW.minor_actions_after<>NEW.minor_actions_before-cost
    OR NOT EXISTS (
      SELECT 1 FROM enc_personal_combatant combatant
       WHERE combatant.encounter_id=NEW.encounter_id
         AND combatant.actor_id=NEW.actor_id)
    OR NOT EXISTS (
      SELECT 1 FROM cmd_command command
       WHERE command.command_id=NEW.command_id
         AND command.command_type='change_personal_stance') THEN
   RAISE EXCEPTION 'Stance receipt does not match relational stance-change mechanics';
 END IF;
 RETURN NEW;
END; $$;

CREATE TRIGGER cmd_personal_stance_receipt_valid
BEFORE INSERT ON cmd_personal_stance_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_validate_personal_stance_receipt();

CREATE FUNCTION cmd_reject_personal_stance_receipt_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Personal stance receipts are immutable'; END; $$;

CREATE TRIGGER cmd_personal_stance_receipt_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_stance_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_personal_stance_receipt_mutation();

COMMENT ON TABLE rule_personal_stance_change IS
  'CE-COMBAT-023 paired-source one-minor-action transition to any different personal-combat stance.';
