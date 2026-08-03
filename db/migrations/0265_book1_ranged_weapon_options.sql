CREATE TABLE rule_book1_ranged_weapon_option (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    option_code text NOT NULL UNIQUE,
    minimum_tech_level smallint NOT NULL CHECK (minimum_tech_level>=0),
    canonical_cost_credits bigint NOT NULL CHECK (canonical_cost_credits>=0),
    listed_mass_grams integer CHECK (listed_mass_grams>=0),
    conflicting_source_table_cost_credits bigint CHECK (
        conflicting_source_table_cost_credits>=0),
    maximum_installations smallint NOT NULL DEFAULT 1 CHECK (maximum_installations=1),
    CHECK (conflicting_source_table_cost_credits IS NULL
           OR conflicting_source_table_cost_credits<>canonical_cost_credits)
);
CREATE TABLE rule_book1_ranged_weapon_option_effect (
    option_rule_id bigint PRIMARY KEY REFERENCES rule_book1_ranged_weapon_option(rule_id),
    length_reduction_mm integer CHECK (length_reduction_mm>0),
    magazine_capacity smallint CHECK (magazine_capacity>0),
    reload_minor_actions smallint CHECK (reload_minor_actions>0),
    automatic_fire_permitted boolean,
    recoil_penalty_reduction smallint,
    resulting_recoil_penalty smallint,
    computer_model smallint CHECK (computer_model>=0),
    aimed_attack_modifier smallint,
    visible_laser_dot_removed_at_tech_level smallint,
    authentication_required boolean,
    replacement_attack_profile text REFERENCES combat_attack_profile,
    attach_detach_combat_rounds smallint CHECK (attach_detach_combat_rounds>0),
    prevents_holstering boolean,
    detection_modifier smallint,
    misalignment_target integer,
    misalignment_dice_count smallint,
    misalignment_die_sides smallint,
    misaligned_attacks_always_miss boolean,
    fragile boolean NOT NULL DEFAULT false,
    CHECK ((misalignment_target IS NULL AND misalignment_dice_count IS NULL
            AND misalignment_die_sides IS NULL)
           OR (misalignment_target>0 AND misalignment_dice_count>0
               AND misalignment_die_sides>1))
);
CREATE TABLE rule_book1_ranged_weapon_option_upgrade (
    option_rule_id bigint NOT NULL REFERENCES rule_book1_ranged_weapon_option(rule_id),
    minimum_tech_level smallint NOT NULL CHECK (minimum_tech_level>=0),
    cost_credits bigint NOT NULL CHECK (cost_credits>=0),
    computer_model smallint,
    removes_visible_laser_dot boolean NOT NULL DEFAULT false,
    PRIMARY KEY (option_rule_id,minimum_tech_level)
);
CREATE TABLE rule_book1_ranged_weapon_option_eligibility (
    option_rule_id bigint NOT NULL REFERENCES rule_book1_ranged_weapon_option(rule_id),
    weapon_rule_id bigint NOT NULL REFERENCES inv_weapon_definition(item_rule_id),
    PRIMARY KEY (option_rule_id,weapon_rule_id)
);
CREATE TABLE cmd_book1_ranged_weapon_option_receipt (
    option_receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    idempotency_key text NOT NULL UNIQUE CHECK (btrim(idempotency_key)<>''),
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    weapon_item_instance_id bigint NOT NULL,
    option_item_instance_id bigint NOT NULL,
    option_rule_id bigint NOT NULL REFERENCES rule_book1_ranged_weapon_option(rule_id),
    installed_cost_credits bigint NOT NULL CHECK (installed_cost_credits>=0),
    installed_mass_grams integer,
    installed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    FOREIGN KEY (weapon_item_instance_id,campaign_id)
        REFERENCES inv_item_instance(item_instance_id,campaign_id),
    FOREIGN KEY (option_item_instance_id,campaign_id)
        REFERENCES inv_item_instance(item_instance_id,campaign_id),
    UNIQUE (weapon_item_instance_id,option_rule_id),
    UNIQUE (option_item_instance_id),
    CHECK (weapon_item_instance_id<>option_item_instance_id)
);
CREATE FUNCTION cmd_validate_book1_ranged_weapon_option_receipt()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE weapon inv_item_instance%ROWTYPE;
DECLARE accessory inv_item_instance%ROWTYPE;
DECLARE option_row rule_book1_ranged_weapon_option%ROWTYPE;
BEGIN
 SELECT * INTO weapon FROM inv_item_instance
  WHERE item_instance_id=NEW.weapon_item_instance_id AND campaign_id=NEW.campaign_id FOR UPDATE;
 SELECT * INTO accessory FROM inv_item_instance
  WHERE item_instance_id=NEW.option_item_instance_id AND campaign_id=NEW.campaign_id FOR UPDATE;
 SELECT * INTO option_row FROM rule_book1_ranged_weapon_option WHERE rule_id=NEW.option_rule_id;
 IF weapon.item_status<>'active' OR accessory.item_status<>'active'
 THEN RAISE EXCEPTION 'Weapon and option must be active'; END IF;
 IF accessory.item_rule_id<>NEW.option_rule_id
 THEN RAISE EXCEPTION 'Option instance does not match option rule'; END IF;
 IF NOT EXISTS (SELECT 1 FROM rule_book1_ranged_weapon_option_eligibility
                 WHERE option_rule_id=NEW.option_rule_id
                   AND weapon_rule_id=weapon.item_rule_id)
 THEN RAISE EXCEPTION 'Option is not eligible for this weapon'; END IF;
 IF NEW.installed_cost_credits<>option_row.canonical_cost_credits
    OR NEW.installed_mass_grams IS DISTINCT FROM option_row.listed_mass_grams
 THEN RAISE EXCEPTION 'Option catalogue snapshot is invalid'; END IF;
 RETURN NEW;
END;
$$;
CREATE TRIGGER cmd_book1_ranged_weapon_option_receipt_valid
BEFORE INSERT ON cmd_book1_ranged_weapon_option_receipt FOR EACH ROW
EXECUTE FUNCTION cmd_validate_book1_ranged_weapon_option_receipt();
CREATE FUNCTION cmd_reject_book1_ranged_weapon_option_receipt_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Book 1 ranged-option receipts are immutable'; END;
$$;
CREATE TRIGGER cmd_book1_ranged_weapon_option_receipt_immutable
BEFORE UPDATE OR DELETE ON cmd_book1_ranged_weapon_option_receipt FOR EACH ROW
EXECUTE FUNCTION cmd_reject_book1_ranged_weapon_option_receipt_mutation();
COMMENT ON TABLE rule_book1_ranged_weapon_option IS
 'CE-EQUIP-032 paired-source ranged accessories; Laser Sight canonically costs Cr200 while the conflicting Cr100 source-table assertion remains recorded.';
COMMENT ON TABLE cmd_book1_ranged_weapon_option_receipt IS
 'CE-EQUIP-032 immutable campaign-scoped ranged option installations.';
