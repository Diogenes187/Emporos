DO $$ DECLARE d text; BEGIN SELECT pg_get_constraintdef(oid) INTO STRICT d FROM pg_constraint WHERE conrelid='cmd_command'::regclass AND conname='cmd_command_command_type_check'; ALTER TABLE cmd_command DROP CONSTRAINT cmd_command_command_type_check; EXECUTE format('ALTER TABLE cmd_command ADD CONSTRAINT cmd_command_command_type_check %s',replace(d,'CHECK (','CHECK (command_type=''begin_leadership_coordination'' OR command_type=''allocate_leadership_coordination'' OR ')); END $$;
CREATE TABLE camp_leadership_coordination (
 coordination_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
 campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
 leader_actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
 goal_reference text NOT NULL CHECK(btrim(goal_reference)<>''),
 pool_points_total smallint NOT NULL CHECK(pool_points_total>=1),
 pool_points_remaining smallint NOT NULL CHECK(pool_points_remaining BETWEEN 0 AND pool_points_total),
 coordination_status text NOT NULL CHECK(coordination_status IN ('active','allocated')),
 source_command_id bigint NOT NULL UNIQUE REFERENCES cmd_command(command_id),
 CHECK((coordination_status='allocated')=(pool_points_remaining=0)),
 UNIQUE(leader_actor_id,goal_reference)
);
CREATE TABLE cmd_leadership_coordination_receipt (
 command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),coordination_id bigint NOT NULL UNIQUE REFERENCES camp_leadership_coordination(coordination_id),leadership_task_command_id bigint NOT NULL UNIQUE REFERENCES cmd_actor_task_receipt(command_id),leader_actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),effect smallint NOT NULL,pool_points smallint NOT NULL CHECK(pool_points=greatest(1,effect))
);
CREATE TABLE camp_leadership_coordination_allocation (
 allocation_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,coordination_id bigint NOT NULL REFERENCES camp_leadership_coordination(coordination_id),recipient_actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),points smallint NOT NULL CHECK(points>0),allocation_status text NOT NULL DEFAULT 'pending' CHECK(allocation_status IN ('pending','consumed')),consumed_task_command_id bigint UNIQUE REFERENCES cmd_actor_task_receipt(command_id) DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE cmd_leadership_coordination_allocation_receipt (
 command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),allocation_id bigint NOT NULL UNIQUE REFERENCES camp_leadership_coordination_allocation(allocation_id),coordination_id bigint NOT NULL REFERENCES camp_leadership_coordination(coordination_id),recipient_actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),points smallint NOT NULL CHECK(points>0),remaining_before smallint NOT NULL,remaining_after smallint NOT NULL CHECK(remaining_after=remaining_before-points)
);
CREATE FUNCTION cmd_reject_leadership_coordination_receipt_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Leadership coordination receipts are immutable'; END $$;
CREATE TRIGGER cmd_leadership_coordination_receipt_immutable BEFORE UPDATE OR DELETE ON cmd_leadership_coordination_receipt FOR EACH ROW EXECUTE FUNCTION cmd_reject_leadership_coordination_receipt_mutation();
CREATE TRIGGER cmd_leadership_coordination_allocation_receipt_immutable BEFORE UPDATE OR DELETE ON cmd_leadership_coordination_allocation_receipt FOR EACH ROW EXECUTE FUNCTION cmd_reject_leadership_coordination_receipt_mutation();
