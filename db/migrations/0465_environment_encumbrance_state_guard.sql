CREATE OR REPLACE FUNCTION actor_guard_encumbrance_state() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF pg_trigger_depth()<2 THEN
  RAISE EXCEPTION 'Encumbrance state changes require an immutable receipt' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
