CREATE TABLE rule_psi_shield (
    power_rule_id bigint PRIMARY KEY REFERENCES psi_power(power_rule_id),
    learned_by_all_telepaths boolean NOT NULL CHECK (
        learned_by_all_telepaths
    ),
    automatically_raised boolean NOT NULL CHECK (automatically_raised),
    blocks_unwanted_telepathy boolean NOT NULL CHECK (
        blocks_unwanted_telepathy
    ),
    maintenance_cost smallint NOT NULL CHECK (maintenance_cost=0),
    raised_prevents_telepathy_use boolean NOT NULL CHECK (
        raised_prevents_telepathy_use
    ),
    lowering_allows_contact boolean NOT NULL CHECK (
        lowering_allows_contact
    ),
    lowering_allows_telepathy_use boolean NOT NULL CHECK (
        lowering_allows_telepathy_use
    ),
    combat_action_kind text NOT NULL CHECK (combat_action_kind='free')
);

ALTER TABLE cmd_telepathic_shield_receipt
    ADD COLUMN campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    ADD COLUMN state_changed boolean NOT NULL,
    ADD COLUMN actor_version_before bigint NOT NULL,
    ADD COLUMN actor_version_after bigint NOT NULL,
    ADD COLUMN changed_at timestamptz NOT NULL,
    ADD FOREIGN KEY (actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    ADD CHECK (state_changed=(shield_before<>shield_after)),
    ADD CHECK (
        actor_version_after=actor_version_before+
            CASE WHEN state_changed THEN 1 ELSE 0 END
    );

CREATE FUNCTION cmd_validate_telepathic_shield_receipt()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE command cmd_command%ROWTYPE;
DECLARE state actor_telepathic_shield_state%ROWTYPE;
DECLARE actor_version bigint;
BEGIN
 SELECT * INTO STRICT command FROM cmd_command
  WHERE command_id=NEW.command_id;
 SELECT * INTO STRICT state FROM actor_telepathic_shield_state
  WHERE actor_id=NEW.actor_id;
 SELECT concurrency_version INTO STRICT actor_version FROM actor_actor
  WHERE actor_id=NEW.actor_id AND campaign_id=NEW.campaign_id;
 IF command.command_type<>'set_telepathic_shield'
    OR state.shield_raised<>NEW.shield_after
    OR state.changed_at<>NEW.changed_at
    OR actor_version<>NEW.actor_version_after THEN
   RAISE EXCEPTION 'Shield receipt does not match command or current state';
 END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER cmd_telepathic_shield_receipt_valid
BEFORE INSERT ON cmd_telepathic_shield_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_validate_telepathic_shield_receipt();

CREATE FUNCTION cmd_reject_telepathic_shield_receipt_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Telepathic shield receipts are immutable'; END; $$;
CREATE TRIGGER cmd_telepathic_shield_receipt_immutable
BEFORE UPDATE OR DELETE ON cmd_telepathic_shield_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_telepathic_shield_receipt_mutation();

CREATE FUNCTION actor_validate_telepathic_shield_state()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 PERFORM 1 FROM cmd_telepathic_shield_receipt receipt
  WHERE receipt.actor_id=NEW.actor_id
    AND receipt.shield_after=NEW.shield_raised
    AND receipt.changed_at=NEW.changed_at;
 IF NOT FOUND THEN
   RAISE EXCEPTION 'Shield state requires an immutable command receipt';
 END IF;
 RETURN NULL;
END; $$;
CREATE CONSTRAINT TRIGGER actor_telepathic_shield_state_audit
AFTER INSERT OR UPDATE ON actor_telepathic_shield_state
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
EXECUTE FUNCTION actor_validate_telepathic_shield_state();

COMMENT ON TABLE rule_psi_shield IS
    'CE-PSI-015 paired-source automatic, free-action Telepathic Shield mechanics.';
COMMENT ON TABLE cmd_telepathic_shield_receipt IS
    'Immutable campaign and actor-version snapshot for each shield command.';
