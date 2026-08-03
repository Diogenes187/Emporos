DO $$
DECLARE old_definition text;
BEGIN
 SELECT pg_get_constraintdef(oid) INTO STRICT old_definition
 FROM pg_constraint WHERE conrelid='cmd_command'::regclass
   AND conname='cmd_command_command_type_check';
 ALTER TABLE cmd_command DROP CONSTRAINT cmd_command_command_type_check;
 EXECUTE format(
   'ALTER TABLE cmd_command ADD CONSTRAINT cmd_command_command_type_check %s',
   replace(old_definition,'CHECK (',
     'CHECK (command_type=''advance_personal_weapon_ready'' OR '));
END; $$;

ALTER TABLE actor_weapon_state
    ADD COLUMN ready_progress smallint NOT NULL DEFAULT 0 CHECK (
        ready_progress>=0),
    ADD COLUMN ready_required_actions smallint CHECK (
        ready_required_actions>0),
    ADD COLUMN ready_basis text CHECK (
        ready_basis IN ('source_default','explicit_profile','referee_override')),
    ADD COLUMN ready_referee_reference text,
    ADD COLUMN ready_override_reason text,
    ADD CONSTRAINT actor_weapon_ready_progress_consistent CHECK (
      (ready_progress=0 AND ready_required_actions IS NULL
       AND ready_basis IS NULL AND ready_referee_reference IS NULL
       AND ready_override_reason IS NULL)
      OR (NOT ready AND ready_progress>0
          AND ready_required_actions>ready_progress
          AND ready_basis IS NOT NULL
          AND ((ready_basis='referee_override'
                AND btrim(ready_referee_reference)<>''
                AND btrim(ready_override_reason)<>'')
               OR (ready_basis<>'referee_override'
                   AND ready_referee_reference IS NULL
                   AND ready_override_reason IS NULL)))
    );

CREATE TABLE cmd_personal_weapon_ready_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    encounter_id bigint NOT NULL,
    actor_id bigint NOT NULL,
    weapon_rule_id bigint NOT NULL REFERENCES inv_weapon_definition(item_rule_id),
    round_number integer NOT NULL CHECK (round_number>0),
    ready_basis text NOT NULL CHECK (
        ready_basis IN ('source_default','explicit_profile','referee_override')),
    required_minor_actions smallint NOT NULL CHECK (required_minor_actions>0),
    progress_before smallint NOT NULL CHECK (progress_before>=0),
    progress_after smallint NOT NULL CHECK (
        progress_after=progress_before+1),
    completed boolean NOT NULL CHECK (
        completed=(progress_after=required_minor_actions)),
    minor_actions_before smallint NOT NULL CHECK (minor_actions_before>0),
    minor_actions_after smallint NOT NULL CHECK (
        minor_actions_after=minor_actions_before-1),
    referee_adjudicator_reference text,
    referee_override_reason text,
    resolved_at timestamptz NOT NULL,
    FOREIGN KEY (encounter_id,actor_id)
        REFERENCES enc_personal_combatant(encounter_id,actor_id),
    CHECK (
      (ready_basis='referee_override'
       AND btrim(referee_adjudicator_reference)<>''
       AND btrim(referee_override_reason)<>'')
      OR (ready_basis<>'referee_override'
          AND referee_adjudicator_reference IS NULL
          AND referee_override_reason IS NULL)
    )
);

CREATE FUNCTION cmd_validate_personal_weapon_ready_receipt()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE stored_type text;
DECLARE combatant_minor smallint;
DECLARE weapon actor_weapon_state%ROWTYPE;
DECLARE owner_reference text;
BEGIN
 SELECT command_type INTO STRICT stored_type FROM cmd_command
  WHERE command_id=NEW.command_id;
 SELECT minor_actions_remaining INTO STRICT combatant_minor
 FROM enc_personal_combatant WHERE encounter_id=NEW.encounter_id
  AND actor_id=NEW.actor_id;
 SELECT * INTO STRICT weapon FROM actor_weapon_state
 WHERE actor_id=NEW.actor_id AND weapon_rule_id=NEW.weapon_rule_id;
 SELECT campaign.owner_reference INTO STRICT owner_reference
 FROM enc_encounter encounter JOIN camp_campaign campaign
  ON campaign.campaign_id=encounter.campaign_id
 WHERE encounter.encounter_id=NEW.encounter_id;
 IF stored_type<>'advance_personal_weapon_ready'
    OR combatant_minor<>NEW.minor_actions_after
    OR weapon.ready<>NEW.completed
    OR (NOT NEW.completed AND (
        weapon.ready_progress<>NEW.progress_after
        OR weapon.ready_required_actions<>NEW.required_minor_actions))
    OR (NEW.ready_basis='referee_override'
        AND NEW.referee_adjudicator_reference<>owner_reference) THEN
   RAISE EXCEPTION 'Weapon-ready receipt does not match command or state';
 END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER cmd_personal_weapon_ready_receipt_valid
BEFORE INSERT ON cmd_personal_weapon_ready_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_validate_personal_weapon_ready_receipt();

CREATE FUNCTION cmd_reject_personal_weapon_ready_receipt_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Weapon-ready receipts are immutable'; END; $$;
CREATE TRIGGER cmd_personal_weapon_ready_receipt_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_weapon_ready_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_personal_weapon_ready_receipt_mutation();

COMMENT ON TABLE cmd_personal_weapon_ready_receipt IS
    'Immutable CE-COMBAT-021 readying progress, action cost, authority, and completion.';
