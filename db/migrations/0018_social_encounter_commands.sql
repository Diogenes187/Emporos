ALTER TABLE cmd_command DROP CONSTRAINT cmd_command_command_type_check;
ALTER TABLE cmd_command ADD CONSTRAINT cmd_command_command_type_check CHECK (
    command_type IN (
        'resolve_personal_attack', 'apply_personal_damage',
        'create_encounter', 'transition_encounter_mode',
        'add_encounter_participant', 'set_encounter_attitude',
        'attempt_attitude_influence'
    )
);

ALTER TABLE cmd_random_draw DROP CONSTRAINT cmd_random_draw_draw_group_check;
ALTER TABLE cmd_random_draw ADD CONSTRAINT cmd_random_draw_draw_group_check CHECK (
    draw_group IN ('attack', 'damage', 'task')
);

ALTER TABLE cmd_domain_event DROP CONSTRAINT cmd_domain_event_event_type_check;
ALTER TABLE cmd_domain_event ADD CONSTRAINT cmd_domain_event_event_type_check CHECK (
    event_type IN (
        'personal_attack_hit', 'personal_attack_missed',
        'personal_damage_applied', 'encounter_created',
        'encounter_mode_transitioned', 'encounter_participant_added',
        'encounter_attitude_set', 'encounter_attitude_changed',
        'encounter_attitude_unchanged'
    )
);

CREATE TABLE cmd_encounter_participant_receipt (
    command_id          bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    encounter_id        bigint NOT NULL REFERENCES enc_encounter(encounter_id),
    actor_id            bigint NOT NULL REFERENCES actor_actor(actor_id),
    participant_role    text NOT NULL,
    side_code           text NOT NULL
);

CREATE TABLE cmd_attitude_set_receipt (
    command_id          bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    encounter_id        bigint NOT NULL REFERENCES enc_encounter(encounter_id),
    actor_id            bigint NOT NULL REFERENCES actor_actor(actor_id),
    attitude_rule_id    bigint NOT NULL REFERENCES rule_attitude(rule_id)
);

CREATE TABLE enc_influence_attempt (
    influence_attempt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    command_id          bigint NOT NULL UNIQUE REFERENCES cmd_command(command_id),
    encounter_id        bigint NOT NULL REFERENCES enc_encounter(encounter_id),
    acting_actor_id     bigint NOT NULL REFERENCES actor_actor(actor_id),
    target_actor_id     bigint NOT NULL REFERENCES actor_actor(actor_id),
    initial_attitude_rule_id bigint NOT NULL REFERENCES rule_attitude(rule_id),
    final_attitude_rule_id bigint NOT NULL REFERENCES rule_attitude(rule_id),
    skill_modifier      integer NOT NULL,
    characteristic_modifier integer NOT NULL,
    circumstance_modifier_total integer NOT NULL,
    difficulty_modifier integer NOT NULL,
    check_total         integer NOT NULL,
    target_number       integer NOT NULL,
    effect              integer NOT NULL,
    attitude_shift      integer NOT NULL,
    UNIQUE (encounter_id, acting_actor_id, target_actor_id),
    CHECK (acting_actor_id <> target_actor_id)
);

CREATE TABLE cmd_influence_modifier (
    command_id          bigint NOT NULL REFERENCES cmd_command(command_id),
    modifier_order      smallint NOT NULL CHECK (modifier_order > 0),
    modifier_value      integer NOT NULL,
    PRIMARY KEY (command_id, modifier_order)
);

COMMENT ON TABLE enc_influence_attempt IS
    'At most one influence attempt by an actor against a target in an encounter.';
