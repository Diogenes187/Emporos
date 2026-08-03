CREATE FUNCTION senc_reject_pursuit_full_tie()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.action_kind IN ('establish','break')
    AND NEW.acting_effect=NEW.opposing_effect
    AND NEW.acting_characteristic_value=NEW.opposing_characteristic_value THEN
   RAISE EXCEPTION 'Pursuit opposed check tie requires reroll' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;

CREATE TRIGGER senc_pursuit_full_tie_requires_reroll
BEFORE INSERT ON senc_pursuit_action_receipt
FOR EACH ROW EXECUTE FUNCTION senc_reject_pursuit_full_tie();
