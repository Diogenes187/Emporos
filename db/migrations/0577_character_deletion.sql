ALTER TABLE actor_actor
    DROP CONSTRAINT actor_actor_lifecycle_status_check,
    ADD CONSTRAINT actor_actor_lifecycle_status_check CHECK (
        lifecycle_status IN ('active','abandoned','deleted')
    );

INSERT INTO cmd_command_type VALUES ('delete_character','Delete character');
INSERT INTO cmd_domain_event_type VALUES ('character_deleted','Character deleted');

CREATE TABLE cmd_character_deletion_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    actor_id bigint NOT NULL UNIQUE REFERENCES actor_actor(actor_id),
    actor_version_before bigint NOT NULL CHECK (actor_version_before>0),
    actor_version_after bigint NOT NULL CHECK (
        actor_version_after=actor_version_before+1
    ),
    deleted_character_name text NOT NULL CHECK (btrim(deleted_character_name)<>'')
);

COMMENT ON TABLE cmd_character_deletion_receipt IS
    'Permanent gameplay deletion retaining a tombstone for relational history.';
