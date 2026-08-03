ALTER TABLE enc_personal_attack_weapon_assistance
  ADD CONSTRAINT enc_personal_attack_weapon_assistance_suppression_complete
  CHECK (
    (intelligent_weapon_suppressed
     AND intelligent_weapon_installed
     AND intelligent_weapon_modifier=0
     AND suppression_referee_reference IS NOT NULL
     AND btrim(suppression_referee_reference)<>''
     AND suppression_reason IS NOT NULL
     AND btrim(suppression_reason)<>'')
    OR
    (NOT intelligent_weapon_suppressed
     AND suppression_referee_reference IS NULL
     AND suppression_reason IS NULL)
  );

CREATE OR REPLACE FUNCTION enc_validate_personal_attack_weapon_assistance()
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
    OR NEW.laser_sight_modifier<>(
       CASE WHEN laser_installed AND attack.aim_modifier>0 THEN 1 ELSE 0 END)
    OR NEW.intelligent_weapon_modifier<>(
       CASE WHEN intelligent_installed AND NOT NEW.intelligent_weapon_suppressed
            THEN 1 ELSE 0 END)
    OR (NEW.intelligent_weapon_suppressed
        AND NEW.suppression_referee_reference<>owner_reference) THEN
   RAISE EXCEPTION 'Weapon assistance does not match attack, custody, options, or referee';
 END IF;
 RETURN NEW;
END; $$;

COMMENT ON CONSTRAINT
  enc_personal_attack_weapon_assistance_suppression_complete
  ON enc_personal_attack_weapon_assistance IS
  'CE-COMBAT-022 requires an attributable referee reason whenever the normal Intelligent Weapon +1 is outside program tolerance.';
