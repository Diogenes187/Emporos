CREATE TABLE cmd_psi_telekinetic_manipulation_receipt (
    activation_command_id bigint PRIMARY KEY REFERENCES
        cmd_psionic_activation_receipt(command_id),
    actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    target_kind text NOT NULL CHECK (target_kind IN ('item','creature')),
    target_item_instance_id bigint,
    target_actor_id bigint,
    mass_grams_snapshot bigint NOT NULL CHECK (mass_grams_snapshot>0),
    maximum_mass_grams_snapshot bigint NOT NULL CHECK (
        maximum_mass_grams_snapshot>0
    ),
    duration_rounds smallint NOT NULL CHECK (duration_rounds>0),
    manipulation_started_at timestamptz NOT NULL,
    FOREIGN KEY (actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    FOREIGN KEY (target_item_instance_id,campaign_id)
        REFERENCES inv_item_instance(item_instance_id,campaign_id),
    FOREIGN KEY (target_actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    CHECK (
        (target_kind='item' AND target_item_instance_id IS NOT NULL
         AND target_actor_id IS NULL)
        OR
        (target_kind='creature' AND target_actor_id IS NOT NULL
         AND target_item_instance_id IS NULL)
    ),
    CHECK (mass_grams_snapshot<=maximum_mass_grams_snapshot)
);

CREATE FUNCTION cmd_validate_psi_telekinetic_manipulation()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE activation cmd_psionic_activation_receipt%ROWTYPE;
DECLARE profile rule_psi_telekinesis_mass_profile%ROWTYPE;
DECLARE actual_item_mass integer;
BEGIN
 SELECT * INTO STRICT activation FROM cmd_psionic_activation_receipt
  WHERE command_id=NEW.activation_command_id;
 SELECT * INTO STRICT profile FROM rule_psi_telekinesis_mass_profile
  WHERE power_rule_id=activation.power_rule_id;
 IF NOT activation.succeeded OR activation.actor_id<>NEW.actor_id
    OR profile.maximum_mass_grams<>NEW.maximum_mass_grams_snapshot THEN
   RAISE EXCEPTION 'Telekinetic manipulation does not match activation';
 END IF;
 IF NEW.target_kind='item' THEN
   SELECT definition.mass_grams INTO STRICT actual_item_mass
     FROM inv_item_instance instance
     JOIN inv_item_definition definition
       ON definition.rule_id=instance.item_rule_id
    WHERE instance.item_instance_id=NEW.target_item_instance_id
      AND instance.item_status='active';
   IF actual_item_mass IS NULL
      OR actual_item_mass<>NEW.mass_grams_snapshot THEN
     RAISE EXCEPTION 'Telekinetic item requires exact known mass';
   END IF;
 END IF;
 RETURN NEW;
END; $$;

CREATE TRIGGER cmd_psi_telekinetic_manipulation_valid
BEFORE INSERT ON cmd_psi_telekinetic_manipulation_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_validate_psi_telekinetic_manipulation();

CREATE FUNCTION cmd_reject_psi_telekinetic_manipulation_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Telekinetic manipulation receipts are immutable'; END; $$;

CREATE TRIGGER cmd_psi_telekinetic_manipulation_immutable
BEFORE UPDATE OR DELETE ON cmd_psi_telekinetic_manipulation_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_psi_telekinetic_manipulation_mutation();

COMMENT ON TABLE cmd_psi_telekinetic_manipulation_receipt IS
    'CE-PSI-006 immutable mass-qualified item or creature manipulation state.';
