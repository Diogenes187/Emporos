DO $$ DECLARE d text; BEGIN
 SELECT pg_get_constraintdef(oid) INTO STRICT d FROM pg_constraint
  WHERE conrelid='cmd_command'::regclass AND conname='cmd_command_command_type_check';
 ALTER TABLE cmd_command DROP CONSTRAINT cmd_command_command_type_check;
 EXECUTE format('ALTER TABLE cmd_command ADD CONSTRAINT cmd_command_command_type_check %s',
  replace(d,'CHECK (','CHECK (command_type=''perform_computer_basic_operation'' OR '));
END $$;
CREATE TABLE cmd_computer_basic_operation_receipt (
 command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
 actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
 operation_code text NOT NULL REFERENCES rule_computer_basic_operation(operation_code),
 target_reference text NOT NULL CHECK(btrim(target_reference)<>''),
 computer_skill_level smallint NOT NULL CHECK(computer_skill_level>=0),
 performed_without_check boolean NOT NULL CHECK(performed_without_check)
);
CREATE FUNCTION cmd_reject_computer_basic_operation_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Computer basic-operation receipts are immutable'; END $$;
CREATE TRIGGER cmd_computer_basic_operation_immutable BEFORE UPDATE OR DELETE ON cmd_computer_basic_operation_receipt FOR EACH ROW EXECUTE FUNCTION cmd_reject_computer_basic_operation_mutation();
