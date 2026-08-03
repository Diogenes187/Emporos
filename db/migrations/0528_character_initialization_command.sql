INSERT INTO cmd_command_type VALUES
    ('initialize_character','Initialize character');

INSERT INTO cmd_domain_event_type VALUES
    ('character_initialized','Character initialized');

CREATE TABLE cmd_random_draw_group (
    draw_group text PRIMARY KEY CHECK (
        draw_group ~ '^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$'
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
     WHERE conrelid='cmd_random_draw'::regclass
       AND conname='cmd_random_draw_draw_group_check';

    INSERT INTO cmd_random_draw_group (draw_group,description)
    SELECT DISTINCT capture[1],initcap(replace(capture[1],'_',' '))
      FROM regexp_matches(
          definition,
          '''([a-z][a-z0-9]*(?:_[a-z0-9]+)*)''::text',
          'g'
      ) AS capture;
END;
$$;

INSERT INTO cmd_random_draw_group VALUES
    ('character_creation','Character creation');

ALTER TABLE cmd_random_draw
    DROP CONSTRAINT cmd_random_draw_draw_group_check,
    ADD CONSTRAINT cmd_random_draw_group_fk FOREIGN KEY (draw_group)
        REFERENCES cmd_random_draw_group(draw_group);

CREATE TABLE cmd_character_initialization_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    actor_id bigint NOT NULL UNIQUE,
    character_name text NOT NULL CHECK (btrim(character_name) <> ''),
    actor_version_after bigint NOT NULL CHECK (actor_version_after=1),
    FOREIGN KEY (actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id)
);

CREATE TABLE cmd_character_initialization_score (
    command_id bigint NOT NULL REFERENCES
        cmd_character_initialization_receipt(command_id),
    characteristic_rule_id bigint NOT NULL REFERENCES
        rule_characteristic(rule_id),
    display_order smallint NOT NULL CHECK (display_order>0),
    dice_total smallint NOT NULL CHECK (dice_total>0),
    resulting_score smallint NOT NULL CHECK (resulting_score>=0),
    PRIMARY KEY (command_id,characteristic_rule_id),
    UNIQUE (command_id,display_order)
);

COMMENT ON TABLE cmd_character_initialization_receipt IS
    'Audited creation of a player-controlled actor before lifepath entry.';
COMMENT ON TABLE cmd_character_initialization_score IS
    'Source-defined initial characteristic scores linked to recorded draws.';

