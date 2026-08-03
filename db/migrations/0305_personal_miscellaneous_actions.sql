CREATE TABLE rule_personal_miscellaneous_action (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    action_tier text NOT NULL UNIQUE CHECK (action_tier IN ('minor','significant')),
    action_cost smallint NOT NULL CHECK (action_cost=1),
    referee_permission_required boolean NOT NULL CHECK (referee_permission_required),
    permits_skill_check boolean NOT NULL CHECK (permits_skill_check),
    permits_other_action boolean NOT NULL CHECK (permits_other_action),
    requires_full_attention boolean NOT NULL,
    permits_complex_physical_action boolean NOT NULL,
    minimum_seconds smallint,
    maximum_seconds smallint,
    CHECK ((action_tier='minor' AND NOT requires_full_attention
            AND NOT permits_complex_physical_action
            AND minimum_seconds IS NULL AND maximum_seconds IS NULL)
           OR (action_tier='significant' AND requires_full_attention
               AND permits_complex_physical_action
               AND minimum_seconds=1 AND maximum_seconds=6))
);

CREATE TABLE cmd_personal_miscellaneous_action_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_personal_action_receipt(command_id),
    task_command_id bigint UNIQUE REFERENCES cmd_actor_task_receipt(command_id),
    encounter_id bigint NOT NULL REFERENCES enc_personal_combat(encounter_id),
    actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    round_number integer NOT NULL CHECK (round_number>0),
    action_tier text NOT NULL REFERENCES rule_personal_miscellaneous_action(action_tier),
    action_description text NOT NULL CHECK (btrim(action_description)<>''),
    referee_reference text NOT NULL CHECK (btrim(referee_reference)<>''),
    authorization_reason text NOT NULL CHECK (btrim(authorization_reason)<>''),
    significant_before smallint NOT NULL CHECK (significant_before>=0),
    significant_after smallint NOT NULL CHECK (significant_after>=0),
    minor_before smallint NOT NULL CHECK (minor_before>=0),
    minor_after smallint NOT NULL CHECK (minor_after>=0)
);

CREATE FUNCTION cmd_validate_personal_miscellaneous_action_receipt()
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
                  WHEN 'minor' THEN 'spend_minor'
                  ELSE 'spend_significant' END)
    OR (NEW.task_command_id IS NOT NULL AND NOT EXISTS (
      SELECT 1 FROM cmd_actor_task_receipt task
       WHERE task.command_id=NEW.task_command_id
         AND task.actor_id=NEW.actor_id)) THEN
   RAISE EXCEPTION 'Miscellaneous action receipt violates authority, task, or action budget';
 END IF;
 RETURN NEW;
END; $$;

CREATE TRIGGER cmd_personal_miscellaneous_action_receipt_valid
BEFORE INSERT ON cmd_personal_miscellaneous_action_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_validate_personal_miscellaneous_action_receipt();

CREATE FUNCTION cmd_reject_personal_miscellaneous_action_receipt_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Miscellaneous action receipts are immutable'; END; $$;
CREATE TRIGGER cmd_personal_miscellaneous_action_receipt_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_miscellaneous_action_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_personal_miscellaneous_action_receipt_mutation();

COMMENT ON TABLE rule_personal_miscellaneous_action IS
  'CE-COMBAT-024 paired-source referee-authorized minor and significant miscellaneous combat actions.';
