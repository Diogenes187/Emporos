CREATE FUNCTION camp_validate_book1_vehicle_instance()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE profile_minimum_tech_level smallint;
BEGIN
 SELECT minimum_tech_level INTO profile_minimum_tech_level
   FROM rule_book1_vehicle_profile
  WHERE rule_id=NEW.vehicle_profile_rule_id;
 IF NEW.manufactured_tech_level<profile_minimum_tech_level THEN
   RAISE EXCEPTION
     'Vehicle manufacturing TL is below the Book 1 profile minimum';
 END IF;
 IF TG_OP='UPDATE'
    AND (NEW.campaign_id,NEW.vehicle_profile_rule_id,
         NEW.manufactured_tech_level) IS DISTINCT FROM
        (OLD.campaign_id,OLD.vehicle_profile_rule_id,
         OLD.manufactured_tech_level)
    AND EXISTS (
        SELECT 1 FROM cmd_book1_vehicle_option_receipt
         WHERE vehicle_instance_id=OLD.vehicle_instance_id)
 THEN
   RAISE EXCEPTION
     'Vehicle identity and TL are immutable after option installation';
 END IF;
 RETURN NEW;
END;
$$;

CREATE TRIGGER camp_book1_vehicle_instance_valid
BEFORE INSERT OR UPDATE ON camp_book1_vehicle_instance
FOR EACH ROW EXECUTE FUNCTION camp_validate_book1_vehicle_instance();

COMMENT ON FUNCTION camp_validate_book1_vehicle_instance() IS
    'CE-EQUIP-027 protects profile TL and installed-option snapshots.';
