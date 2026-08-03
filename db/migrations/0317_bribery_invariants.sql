DO $$ DECLARE d text; BEGIN
 SELECT pg_get_constraintdef(oid) INTO STRICT d FROM pg_constraint WHERE conrelid='cmd_random_draw'::regclass AND conname='cmd_random_draw_draw_group_check';
 ALTER TABLE cmd_random_draw DROP CONSTRAINT cmd_random_draw_draw_group_check;
 EXECUTE format('ALTER TABLE cmd_random_draw ADD CONSTRAINT cmd_random_draw_draw_group_check %s',replace(d,'CHECK (','CHECK (draw_group=''bribery_minimum'' OR '));
END $$;
CREATE FUNCTION cmd_validate_bribery_attempt() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE k camp_bribery_case%ROWTYPE; prior bigint;
BEGIN SELECT * INTO STRICT k FROM camp_bribery_case WHERE bribery_case_id=NEW.bribery_case_id;
 IF NEW.minimum_bribe_roll<>k.minimum_bribe_roll OR NEW.minimum_bribe_credits<>k.minimum_bribe_credits OR NEW.offense_modifier<>(SELECT check_modifier FROM rule_bribery_offense WHERE rule_id=k.offense_rule_id) THEN RAISE EXCEPTION 'Bribery receipt conflicts with case or offense rule'; END IF;
 IF NEW.attempt_number=2 THEN SELECT offer_credits INTO STRICT prior FROM cmd_bribery_attempt_receipt WHERE bribery_case_id=NEW.bribery_case_id AND attempt_number=1; IF NEW.offer_credits<>prior*2 THEN RAISE EXCEPTION 'Second bribe must double first offer'; END IF; END IF;
 RETURN NEW; END $$;
CREATE TRIGGER cmd_bribery_attempt_valid BEFORE INSERT ON cmd_bribery_attempt_receipt FOR EACH ROW EXECUTE FUNCTION cmd_validate_bribery_attempt();
