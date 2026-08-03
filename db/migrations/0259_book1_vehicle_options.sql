CREATE TABLE rule_book1_vehicle_option (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    option_code text NOT NULL UNIQUE CHECK (option_code IN (
        'autopilot','enclosed','extended-life-support','heavy-armor',
        'high-performance','on-board-computer','sealed','style')),
    minimum_tech_level smallint CHECK (minimum_tech_level>=0),
    maximum_installations smallint CHECK (maximum_installations=1),
    cost_basis text NOT NULL CHECK (cost_basis IN (
        'fixed','base-percent','selected-hand-computer','bounded-fixed')),
    fixed_cost_credits bigint CHECK (fixed_cost_credits>=0),
    minimum_cost_credits bigint CHECK (minimum_cost_credits>=0),
    maximum_cost_credits bigint CHECK (
        maximum_cost_credits>=minimum_cost_credits),
    base_cost_percent smallint CHECK (base_cost_percent>0),
    agility_modifier smallint NOT NULL DEFAULT 0,
    top_speed_percent_modifier smallint NOT NULL DEFAULT 0,
    armor_increase smallint NOT NULL DEFAULT 0,
    life_support_seconds_per_person integer,
    changes_configuration_to_closed boolean NOT NULL DEFAULT false,
    autopilot_model_rating smallint,
    autopilot_intellect_rating smallint,
    autopilot_expert_rating smallint,
    CHECK (
        (cost_basis='fixed' AND fixed_cost_credits IS NOT NULL
         AND minimum_cost_credits IS NULL AND maximum_cost_credits IS NULL
         AND base_cost_percent IS NULL)
        OR (cost_basis='base-percent' AND fixed_cost_credits IS NULL
         AND minimum_cost_credits IS NULL AND maximum_cost_credits IS NULL
         AND base_cost_percent IS NOT NULL)
        OR (cost_basis='selected-hand-computer'
         AND fixed_cost_credits IS NULL AND minimum_cost_credits IS NULL
         AND maximum_cost_credits IS NULL AND base_cost_percent IS NULL)
        OR (cost_basis='bounded-fixed' AND fixed_cost_credits IS NULL
         AND minimum_cost_credits IS NOT NULL
         AND maximum_cost_credits IS NOT NULL
         AND base_cost_percent IS NULL)),
    CHECK (
        (option_code='autopilot' AND autopilot_model_rating=1
         AND autopilot_intellect_rating=1 AND autopilot_expert_rating=1)
        OR (option_code<>'autopilot' AND autopilot_model_rating IS NULL
         AND autopilot_intellect_rating IS NULL
         AND autopilot_expert_rating IS NULL))
);

CREATE TABLE rule_book1_vehicle_included_option (
    vehicle_profile_rule_id bigint NOT NULL REFERENCES
        rule_book1_vehicle_profile(rule_id),
    option_rule_id bigint NOT NULL REFERENCES
        rule_book1_vehicle_option(rule_id),
    PRIMARY KEY (vehicle_profile_rule_id,option_rule_id)
);

CREATE TABLE camp_book1_vehicle_instance (
    vehicle_instance_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    vehicle_profile_rule_id bigint NOT NULL REFERENCES
        rule_book1_vehicle_profile(rule_id),
    instance_name text NOT NULL CHECK (btrim(instance_name)<>''),
    manufactured_tech_level smallint NOT NULL CHECK (
        manufactured_tech_level>=0),
    vehicle_status text NOT NULL DEFAULT 'active' CHECK (
        vehicle_status IN ('active','destroyed','retired')),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (vehicle_instance_id,campaign_id)
);

