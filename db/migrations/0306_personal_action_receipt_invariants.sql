CREATE FUNCTION cmd_validate_personal_action_receipt()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE converted smallint;
BEGIN
 SELECT minor_actions_from_significant INTO STRICT converted
   FROM rule_personal_action_economy;
 IF NOT EXISTS (
      SELECT 1 FROM cmd_command command
       WHERE command.command_id=NEW.command_id
         AND command.command_type='spend_personal_action')
    OR NOT EXISTS (
      SELECT 1 FROM enc_personal_combatant combatant
       WHERE combatant.encounter_id=NEW.encounter_id
         AND combatant.actor_id=NEW.actor_id)
    OR (NEW.action_operation='spend_minor' AND NOT (
          NEW.significant_after=NEW.significant_before
          AND NEW.minor_after=NEW.minor_before-1))
    OR (NEW.action_operation='spend_significant' AND NOT (
          NEW.significant_after=NEW.significant_before-1
          AND NEW.minor_after=NEW.minor_before))
    OR (NEW.action_operation='convert_significant' AND NOT (
          NEW.significant_after=NEW.significant_before-1
          AND NEW.minor_after=NEW.minor_before+converted)) THEN
   RAISE EXCEPTION 'Personal action receipt violates relational action economy';
 END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER cmd_personal_action_receipt_valid
BEFORE INSERT ON cmd_personal_action_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_validate_personal_action_receipt();

CREATE FUNCTION cmd_reject_personal_action_receipt_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Personal action receipts are immutable'; END; $$;
CREATE TRIGGER cmd_personal_action_receipt_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_action_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_personal_action_receipt_mutation();

CREATE OR REPLACE FUNCTION cmd_validate_personal_miscellaneous_action_receipt()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE owner_reference text;
DECLARE spend cmd_personal_action_receipt%ROWTYPE;
BEGIN
 SELECT campaign.owner_reference INTO STRICT owner_reference
   FROM enc_personal_combat combat
   JOIN enc_encounter encounter USING(encounter_id)
   JOIN camp_campaign campaign USING(campaign_id)
  WHERE combat.encounter_id=NEW.encounter_id;
 SELECT receipt.* INTO STRICT spend
   FROM cmd_personal_action_receipt receipt
  WHERE receipt.command_id=NEW.command_id;
 IF NEW.referee_reference<>owner_reference
    OR spend.encounter_id<>NEW.encounter_id OR spend.actor_id<>NEW.actor_id
    OR spend.round_number<>NEW.round_number
    OR spend.significant_before<>NEW.significant_before
    OR spend.significant_after<>NEW.significant_after
    OR spend.minor_before<>NEW.minor_before
    OR spend.minor_after<>NEW.minor_after
    OR spend.action_operation<>(CASE NEW.action_tier
         WHEN 'minor' THEN 'spend_minor' ELSE 'spend_significant' END)
    OR (NEW.task_command_id IS NOT NULL AND NOT EXISTS (
      SELECT 1 FROM cmd_actor_task_receipt task
      JOIN cmd_command command USING(command_id)
       WHERE task.command_id=NEW.task_command_id
         AND task.actor_id=NEW.actor_id
         AND command.command_status='completed')) THEN
   RAISE EXCEPTION 'Miscellaneous action receipt violates authority, task, or action budget';
 END IF;
 RETURN NEW;
END; $$;

COMMENT ON FUNCTION cmd_validate_personal_action_receipt() IS
  'CE-COMBAT-024 protects the shared action-budget evidence used by miscellaneous combat actions.';
