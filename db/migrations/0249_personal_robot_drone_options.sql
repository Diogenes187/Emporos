CREATE TABLE rule_personal_robot_drone_option (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    option_code text NOT NULL UNIQUE CHECK (
        option_code IN ('armor','integral-system','integral-weapon')),
    armor_increase integer,
    robot_cost_increase_basis_points integer,
    selected_item_cost_increase_basis_points integer,
    fixed_surcharge_credits bigint,
    requires_selected_item boolean NOT NULL,
    CHECK (
        (option_code='armor' AND armor_increase=5
         AND robot_cost_increase_basis_points=2500
         AND selected_item_cost_increase_basis_points IS NULL
         AND fixed_surcharge_credits IS NULL AND NOT requires_selected_item)
        OR
        (option_code='integral-system' AND armor_increase IS NULL
         AND robot_cost_increase_basis_points IS NULL
         AND selected_item_cost_increase_basis_points=5000
         AND fixed_surcharge_credits IS NULL AND requires_selected_item)
        OR
        (option_code='integral-weapon' AND armor_increase IS NULL
         AND robot_cost_increase_basis_points IS NULL
         AND selected_item_cost_increase_basis_points IS NULL
         AND fixed_surcharge_credits=10000 AND requires_selected_item))
);

CREATE TABLE cmd_personal_robot_drone_option_receipt (
    option_receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    idempotency_key text NOT NULL UNIQUE CHECK (btrim(idempotency_key)<>''),
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    robot_item_instance_id bigint NOT NULL,
    option_rule_id bigint NOT NULL REFERENCES
        rule_personal_robot_drone_option(rule_id),
    selected_item_rule_id bigint REFERENCES inv_item_definition(rule_id),
    base_robot_cost_credits bigint NOT NULL CHECK (base_robot_cost_credits>=0),
    selected_item_cost_credits bigint,
    surcharge_quarter_credits bigint NOT NULL CHECK (
        surcharge_quarter_credits>=0),
    installed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    FOREIGN KEY (robot_item_instance_id,campaign_id)
        REFERENCES inv_item_instance(item_instance_id,campaign_id),
    UNIQUE (robot_item_instance_id,option_rule_id),
    CHECK (
        (selected_item_rule_id IS NULL AND selected_item_cost_credits IS NULL)
        OR
        (selected_item_rule_id IS NOT NULL
         AND selected_item_cost_credits IS NOT NULL
         AND selected_item_cost_credits>=0))
);

CREATE FUNCTION cmd_validate_personal_robot_drone_option_receipt()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE option_row rule_personal_robot_drone_option%ROWTYPE;
DECLARE expected_robot_cost bigint;
DECLARE expected_selected_cost bigint;
DECLARE expected_surcharge bigint;
BEGIN
 SELECT option.* INTO option_row
   FROM rule_personal_robot_drone_option option
  WHERE option.rule_id=NEW.option_rule_id;
 SELECT item.cost_credits INTO expected_robot_cost
   FROM inv_item_instance instance
   JOIN inv_personal_robot_drone_chassis chassis
     ON chassis.item_rule_id=instance.item_rule_id
   JOIN inv_item_definition item ON item.rule_id=instance.item_rule_id
  WHERE instance.item_instance_id=NEW.robot_item_instance_id
    AND instance.campaign_id=NEW.campaign_id
    AND instance.item_status='active';
 IF expected_robot_cost IS NULL
    OR NEW.base_robot_cost_credits<>expected_robot_cost
 THEN RAISE EXCEPTION
   'Robot/drone option receipt does not match active chassis';
 END IF;
 IF option_row.requires_selected_item<>(NEW.selected_item_rule_id IS NOT NULL)
 THEN RAISE EXCEPTION
   'Robot/drone option selected-item requirement is not satisfied';
 END IF;
 IF NEW.selected_item_rule_id IS NOT NULL THEN
   SELECT cost_credits INTO expected_selected_cost
     FROM inv_item_definition WHERE rule_id=NEW.selected_item_rule_id;
   IF expected_selected_cost IS NULL
      OR NEW.selected_item_cost_credits<>expected_selected_cost
   THEN RAISE EXCEPTION
     'Robot/drone option selected-item cost does not match catalogue';
   END IF;
 END IF;
 expected_surcharge := CASE option_row.option_code
   WHEN 'armor' THEN expected_robot_cost
   WHEN 'integral-system' THEN expected_selected_cost*6
   WHEN 'integral-weapon' THEN 40000+expected_selected_cost*4
 END;
 IF NEW.surcharge_quarter_credits<>expected_surcharge THEN
   RAISE EXCEPTION 'Robot/drone option surcharge arithmetic is invalid';
 END IF;
 RETURN NEW;
END;
$$;

CREATE TRIGGER cmd_personal_robot_drone_option_receipt_valid
BEFORE INSERT ON cmd_personal_robot_drone_option_receipt
FOR EACH ROW EXECUTE FUNCTION
    cmd_validate_personal_robot_drone_option_receipt();

CREATE FUNCTION cmd_reject_personal_robot_drone_option_receipt_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 RAISE EXCEPTION 'Robot/drone option receipts are immutable';
END;
$$;

CREATE TRIGGER cmd_personal_robot_drone_option_receipt_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_robot_drone_option_receipt
FOR EACH ROW EXECUTE FUNCTION
    cmd_reject_personal_robot_drone_option_receipt_mutation();

COMMENT ON TABLE rule_personal_robot_drone_option IS
    'CE-EQUIP-018 paired-source robot and drone construction options.';
COMMENT ON COLUMN
    cmd_personal_robot_drone_option_receipt.surcharge_quarter_credits IS
    'Exact surcharge in quarter-Credit units; avoids unstated rounding.';
