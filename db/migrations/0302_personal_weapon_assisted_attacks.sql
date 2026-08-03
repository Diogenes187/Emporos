CREATE TABLE enc_personal_attack_weapon_assistance (
    personal_attack_id bigint PRIMARY KEY REFERENCES
        enc_personal_attack(personal_attack_id),
    weapon_item_instance_id bigint NOT NULL REFERENCES
        inv_item_instance(item_instance_id),
    laser_sight_installed boolean NOT NULL,
    laser_sight_modifier smallint NOT NULL CHECK (
        laser_sight_modifier IN (0,1)),
    intelligent_weapon_installed boolean NOT NULL,
    intelligent_weapon_modifier smallint NOT NULL CHECK (
        intelligent_weapon_modifier IN (0,1)),
    intelligent_weapon_suppressed boolean NOT NULL,
    suppression_referee_reference text,
    suppression_reason text,
    CHECK ((laser_sight_modifier=1)<=laser_sight_installed),
    CHECK ((intelligent_weapon_modifier=1 OR intelligent_weapon_suppressed)
           =intelligent_weapon_installed),
    CHECK ((intelligent_weapon_suppressed AND intelligent_weapon_modifier=0
            AND btrim(suppression_referee_reference)<>''
            AND btrim(suppression_reason)<>'')
           OR (NOT intelligent_weapon_suppressed
               AND suppression_referee_reference IS NULL
               AND suppression_reason IS NULL))
);

CREATE FUNCTION enc_validate_personal_attack_weapon_assistance()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE attack enc_personal_attack%ROWTYPE;
DECLARE item inv_item_instance%ROWTYPE;
DECLARE owner_reference text;
DECLARE laser_installed boolean;
DECLARE intelligent_installed boolean;
BEGIN
 SELECT * INTO STRICT attack FROM enc_personal_attack
  WHERE personal_attack_id=NEW.personal_attack_id;
 SELECT * INTO STRICT item FROM inv_item_instance
  WHERE item_instance_id=NEW.weapon_item_instance_id;
 SELECT campaign.owner_reference INTO STRICT owner_reference
 FROM enc_encounter encounter JOIN camp_campaign campaign
  ON campaign.campaign_id=encounter.campaign_id
 WHERE encounter.encounter_id=attack.encounter_id;
 SELECT EXISTS (
   SELECT 1 FROM cmd_book1_ranged_weapon_option_receipt receipt
   JOIN rule_book1_ranged_weapon_option option
     ON option.rule_id=receipt.option_rule_id
   WHERE receipt.weapon_item_instance_id=NEW.weapon_item_instance_id
     AND option.option_code='laser-sights'),
   EXISTS (
   SELECT 1 FROM cmd_book1_ranged_weapon_option_receipt receipt
   JOIN rule_book1_ranged_weapon_option option
     ON option.rule_id=receipt.option_rule_id
   WHERE receipt.weapon_item_instance_id=NEW.weapon_item_instance_id
     AND option.option_code='intelligent-weapon')
 INTO laser_installed,intelligent_installed;
 IF item.item_rule_id<>attack.weapon_rule_id
    OR item.item_status<>'active'
    OR item.campaign_id<>(SELECT campaign_id FROM actor_actor
                          WHERE actor_id=attack.attacker_actor_id)
    OR NOT EXISTS (
      SELECT 1 FROM inv_container_item held
      JOIN inv_actor_container owner USING (container_id,campaign_id)
      WHERE held.item_instance_id=item.item_instance_id
        AND owner.actor_id=attack.attacker_actor_id)
    OR NEW.laser_sight_installed<>laser_installed
    OR NEW.intelligent_weapon_installed<>intelligent_installed
    OR (NEW.intelligent_weapon_suppressed
        AND NEW.suppression_referee_reference<>owner_reference) THEN
   RAISE EXCEPTION 'Weapon assistance does not match custody, options, or referee';
 END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER enc_personal_attack_weapon_assistance_valid
BEFORE INSERT ON enc_personal_attack_weapon_assistance
FOR EACH ROW EXECUTE FUNCTION enc_validate_personal_attack_weapon_assistance();

CREATE FUNCTION enc_reject_personal_attack_weapon_assistance_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Declared weapon assistance is immutable'; END; $$;
CREATE TRIGGER enc_personal_attack_weapon_assistance_immutable
BEFORE UPDATE OR DELETE ON enc_personal_attack_weapon_assistance
FOR EACH ROW EXECUTE FUNCTION enc_reject_personal_attack_weapon_assistance_mutation();

COMMENT ON TABLE enc_personal_attack_weapon_assistance IS
    'CE-COMBAT-022 instance-bound Laser Sight and default Intelligent Weapon modifiers.';
