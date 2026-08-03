CREATE FUNCTION cmd_validate_competitive_gambling_game() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
 IF NEW.winner_actor_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM actor_actor a WHERE a.actor_id=NEW.winner_actor_id AND a.campaign_id=NEW.campaign_id) THEN RAISE EXCEPTION 'Gambling winner belongs to another campaign'; END IF; RETURN NEW; END $$;
CREATE TRIGGER camp_competitive_gambling_game_valid BEFORE INSERT ON camp_competitive_gambling_game FOR EACH ROW EXECUTE FUNCTION cmd_validate_competitive_gambling_game();