CREATE TABLE cmd_book1_vehicle_option_receipt (
    option_receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    idempotency_key text NOT NULL UNIQUE CHECK (btrim(idempotency_key)<>''),
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    vehicle_instance_id bigint NOT NULL,
    option_rule_id bigint NOT NULL REFERENCES
        rule_book1_vehicle_option(rule_id),
    installation_number smallint NOT NULL CHECK (installation_number>0),
    selected_hand_computer_rule_id bigint REFERENCES
        inv_personal_computer_definition(item_rule_id),
    base_vehicle_cost_credits bigint NOT NULL CHECK (
        base_vehicle_cost_credits>=0),
    selected_hand_computer_cost_credits bigint,
    surcharge_credits bigint NOT NULL CHECK (surcharge_credits>=0),
    agility_modifier smallint NOT NULL,
    top_speed_percent_modifier smallint NOT NULL,
    armor_increase smallint NOT NULL,
    life_support_seconds_per_person integer,
    changes_configuration_to_closed boolean NOT NULL,
    installed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    FOREIGN KEY (vehicle_instance_id,campaign_id) REFERENCES
        camp_book1_vehicle_instance(vehicle_instance_id,campaign_id),
    UNIQUE (vehicle_instance_id,option_rule_id,installation_number),
    CHECK ((selected_hand_computer_rule_id IS NULL)=
           (selected_hand_computer_cost_credits IS NULL))
);

