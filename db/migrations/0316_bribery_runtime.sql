DO $$ DECLARE d text; BEGIN
 SELECT pg_get_constraintdef(oid) INTO STRICT d FROM pg_constraint WHERE conrelid='cmd_command'::regclass AND conname='cmd_command_command_type_check';
 ALTER TABLE cmd_command DROP CONSTRAINT cmd_command_command_type_check;
 EXECUTE format('ALTER TABLE cmd_command ADD CONSTRAINT cmd_command_command_type_check %s',replace(d,'CHECK (','CHECK (command_type=''attempt_bribery'' OR command_type=''resolve_bribery_consequence'' OR '));
END $$;

CREATE TABLE camp_bribery_case (
 bribery_case_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
 target_reference text NOT NULL CHECK(btrim(target_reference)<>''),
 incident_reference text NOT NULL CHECK(btrim(incident_reference)<>''),
 offense_rule_id bigint NOT NULL REFERENCES rule_bribery_offense(rule_id),
 law_level smallint NOT NULL CHECK(law_level>=0),
 minimum_bribe_roll smallint NOT NULL CHECK(minimum_bribe_roll BETWEEN 1 AND 6),
 minimum_bribe_credits bigint NOT NULL CHECK(minimum_bribe_credits>0),
 case_status text NOT NULL DEFAULT 'active' CHECK(case_status IN ('active','accepted','pending_social_check','cleared','charged')),
 attempts_completed smallint NOT NULL DEFAULT 0 CHECK(attempts_completed BETWEEN 0 AND 2),
 UNIQUE(actor_id,target_reference,incident_reference)
);
CREATE TABLE cmd_bribery_attempt_receipt (
 command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
 bribery_case_id bigint NOT NULL REFERENCES camp_bribery_case(bribery_case_id),
 task_command_id bigint UNIQUE REFERENCES cmd_actor_task_receipt(command_id),
 attempt_number smallint NOT NULL CHECK(attempt_number IN (1,2)),
 offer_credits bigint NOT NULL CHECK(offer_credits>0),
 minimum_bribe_roll smallint NOT NULL CHECK(minimum_bribe_roll BETWEEN 1 AND 6),
 credits_per_die smallint NOT NULL CHECK(credits_per_die IN (10,50,100,500)),
 minimum_bribe_credits bigint NOT NULL CHECK(minimum_bribe_credits=minimum_bribe_roll*credits_per_die),
 offense_modifier smallint NOT NULL,
 offer_modifier smallint NOT NULL CHECK(offer_modifier>=0),
 automatic_failure boolean NOT NULL,
 accepted boolean NOT NULL,
 CHECK(automatic_failure=(offer_credits<minimum_bribe_credits)),
 CHECK(NOT automatic_failure OR (task_command_id IS NULL AND NOT accepted)),
 UNIQUE(bribery_case_id,attempt_number)
);
CREATE TABLE cmd_bribery_consequence_receipt (
 command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
 bribery_case_id bigint NOT NULL UNIQUE REFERENCES camp_bribery_case(bribery_case_id),
 task_command_id bigint NOT NULL UNIQUE REFERENCES cmd_actor_task_receipt(command_id),
 charged_with_attempted_bribery boolean NOT NULL
);
CREATE FUNCTION cmd_reject_bribery_receipt_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Bribery receipts are immutable'; END $$;
CREATE TRIGGER cmd_bribery_attempt_receipt_immutable BEFORE UPDATE OR DELETE ON cmd_bribery_attempt_receipt FOR EACH ROW EXECUTE FUNCTION cmd_reject_bribery_receipt_mutation();
CREATE TRIGGER cmd_bribery_consequence_receipt_immutable BEFORE UPDATE OR DELETE ON cmd_bribery_consequence_receipt FOR EACH ROW EXECUTE FUNCTION cmd_reject_bribery_receipt_mutation();
