DO $$ DECLARE d text; BEGIN SELECT pg_get_constraintdef(oid) INTO STRICT d FROM pg_constraint WHERE conrelid='cmd_command'::regclass AND conname='cmd_command_command_type_check'; ALTER TABLE cmd_command DROP CONSTRAINT cmd_command_command_type_check; EXECUTE format('ALTER TABLE cmd_command ADD CONSTRAINT cmd_command_command_type_check %s',replace(d,'CHECK (','CHECK (command_type IN (''start_trade_work_week'',''complete_trade_work_week'') OR ')); END $$;
CREATE TABLE camp_trade_work_week (
 work_week_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
 campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id), actor_id bigint NOT NULL, skill_rule_id bigint NOT NULL REFERENCES rule_trade_work_skill(skill_rule_id),
 employer_account_id bigint NOT NULL, worker_account_id bigint NOT NULL, started_day bigint NOT NULL, started_second integer NOT NULL CHECK(started_second BETWEEN 0 AND 86399),
 work_status text NOT NULL CHECK(work_status IN ('active','completed')), completed_day bigint, completed_second integer CHECK(completed_second BETWEEN 0 AND 86399),
 payment_transaction_id bigint UNIQUE REFERENCES fin_transaction(transaction_id), source_command_id bigint NOT NULL UNIQUE REFERENCES cmd_command(command_id), completion_command_id bigint UNIQUE REFERENCES cmd_command(command_id),
 FOREIGN KEY(actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id), FOREIGN KEY(employer_account_id,campaign_id) REFERENCES fin_account(account_id,campaign_id), FOREIGN KEY(worker_account_id,campaign_id) REFERENCES fin_account(account_id,campaign_id),
 CHECK(employer_account_id<>worker_account_id), CHECK((work_status='completed')=(completed_day IS NOT NULL AND completed_second IS NOT NULL AND payment_transaction_id IS NOT NULL AND completion_command_id IS NOT NULL))
);
CREATE UNIQUE INDEX camp_trade_work_one_active_actor ON camp_trade_work_week(actor_id) WHERE work_status='active';
CREATE TABLE cmd_trade_work_start_receipt(command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),work_week_id bigint NOT NULL UNIQUE REFERENCES camp_trade_work_week(work_week_id),skill_level smallint NOT NULL CHECK(skill_level>=0));
CREATE TABLE cmd_trade_work_complete_receipt(command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),work_week_id bigint NOT NULL UNIQUE REFERENCES camp_trade_work_week(work_week_id),elapsed_seconds bigint NOT NULL CHECK(elapsed_seconds>=604800),wage_credits integer NOT NULL CHECK(wage_credits=250),payment_transaction_id bigint NOT NULL UNIQUE REFERENCES fin_transaction(transaction_id));
CREATE FUNCTION cmd_reject_trade_work_receipt_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Trade work receipts are immutable'; END $$;
CREATE TRIGGER cmd_trade_work_start_immutable BEFORE UPDATE OR DELETE ON cmd_trade_work_start_receipt FOR EACH ROW EXECUTE FUNCTION cmd_reject_trade_work_receipt_mutation();
CREATE TRIGGER cmd_trade_work_complete_immutable BEFORE UPDATE OR DELETE ON cmd_trade_work_complete_receipt FOR EACH ROW EXECUTE FUNCTION cmd_reject_trade_work_receipt_mutation();
