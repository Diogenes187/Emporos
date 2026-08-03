CREATE TABLE camp_campaign (
    campaign_id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id           uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    name                text NOT NULL CHECK (btrim(name) <> ''),
    created_at          timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE actor_actor (
    actor_id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id           uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    campaign_id         bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    name                text NOT NULL CHECK (btrim(name) <> ''),
    controller_reference text NOT NULL CHECK (btrim(controller_reference) <> ''),
    damage_sequence_started boolean NOT NULL DEFAULT false,
    concurrency_version bigint NOT NULL DEFAULT 1 CHECK (concurrency_version > 0),
    UNIQUE (actor_id, campaign_id)
);

CREATE TABLE actor_characteristic (
    actor_id            bigint NOT NULL REFERENCES actor_actor(actor_id),
    characteristic_rule_id bigint NOT NULL REFERENCES rule_characteristic(rule_id),
    maximum_value       smallint NOT NULL CHECK (maximum_value >= 0),
    current_value       smallint NOT NULL CHECK (current_value >= 0),
    PRIMARY KEY (actor_id, characteristic_rule_id),
    CHECK (current_value <= maximum_value)
);

ALTER TABLE cmd_attack_receipt
    ADD COLUMN target_actor_id bigint REFERENCES actor_actor(actor_id);

CREATE TABLE health_damage_instance (
    damage_instance_id  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    attack_command_id   bigint NOT NULL UNIQUE REFERENCES cmd_attack_receipt(command_id),
    target_actor_id     bigint NOT NULL REFERENCES actor_actor(actor_id),
    penetrating_damage  integer NOT NULL CHECK (penetrating_damage > 0),
    allocation_status   text NOT NULL DEFAULT 'pending' CHECK (
                            allocation_status IN ('pending', 'applied')
                        ),
    created_at          timestamptz NOT NULL DEFAULT clock_timestamp(),
    applied_at          timestamptz,
    CHECK (
        (allocation_status = 'pending' AND applied_at IS NULL)
        OR (allocation_status = 'applied' AND applied_at IS NOT NULL)
    )
);

CREATE TABLE health_damage_allocation (
    damage_instance_id  bigint NOT NULL
                        REFERENCES health_damage_instance(damage_instance_id),
    characteristic_rule_id bigint NOT NULL
                        REFERENCES rule_characteristic(rule_id),
    allocated_damage    integer NOT NULL CHECK (allocated_damage > 0),
    resulting_value     integer NOT NULL CHECK (resulting_value >= 0),
    allocation_order    smallint NOT NULL CHECK (allocation_order > 0),
    PRIMARY KEY (damage_instance_id, characteristic_rule_id),
    UNIQUE (damage_instance_id, allocation_order)
);

ALTER TABLE cmd_command DROP CONSTRAINT cmd_command_command_type_check;
ALTER TABLE cmd_command ADD CONSTRAINT cmd_command_command_type_check CHECK (
    command_type IN ('resolve_personal_attack', 'apply_personal_damage')
);

ALTER TABLE cmd_domain_event DROP CONSTRAINT cmd_domain_event_event_type_check;
ALTER TABLE cmd_domain_event ADD CONSTRAINT cmd_domain_event_event_type_check CHECK (
    event_type IN (
        'personal_attack_hit', 'personal_attack_missed',
        'personal_damage_applied'
    )
);

CREATE TABLE cmd_damage_receipt (
    command_id          bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    damage_instance_id  bigint NOT NULL UNIQUE
                        REFERENCES health_damage_instance(damage_instance_id),
    target_actor_id     bigint NOT NULL REFERENCES actor_actor(actor_id),
    total_damage        integer NOT NULL CHECK (total_damage > 0),
    actor_version_before bigint NOT NULL CHECK (actor_version_before > 0),
    actor_version_after bigint NOT NULL CHECK (
                            actor_version_after = actor_version_before + 1
                        )
);

COMMENT ON TABLE health_damage_allocation IS
    'Player-selected, source-validated allocation of penetrating personal damage.';
