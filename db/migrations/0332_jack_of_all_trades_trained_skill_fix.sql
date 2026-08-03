ALTER TABLE cmd_actor_task_receipt
 DROP CONSTRAINT cmd_actor_task_receipt_check6,
 ADD CHECK(
   (base_skill_modifier IS NULL
    AND jack_of_all_trades_level IS NULL
    AND jack_of_all_trades_reduction=0)
   OR
   (base_skill_modifier IS NOT NULL
    AND jack_of_all_trades_level IS NULL
    AND jack_of_all_trades_reduction=0
    AND skill_modifier=base_skill_modifier)
   OR
   (base_skill_modifier IS NOT NULL
    AND jack_of_all_trades_level IS NOT NULL
    AND skill_modifier=least(0,base_skill_modifier+jack_of_all_trades_reduction)
    AND jack_of_all_trades_reduction=least(
      -least(base_skill_modifier,0),jack_of_all_trades_level))
 );

CREATE OR REPLACE FUNCTION cmd_validate_jack_of_all_trades_snapshot()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE trained integer; jot integer;
BEGIN
 SELECT skill_level INTO trained FROM actor_skill
  WHERE actor_id=NEW.actor_id AND skill_rule_id=NEW.skill_rule_id;
 SELECT COALESCE(s.skill_level,0) INTO jot
   FROM rule_jack_of_all_trades r
   LEFT JOIN actor_skill s ON s.skill_rule_id=r.skill_rule_id
    AND s.actor_id=NEW.actor_id;
 IF trained IS NOT NULL THEN
  IF NEW.base_skill_modifier<>trained OR NEW.skill_modifier<>trained
     OR NEW.jack_of_all_trades_level IS NOT NULL
     OR NEW.jack_of_all_trades_reduction<>0 THEN
   RAISE EXCEPTION 'Trained task must not use Jack of All Trades';
  END IF;
 ELSIF NEW.skill_rule_id IS NOT NULL
       AND (NEW.base_skill_modifier IS NULL
            OR NEW.jack_of_all_trades_level IS DISTINCT FROM jot) THEN
  RAISE EXCEPTION 'Untrained task Jack of All Trades snapshot mismatch';
 END IF;
 RETURN NEW;
END $$;
