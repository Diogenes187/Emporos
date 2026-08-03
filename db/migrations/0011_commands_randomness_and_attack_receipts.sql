CREATE TABLE cmd_command (
    command_id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id           uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    command_type        text NOT NULL CHECK (
                            command_type IN ('resolve_personal_attack')
                        ),
    initiator_reference text NOT NULL CHECK (btrim(initiator_reference) <> ''),
    idempotency_key     text NOT NULL CHECK (btrim(idempotency_key) <> ''),
    command_status      text NOT NULL DEFAULT 'pending' CHECK (
                            command_status IN (
                                'pending', 'completed', 'rejected', 'failed'
                            )
                        ),
    created_at          timestamptz NOT NULL DEFAULT clock_timestamp(),
    completed_at        timestamptz,
    UNIQUE (initiator_reference, idempotency_key),
    CHECK (
        (command_status = 'pending' AND completed_at IS NULL)
        OR (command_status <> 'pending' AND completed_at IS NOT NULL)
    )
);

CREATE TABLE cmd_random_draw (
    random_draw_id      bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    command_id          bigint NOT NULL REFERENCES cmd_command(command_id),
    draw_group          text NOT NULL CHECK (
                            draw_group IN ('attack', 'damage')
                        ),
    draw_order          smallint NOT NULL CHECK (draw_order > 0),
    die_sides           smallint NOT NULL CHECK (die_sides > 1),
    result              smallint NOT NULL,
    UNIQUE (command_id, draw_group, draw_order),
    CHECK (result >= 1 AND result <= die_sides)
);

CREATE TABLE cmd_attack_receipt (
    command_id          bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    weapon_rule_id      bigint NOT NULL REFERENCES inv_weapon_definition(item_rule_id),
    armor_rule_id       bigint NOT NULL REFERENCES inv_armor_definition(item_rule_id),
    attack_profile_code text NOT NULL REFERENCES combat_attack_profile,
    range_band_rule_id  bigint NOT NULL REFERENCES combat_range_band(rule_id),
    skill_modifier      integer NOT NULL,
    characteristic_modifier integer NOT NULL,
    circumstance_modifier_total integer NOT NULL,
    difficulty_modifier integer NOT NULL,
    attack_total        integer NOT NULL,
    target_number       integer NOT NULL,
    effect              integer NOT NULL,
    hit                 boolean NOT NULL,
    rolled_damage       integer NOT NULL CHECK (rolled_damage >= 0),
    effect_damage       integer NOT NULL,
    raw_damage          integer NOT NULL CHECK (raw_damage >= 0),
    armor_rating        integer NOT NULL CHECK (armor_rating >= 0),
    penetrating_damage  integer NOT NULL CHECK (penetrating_damage >= 0),
    exceptional_minimum_applied boolean NOT NULL,
    CHECK (
        (hit AND raw_damage = rolled_damage + effect_damage)
        OR (NOT hit AND rolled_damage = 0 AND effect_damage = 0
            AND raw_damage = 0 AND penetrating_damage = 0)
    )
);

CREATE TABLE cmd_domain_event (
    domain_event_id     bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    command_id          bigint NOT NULL REFERENCES cmd_command(command_id),
    event_order         smallint NOT NULL CHECK (event_order > 0),
    event_type          text NOT NULL CHECK (
                            event_type IN (
                                'personal_attack_hit', 'personal_attack_missed'
                            )
                        ),
    occurred_at         timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (command_id, event_order)
);

COMMENT ON TABLE cmd_random_draw IS
    'Every mechanically consumed die is recorded once against its command.';
COMMENT ON TABLE cmd_attack_receipt IS
    'Relational, reproducible explanation of a committed personal attack.';
