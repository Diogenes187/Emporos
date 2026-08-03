DO $$ DECLARE d text; BEGIN
 SELECT pg_get_constraintdef(oid) INTO STRICT d FROM pg_constraint
  WHERE conrelid='cmd_command'::regclass AND conname='cmd_command_command_type_check';
 ALTER TABLE cmd_command DROP CONSTRAINT cmd_command_command_type_check;
 EXECUTE format('ALTER TABLE cmd_command ADD CONSTRAINT cmd_command_command_type_check %s',
  replace(d,'CHECK (','CHECK (command_type=''resolve_liaison_negotiation'' OR '));
END $$;

CREATE TABLE camp_liaison_negotiation (
 negotiation_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
 campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
 scene_reference text NOT NULL CHECK(btrim(scene_reference)<>''),
 subject_reference text NOT NULL CHECK(btrim(subject_reference)<>''),
 negotiation_status text NOT NULL CHECK(negotiation_status IN ('resolved','tied')),
 winner_actor_id bigint REFERENCES actor_actor(actor_id),
 source_command_id bigint NOT NULL UNIQUE REFERENCES cmd_command(command_id),
 CHECK((negotiation_status='resolved')=(winner_actor_id IS NOT NULL))
);
CREATE TABLE cmd_liaison_negotiation_receipt (
 command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
 negotiation_id bigint NOT NULL UNIQUE REFERENCES camp_liaison_negotiation(negotiation_id),
 rule_id bigint NOT NULL REFERENCES rule_liaison_negotiation(rule_id),
 participant_count smallint NOT NULL CHECK(participant_count>=2),
 winning_total smallint NOT NULL,
 tied_at_winning_total boolean NOT NULL
);
CREATE TABLE cmd_liaison_negotiation_participant (
 command_id bigint NOT NULL REFERENCES cmd_liaison_negotiation_receipt(command_id),
 participant_order smallint NOT NULL CHECK(participant_order>0),
 actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
 characteristic_rule_id bigint NOT NULL REFERENCES rule_characteristic(rule_id),
 task_command_id bigint NOT NULL UNIQUE REFERENCES cmd_actor_task_receipt(command_id),
 check_total smallint NOT NULL,
 gained_advantage boolean NOT NULL,
 PRIMARY KEY(command_id,participant_order),
 UNIQUE(command_id,actor_id)
);
CREATE FUNCTION cmd_reject_liaison_negotiation_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Liaison negotiation receipts are immutable'; END $$;
CREATE TRIGGER camp_liaison_negotiation_immutable BEFORE UPDATE OR DELETE ON camp_liaison_negotiation FOR EACH ROW EXECUTE FUNCTION cmd_reject_liaison_negotiation_mutation();
CREATE TRIGGER cmd_liaison_negotiation_receipt_immutable BEFORE UPDATE OR DELETE ON cmd_liaison_negotiation_receipt FOR EACH ROW EXECUTE FUNCTION cmd_reject_liaison_negotiation_mutation();
CREATE TRIGGER cmd_liaison_negotiation_participant_immutable BEFORE UPDATE OR DELETE ON cmd_liaison_negotiation_participant FOR EACH ROW EXECUTE FUNCTION cmd_reject_liaison_negotiation_mutation();
