DO $$ DECLARE d text; BEGIN
 SELECT pg_get_constraintdef(oid) INTO STRICT d FROM pg_constraint WHERE conrelid='cmd_command'::regclass AND conname='cmd_command_command_type_check';
 ALTER TABLE cmd_command DROP CONSTRAINT cmd_command_command_type_check;
 EXECUTE format('ALTER TABLE cmd_command ADD CONSTRAINT cmd_command_command_type_check %s',replace(d,'CHECK (','CHECK (command_type=''resolve_house_gambling'' OR '));
END $$;
CREATE TABLE cmd_house_gambling_receipt (
 command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
 task_command_id bigint NOT NULL UNIQUE REFERENCES cmd_actor_task_receipt(command_id),
 actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
 odds_rule_id bigint NOT NULL REFERENCES rule_gambling_house_odds(rule_id),
 venue_reference text NOT NULL CHECK(btrim(venue_reference)<>''),
 game_reference text NOT NULL CHECK(btrim(game_reference)<>''),
 bet_credits bigint NOT NULL CHECK(bet_credits>0),
 check_modifier smallint NOT NULL,
 natural_two boolean NOT NULL,
 won boolean NOT NULL,
 payoff_numerator smallint,
 payoff_denominator smallint,
 winnings_credits numeric(20,6) CHECK(winnings_credits IS NULL OR winnings_credits>=0),
 rigged_terms_reference text,
 CHECK(NOT natural_two OR NOT won),
 CHECK((won AND payoff_numerator IS NOT NULL AND winnings_credits=bet_credits*payoff_numerator::numeric/payoff_denominator)
    OR (NOT won AND winnings_credits=0)
    OR (won AND payoff_numerator IS NULL AND winnings_credits IS NULL AND btrim(rigged_terms_reference)<>''))
);
CREATE FUNCTION cmd_reject_house_gambling_receipt_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'House gambling receipts are immutable'; END $$;
CREATE TRIGGER cmd_house_gambling_receipt_immutable BEFORE UPDATE OR DELETE ON cmd_house_gambling_receipt FOR EACH ROW EXECUTE FUNCTION cmd_reject_house_gambling_receipt_mutation();
