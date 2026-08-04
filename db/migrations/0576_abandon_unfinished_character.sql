ALTER TABLE actor_actor
    ADD COLUMN lifecycle_status text NOT NULL DEFAULT 'active' CHECK (
        lifecycle_status IN ('active','abandoned')
    );

INSERT INTO cmd_command_type VALUES
    ('abandon_unfinished_character','Abandon unfinished character');

INSERT INTO cmd_domain_event_type VALUES
    ('unfinished_character_abandoned','Unfinished character abandoned');

CREATE TABLE cmd_character_abandonment_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    actor_id bigint NOT NULL UNIQUE REFERENCES actor_actor(actor_id),
    actor_version_before bigint NOT NULL CHECK (actor_version_before>0),
    actor_version_after bigint NOT NULL CHECK (
        actor_version_after=actor_version_before+1
    )
);

COMMENT ON COLUMN actor_actor.lifecycle_status IS
    'Recoverable visibility state; abandoned creation drafts remain audited.';
