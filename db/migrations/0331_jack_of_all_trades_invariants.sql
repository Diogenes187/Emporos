CREATE FUNCTION cmd_validate_jack_of_all_trades_snapshot() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE trained integer; jot integer;
BEGIN SELECT skill_level INTO trained FROM actor_skill WHERE actor_id=NEW.actor_id AND skill_rule_id=NEW.skill_rule_id; SELECT COALESCE(s.skill_level,0) INTO jot FROM rule_jack_of_all_trades r LEFT JOIN actor_skill s ON s.skill_rule_id=r.skill_rule_id AND s.actor_id=NEW.actor_id;
 IF trained IS NOT NULL THEN IF NEW.base_skill_modifier<>trained OR NEW.skill_modifier<>trained OR NEW.jack_of_all_trades_reduction<>0 THEN RAISE EXCEPTION 'Trained task must not use Jack of All Trades'; END IF;
 ELSIF NEW.skill_rule_id IS NOT NULL AND (NEW.base_skill_modifier IS NULL OR NEW.jack_of_all_trades_level IS DISTINCT FROM jot) THEN RAISE EXCEPTION 'Untrained task Jack of All Trades snapshot mismatch'; END IF; RETURN NEW; END $$;
CREATE TRIGGER cmd_actor_task_jack_of_all_trades_valid BEFORE INSERT ON cmd_actor_task_receipt FOR EACH ROW EXECUTE FUNCTION cmd_validate_jack_of_all_trades_snapshot();
