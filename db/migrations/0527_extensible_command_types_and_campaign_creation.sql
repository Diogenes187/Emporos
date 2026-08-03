CREATE TABLE cmd_command_type (
    command_type text PRIMARY KEY CHECK (
        command_type ~ '^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$'
    ),
    description text NOT NULL CHECK (btrim(description) <> '')
);

DO $$
DECLARE
    definition text;
BEGIN
    SELECT pg_get_constraintdef(oid)
      INTO definition
      FROM pg_constraint
     WHERE conrelid='cmd_command'::regclass
       AND conname='cmd_command_command_type_check';

    INSERT INTO cmd_command_type (command_type,description)
    SELECT DISTINCT capture[1],initcap(replace(capture[1],'_',' '))
      FROM regexp_matches(
          definition,
          '''([a-z][a-z0-9]*(?:_[a-z0-9]+)*)''::text',
          'g'
      ) AS capture;
END;
$$;

INSERT INTO cmd_command_type VALUES
    ('create_campaign','Create campaign');

ALTER TABLE cmd_command
    DROP CONSTRAINT cmd_command_command_type_check,
    ADD CONSTRAINT cmd_command_type_fk FOREIGN KEY (command_type)
        REFERENCES cmd_command_type(command_type);

CREATE TABLE cmd_domain_event_type (
    event_type text PRIMARY KEY CHECK (
        event_type ~ '^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$'
    ),
    description text NOT NULL CHECK (btrim(description) <> '')
);

DO $$
DECLARE
    definition text;
BEGIN
    SELECT pg_get_constraintdef(oid)
      INTO definition
      FROM pg_constraint
     WHERE conrelid='cmd_domain_event'::regclass
       AND conname='cmd_domain_event_event_type_check';

    INSERT INTO cmd_domain_event_type (event_type,description)
    SELECT DISTINCT capture[1],initcap(replace(capture[1],'_',' '))
      FROM regexp_matches(
          definition,
          '''([a-z][a-z0-9]*(?:_[a-z0-9]+)*)''::text',
          'g'
      ) AS capture;
END;
$$;

INSERT INTO cmd_domain_event_type VALUES
    ('campaign_created','Campaign created');

ALTER TABLE cmd_domain_event
    DROP CONSTRAINT cmd_domain_event_event_type_check,
    ADD CONSTRAINT cmd_domain_event_type_fk FOREIGN KEY (event_type)
        REFERENCES cmd_domain_event_type(event_type);

CREATE TABLE cmd_campaign_creation_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    campaign_id bigint NOT NULL UNIQUE REFERENCES camp_campaign(campaign_id),
    initial_day_number bigint NOT NULL,
    initial_second_of_day integer NOT NULL CHECK (
        initial_second_of_day BETWEEN 0 AND 86399
    )
);

COMMENT ON TABLE cmd_command_type IS
    'Extensible registry replacing the monolithic command-type CHECK constraint.';
COMMENT ON TABLE cmd_domain_event_type IS
    'Extensible registry replacing the monolithic event-type CHECK constraint.';
COMMENT ON TABLE cmd_campaign_creation_receipt IS
    'Audited creation of a campaign and its authoritative clock.';

