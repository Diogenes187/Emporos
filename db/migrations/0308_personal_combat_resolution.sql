DO $$ DECLARE d text; BEGIN
 SELECT pg_get_constraintdef(oid) INTO STRICT d FROM pg_constraint
 WHERE conrelid='cmd_command'::regclass AND conname='cmd_command_command_type_check';
 ALTER TABLE cmd_command DROP CONSTRAINT cmd_command_command_type_check;
 EXECUTE format('ALTER TABLE cmd_command ADD CONSTRAINT cmd_command_command_type_check %s',
   replace(d,'CHECK (','CHECK (command_type=''resolve_personal_combat'' OR '));
 SELECT pg_get_constraintdef(oid) INTO STRICT d FROM pg_constraint
 WHERE conrelid='cmd_domain_event'::regclass AND conname='cmd_domain_event_event_type_check';
 ALTER TABLE cmd_domain_event DROP CONSTRAINT cmd_domain_event_event_type_check;
 EXECUTE format('ALTER TABLE cmd_domain_event ADD CONSTRAINT cmd_domain_event_event_type_check %s',
   replace(d,'CHECK (','CHECK (event_type=''personal_combat_resolved'' OR '));
END $$;

CREATE TABLE rule_personal_conflict_avoidance (
 rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
 avoiding_group_must_be_aware boolean NOT NULL CHECK(avoiding_group_must_be_aware),
 opposing_group_must_be_unaware boolean NOT NULL CHECK(opposing_group_must_be_unaware),
 voluntary boolean NOT NULL CHECK(voluntary),
 ends_conflict boolean NOT NULL CHECK(ends_conflict)
);

CREATE TABLE cmd_personal_combat_resolution_receipt (
 command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
 encounter_resolution_id bigint NOT NULL UNIQUE REFERENCES enc_resolution(encounter_resolution_id),
 encounter_id bigint NOT NULL UNIQUE REFERENCES enc_personal_combat(encounter_id),
 outcome_kind text NOT NULL,
 winning_side_code text,
 avoiding_side_code text,
 opposing_side_code text,
 initiator_reference text NOT NULL CHECK(btrim(initiator_reference)<>''),
 referee_reference text NOT NULL CHECK(btrim(referee_reference)<>''),
 resolution_summary text NOT NULL CHECK(btrim(resolution_summary)<>''),
 resolved_at timestamptz NOT NULL,
 CHECK ((outcome_kind='avoided' AND avoiding_side_code IS NOT NULL
         AND opposing_side_code IS NOT NULL AND winning_side_code IS NULL)
        OR (outcome_kind<>'avoided' AND avoiding_side_code IS NULL
            AND opposing_side_code IS NULL))
);

CREATE FUNCTION cmd_reject_personal_combat_resolution_receipt_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Personal combat resolution receipts are immutable'; END $$;
CREATE TRIGGER cmd_personal_combat_resolution_receipt_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_combat_resolution_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_personal_combat_resolution_receipt_mutation();

COMMENT ON TABLE cmd_personal_combat_resolution_receipt IS
 'CE-COMBAT-026 immutable command boundary for avoided and referee-resolved personal combat.';