CREATE FUNCTION cmd_validate_book1_vehicle_option_receipt()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE vehicle camp_book1_vehicle_instance%ROWTYPE;
DECLARE profile rule_book1_vehicle_profile%ROWTYPE;
DECLARE option_row rule_book1_vehicle_option%ROWTYPE;
DECLARE expected_computer_cost bigint;
DECLARE expected_surcharge bigint;
DECLARE prior_count integer;
DECLARE effectively_closed boolean;
BEGIN
 SELECT * INTO vehicle FROM camp_book1_vehicle_instance
  WHERE vehicle_instance_id=NEW.vehicle_instance_id
    AND campaign_id=NEW.campaign_id FOR UPDATE;
 SELECT * INTO profile FROM rule_book1_vehicle_profile
  WHERE rule_id=vehicle.vehicle_profile_rule_id;
 SELECT * INTO option_row FROM rule_book1_vehicle_option
  WHERE rule_id=NEW.option_rule_id;
 IF vehicle.vehicle_status<>'active'
    OR vehicle.manufactured_tech_level<profile.minimum_tech_level
    OR (option_row.minimum_tech_level IS NOT NULL
        AND vehicle.manufactured_tech_level<option_row.minimum_tech_level)
 THEN RAISE EXCEPTION 'Vehicle option is not eligible at this state or TL';
 END IF;
 IF EXISTS (SELECT 1 FROM rule_book1_vehicle_capability capability
             WHERE capability.vehicle_profile_rule_id=profile.rule_id
               AND capability.vehicle_options_prohibited)
 THEN RAISE EXCEPTION 'This vehicle profile prohibits options'; END IF;
 SELECT count(*) INTO prior_count FROM cmd_book1_vehicle_option_receipt
  WHERE vehicle_instance_id=NEW.vehicle_instance_id
    AND option_rule_id=NEW.option_rule_id;
 IF option_row.maximum_installations=1 AND prior_count>0
 THEN RAISE EXCEPTION 'Vehicle option can only be installed once'; END IF;
 IF NEW.installation_number<>prior_count+1
 THEN RAISE EXCEPTION 'Vehicle option installation number is not contiguous';
 END IF;
 effectively_closed := profile.configuration='closed' OR EXISTS (
   SELECT 1 FROM cmd_book1_vehicle_option_receipt receipt
   JOIN rule_book1_vehicle_option installed
     ON installed.rule_id=receipt.option_rule_id
   WHERE receipt.vehicle_instance_id=NEW.vehicle_instance_id
     AND installed.option_code='enclosed');
 IF option_row.option_code='enclosed' AND effectively_closed
 THEN RAISE EXCEPTION 'Enclosed requires an open vehicle'; END IF;
 IF option_row.option_code='sealed' AND NOT effectively_closed
 THEN RAISE EXCEPTION 'Sealed requires a closed vehicle'; END IF;
 IF option_row.option_code='sealed' AND EXISTS (
   SELECT 1 FROM rule_book1_vehicle_included_option included
   JOIN rule_book1_vehicle_option included_option
     ON included_option.rule_id=included.option_rule_id
   WHERE included.vehicle_profile_rule_id=profile.rule_id
     AND included_option.option_code='sealed')
 THEN RAISE EXCEPTION 'Sealed is already included in this profile'; END IF;
 IF option_row.option_code='extended-life-support' AND NOT (
   EXISTS (SELECT 1 FROM rule_book1_vehicle_included_option included
     JOIN rule_book1_vehicle_option included_option
       ON included_option.rule_id=included.option_rule_id
     WHERE included.vehicle_profile_rule_id=profile.rule_id
       AND included_option.option_code='sealed')
   OR EXISTS (SELECT 1 FROM cmd_book1_vehicle_option_receipt receipt
     JOIN rule_book1_vehicle_option installed
       ON installed.rule_id=receipt.option_rule_id
     WHERE receipt.vehicle_instance_id=NEW.vehicle_instance_id
       AND installed.option_code='sealed'))
 THEN RAISE EXCEPTION 'Extended life support requires sealed'; END IF;
 IF option_row.option_code='heavy-armor' AND profile.armor IS NULL
 THEN RAISE EXCEPTION 'Heavy armor requires a defined armor value'; END IF;
 IF NEW.base_vehicle_cost_credits<>profile.cost_credits
 THEN RAISE EXCEPTION 'Vehicle base-cost snapshot is invalid'; END IF;
 IF option_row.cost_basis='selected-hand-computer' THEN
   SELECT item.cost_credits INTO expected_computer_cost
     FROM inv_personal_computer_definition computer
     JOIN inv_item_definition item ON item.rule_id=computer.item_rule_id
    WHERE computer.item_rule_id=NEW.selected_hand_computer_rule_id
      AND computer.computer_kind='hand-computer'
      AND computer.optimum_tech_level<=vehicle.manufactured_tech_level;
   IF expected_computer_cost IS NULL
      OR NEW.selected_hand_computer_cost_credits<>expected_computer_cost
   THEN RAISE EXCEPTION 'On-board computer selection or cost is invalid';
   END IF;
 ELSE
   IF NEW.selected_hand_computer_rule_id IS NOT NULL
   THEN RAISE EXCEPTION 'Only on-board computer selects a hand computer';
   END IF;
 END IF;
 expected_surcharge := CASE option_row.cost_basis
   WHEN 'fixed' THEN option_row.fixed_cost_credits
   WHEN 'base-percent' THEN
     profile.cost_credits*option_row.base_cost_percent/100
   WHEN 'selected-hand-computer' THEN expected_computer_cost
   WHEN 'bounded-fixed' THEN NEW.surcharge_credits
 END;
 IF NEW.surcharge_credits<>expected_surcharge
    OR (option_row.cost_basis='bounded-fixed' AND
        NEW.surcharge_credits NOT BETWEEN option_row.minimum_cost_credits
                                  AND option_row.maximum_cost_credits)
 THEN RAISE EXCEPTION 'Vehicle option surcharge is invalid'; END IF;
 IF (NEW.agility_modifier,NEW.top_speed_percent_modifier,
     NEW.armor_increase,NEW.life_support_seconds_per_person,
     NEW.changes_configuration_to_closed) IS DISTINCT FROM
    (option_row.agility_modifier,option_row.top_speed_percent_modifier,
     option_row.armor_increase,option_row.life_support_seconds_per_person,
     option_row.changes_configuration_to_closed)
 THEN RAISE EXCEPTION 'Vehicle option mechanical snapshot is invalid'; END IF;
 RETURN NEW;
END;
$$;

CREATE TRIGGER cmd_book1_vehicle_option_receipt_valid
BEFORE INSERT ON cmd_book1_vehicle_option_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_validate_book1_vehicle_option_receipt();

CREATE FUNCTION cmd_reject_book1_vehicle_option_receipt_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Book 1 vehicle-option receipts are immutable'; END;
$$;
CREATE TRIGGER cmd_book1_vehicle_option_receipt_immutable
BEFORE UPDATE OR DELETE ON cmd_book1_vehicle_option_receipt
FOR EACH ROW EXECUTE FUNCTION
    cmd_reject_book1_vehicle_option_receipt_mutation();

COMMENT ON TABLE rule_book1_vehicle_option IS
    'CE-EQUIP-027 paired-source Book 1 vehicle options.';
COMMENT ON TABLE cmd_book1_vehicle_option_receipt IS
    'CE-EQUIP-027 immutable campaign-scoped vehicle option installations.';
