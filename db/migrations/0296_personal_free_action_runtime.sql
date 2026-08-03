DO $$
DECLARE old_definition text;
BEGIN
 SELECT pg_get_constraintdef(oid) INTO STRICT old_definition
 FROM pg_constraint
 WHERE conrelid='cmd_command'::regclass
   AND conname='cmd_command_command_type_check';
 ALTER TABLE cmd_command DROP CONSTRAINT cmd_command_command_type_check;
 EXECUTE format(
   'ALTER TABLE cmd_command ADD CONSTRAINT cmd_command_command_type_check %s',
   replace(old_definition,'CHECK (',
     'CHECK (command_type=''perform_personal_free_action'' OR '));
END; $$;

CREATE TABLE cmd_personal_free_action_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    encounter_id bigint NOT NULL,
    actor_id bigint NOT NULL,
    round_number integer NOT NULL CHECK (round_number>0),
    action_reference text NOT NULL CHECK (btrim(action_reference)<>''),
    assessed_cost text NOT NULL CHECK (
        assessed_cost IN ('free','minor','significant')),
    free_action_ordinal integer NOT NULL CHECK (free_action_ordinal>0),
    significant_actions_before smallint NOT NULL CHECK (
        significant_actions_before>=0),
    significant_actions_after smallint NOT NULL CHECK (
        significant_actions_after>=0),
    minor_actions_before smallint NOT NULL CHECK (minor_actions_before>=0),
    minor_actions_after smallint NOT NULL CHECK (minor_actions_after>=0),
    referee_adjudicator_reference text,
    performed_at timestamptz NOT NULL,
    FOREIGN KEY (encounter_id,actor_id)
        REFERENCES enc_personal_combatant(encounter_id,actor_id),
    CHECK (
      (assessed_cost='free'
       AND significant_actions_after=significant_actions_before
       AND minor_actions_after=minor_actions_before
       AND referee_adjudicator_reference IS NULL)
      OR (assessed_cost='minor'
          AND minor_actions_before>0
          AND minor_actions_after=minor_actions_before-1
          AND significant_actions_after=significant_actions_before
          AND btrim(referee_adjudicator_reference)<>'')
      OR (assessed_cost='significant'
          AND significant_actions_before>0
          AND significant_actions_after=significant_actions_before-1
          AND minor_actions_after=minor_actions_before
          AND btrim(referee_adjudicator_reference)<>'')
    ),
    UNIQUE (encounter_id,actor_id,round_number,free_action_ordinal)
);

CREATE FUNCTION cmd_validate_personal_free_action_receipt()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE stored_type text;
DECLARE combatant enc_personal_combatant%ROWTYPE;
DECLARE owner_reference text;
BEGIN
 SELECT command_type INTO STRICT stored_type FROM cmd_command
 WHERE command_id=NEW.command_id;
 SELECT * INTO STRICT combatant FROM enc_personal_combatant
 WHERE encounter_id=NEW.encounter_id AND actor_id=NEW.actor_id;
 SELECT campaign.owner_reference INTO STRICT owner_reference
 FROM enc_encounter encounter JOIN camp_campaign campaign
   ON campaign.campaign_id=encounter.campaign_id
 WHERE encounter.encounter_id=NEW.encounter_id;
 IF stored_type<>'perform_personal_free_action'
    OR combatant.significant_actions_remaining<>
       NEW.significant_actions_after
    OR combatant.minor_actions_remaining<>NEW.minor_actions_after
    OR (NEW.assessed_cost<>'free'
        AND NEW.referee_adjudicator_reference<>owner_reference) THEN
   RAISE EXCEPTION 'Free Action receipt does not match command or state';
 END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER cmd_personal_free_action_receipt_valid
BEFORE INSERT ON cmd_personal_free_action_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_validate_personal_free_action_receipt();

CREATE FUNCTION cmd_reject_personal_free_action_receipt_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Free Action receipts are immutable'; END; $$;
CREATE TRIGGER cmd_personal_free_action_receipt_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_free_action_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_personal_free_action_receipt_mutation();

COMMENT ON TABLE cmd_personal_free_action_receipt IS
    'Immutable CE-COMBAT-019 turn action, ordinal, escalation, and action-budget snapshot.';
