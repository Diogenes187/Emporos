CREATE TABLE inv_personal_computer_option_definition (
    item_rule_id bigint PRIMARY KEY REFERENCES inv_item_definition(rule_id),
    option_kind text NOT NULL UNIQUE CHECK (
        option_kind IN ('data-display-recorder','data-wafer')),
    source_mass_is_unquantified boolean NOT NULL CHECK (
        source_mass_is_unquantified),
    wearable_headpiece boolean NOT NULL,
    transparent_display boolean NOT NULL,
    displays_linked_system_data boolean NOT NULL,
    information_storage_medium boolean NOT NULL,
    CHECK (
        (option_kind='data-display-recorder'
         AND wearable_headpiece AND transparent_display
         AND displays_linked_system_data
         AND NOT information_storage_medium)
        OR
        (option_kind='data-wafer'
         AND NOT wearable_headpiece AND NOT transparent_display
         AND NOT displays_linked_system_data
         AND information_storage_medium))
);

CREATE TABLE rule_personal_computer_specialization (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    minimum_added_rating integer NOT NULL CHECK (minimum_added_rating=1),
    maximum_added_rating integer NOT NULL CHECK (maximum_added_rating=2),
    cost_increase_basis_points_per_rating integer NOT NULL CHECK (
        cost_increase_basis_points_per_rating=2500),
    applies_to_one_program boolean NOT NULL CHECK (applies_to_one_program),
    specialized_program_capacity_cost integer NOT NULL CHECK (
        specialized_program_capacity_cost=0)
);

CREATE TABLE cmd_personal_computer_specialization_receipt (
    specialization_receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    command_id bigint NOT NULL UNIQUE REFERENCES cmd_command(command_id),
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    computer_item_instance_id bigint NOT NULL,
    specialized_program_rule_id bigint NOT NULL REFERENCES rule_rule(rule_id),
    added_rating integer NOT NULL CHECK (added_rating IN (1,2)),
    base_computer_rating integer NOT NULL CHECK (base_computer_rating>=0),
    specialized_program_rating integer NOT NULL CHECK (
        specialized_program_rating=base_computer_rating+added_rating),
    base_computer_cost_credits bigint NOT NULL CHECK (
        base_computer_cost_credits>=0),
    surcharge_credits bigint NOT NULL CHECK (
        surcharge_credits=base_computer_cost_credits*added_rating/4),
    installed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    FOREIGN KEY (computer_item_instance_id,campaign_id)
        REFERENCES inv_item_instance(item_instance_id,campaign_id),
    UNIQUE (computer_item_instance_id,specialized_program_rule_id)
);

CREATE FUNCTION cmd_validate_personal_computer_specialization()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE expected_rating integer;
DECLARE expected_cost bigint;
BEGIN
 SELECT computer.model_rating,item.cost_credits
   INTO expected_rating,expected_cost
   FROM inv_item_instance instance
   JOIN inv_personal_computer_definition computer
     ON computer.item_rule_id=instance.item_rule_id
   JOIN inv_item_definition item ON item.rule_id=instance.item_rule_id
  WHERE instance.item_instance_id=NEW.computer_item_instance_id
    AND instance.campaign_id=NEW.campaign_id
    AND instance.item_status='active';
 IF expected_rating IS NULL
    OR NEW.base_computer_rating<>expected_rating
    OR NEW.base_computer_cost_credits<>expected_cost
 THEN RAISE EXCEPTION
   'Computer specialization receipt does not match active computer';
 END IF;
 RETURN NEW;
END;
$$;
CREATE TRIGGER cmd_personal_computer_specialization_valid
BEFORE INSERT ON cmd_personal_computer_specialization_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_validate_personal_computer_specialization();

CREATE FUNCTION cmd_reject_personal_computer_specialization_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 RAISE EXCEPTION 'Computer specialization receipts are immutable';
END;
$$;
CREATE TRIGGER cmd_personal_computer_specialization_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_computer_specialization_receipt
FOR EACH ROW EXECUTE FUNCTION
    cmd_reject_personal_computer_specialization_mutation();

COMMENT ON TABLE cmd_personal_computer_specialization_receipt IS
    'CE-EQUIP-006 immutable campaign specialization configuration.';
