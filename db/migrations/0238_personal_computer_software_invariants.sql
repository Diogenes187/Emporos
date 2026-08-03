CREATE FUNCTION rule_validate_personal_software_profile()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE family rule_personal_software_family%ROWTYPE;
BEGIN
 SELECT * INTO STRICT family FROM rule_personal_software_family
  WHERE rule_id=NEW.software_rule_id;
 IF family.ranked<>(NEW.rating IS NOT NULL)
    OR (family.ranked AND (
        NEW.rating<family.minimum_published_rating
        OR NEW.rating>family.maximum_published_rating))
    OR NEW.rating_or_higher<>(
        family.maximum_is_open_ended
        AND NEW.rating=family.maximum_published_rating)
 THEN
   RAISE EXCEPTION 'Software profile does not match family rating bounds';
 END IF;
 RETURN NEW;
END;
$$;

CREATE TRIGGER rule_personal_software_profile_valid
BEFORE INSERT OR UPDATE ON rule_personal_software_profile
FOR EACH ROW EXECUTE FUNCTION rule_validate_personal_software_profile();

CREATE FUNCTION rule_validate_personal_software_family_profiles()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF EXISTS (
   SELECT 1 FROM rule_personal_software_profile profile
    WHERE profile.software_rule_id=NEW.rule_id
      AND (
        NEW.ranked<>(profile.rating IS NOT NULL)
        OR (NEW.ranked AND (
            profile.rating<NEW.minimum_published_rating
            OR profile.rating>NEW.maximum_published_rating))
        OR profile.rating_or_higher<>(
            NEW.maximum_is_open_ended
            AND profile.rating=NEW.maximum_published_rating))
 ) THEN
   RAISE EXCEPTION 'Software family change invalidates published profiles';
 END IF;
 RETURN NEW;
END;
$$;

CREATE TRIGGER rule_personal_software_family_profiles_valid
BEFORE UPDATE ON rule_personal_software_family
FOR EACH ROW EXECUTE FUNCTION
    rule_validate_personal_software_family_profiles();
