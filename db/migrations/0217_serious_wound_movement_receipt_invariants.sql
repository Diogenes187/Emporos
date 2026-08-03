CREATE FUNCTION cmd_validate_serious_wound_movement()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE serious boolean;
BEGIN
 SELECT combatant.seriously_wounded INTO STRICT serious
   FROM enc_personal_combatant combatant
  WHERE combatant.encounter_id=NEW.encounter_id
    AND combatant.actor_id=NEW.actor_id;
 IF serious AND (
      TG_TABLE_NAME<>'cmd_personal_move_receipt'
      OR NEW.round_metres_after>1.5
    ) THEN
   RAISE EXCEPTION 'Seriously wounded movement exceeds hobble/crawl rule';
 END IF;
 RETURN NEW;
END;
$$;
CREATE TRIGGER cmd_personal_move_serious_wound_validate
BEFORE INSERT ON cmd_personal_move_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_validate_serious_wound_movement();
CREATE TRIGGER cmd_species_flyer_move_serious_wound_validate
BEFORE INSERT ON cmd_species_flyer_move_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_validate_serious_wound_movement();
CREATE TRIGGER cmd_species_great_leap_serious_wound_validate
BEFORE INSERT ON cmd_species_great_leap_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_validate_serious_wound_movement();
