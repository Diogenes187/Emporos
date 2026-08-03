ALTER TABLE enc_personal_combatant
    ADD COLUMN seriously_wounded boolean NOT NULL DEFAULT false;

CREATE FUNCTION enc_validate_serious_wound_snapshot()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE expected boolean;
BEGIN
 SELECT injury.injury_status='seriously_wounded' INTO expected
   FROM health_actor_injury_status injury
  WHERE injury.actor_id=NEW.actor_id;
 expected := COALESCE(expected,false);
 IF NEW.seriously_wounded<>expected THEN
   RAISE EXCEPTION 'Serious-wound combat snapshot does not match actor state';
 END IF;
 RETURN NEW;
END;
$$;
CREATE TRIGGER enc_personal_combatant_serious_wound_validate
BEFORE INSERT OR UPDATE OF seriously_wounded ON enc_personal_combatant
FOR EACH ROW EXECUTE FUNCTION enc_validate_serious_wound_snapshot();

COMMENT ON COLUMN enc_personal_combatant.seriously_wounded IS
    'Current CE-COMBAT-013 restriction snapshot, refreshed on health/round changes.';
