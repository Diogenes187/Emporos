DO $$ DECLARE d text; BEGIN SELECT pg_get_constraintdef(oid) INTO STRICT d FROM pg_constraint WHERE conrelid='cmd_command'::regclass AND conname='cmd_command_command_type_check'; ALTER TABLE cmd_command DROP CONSTRAINT cmd_command_command_type_check; EXECUTE format('ALTER TABLE cmd_command ADD CONSTRAINT cmd_command_command_type_check %s',replace(d,'CHECK (','CHECK (command_type=''resolve_navigation'' OR ')); END $$;

CREATE TABLE journey_navigation_solution (
    navigation_solution_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    journey_leg_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    navigator_actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    operation_kind text NOT NULL CHECK (operation_kind IN ('post_jump_fix','normal_course','jump_route')),
    task_command_id bigint NOT NULL UNIQUE REFERENCES cmd_actor_task_receipt(command_id),
    check_total smallint NOT NULL,
    effect smallint NOT NULL,
    succeeded boolean NOT NULL,
    source_command_id bigint NOT NULL UNIQUE REFERENCES cmd_command(command_id),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    FOREIGN KEY (journey_leg_id,campaign_id) REFERENCES journey_leg(journey_leg_id,campaign_id),
    FOREIGN KEY (navigator_actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id)
);

CREATE TABLE cmd_navigation_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    navigation_solution_id bigint NOT NULL UNIQUE REFERENCES journey_navigation_solution(navigation_solution_id),
    journey_leg_id bigint NOT NULL,
    navigator_actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    operation_kind text NOT NULL,
    task_command_id bigint NOT NULL UNIQUE REFERENCES cmd_actor_task_receipt(command_id),
    check_total smallint NOT NULL,
    effect smallint NOT NULL,
    succeeded boolean NOT NULL
);

ALTER TABLE journey_jump_attempt ADD COLUMN navigation_solution_id bigint REFERENCES journey_navigation_solution(navigation_solution_id);
