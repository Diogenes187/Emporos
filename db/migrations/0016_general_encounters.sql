CREATE TABLE rule_encounter_type (
    rule_id             bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    encounter_type_code text NOT NULL UNIQUE CHECK (
                            encounter_type_code IN (
                                'routine', 'legal', 'patron', 'random',
                                'rumor', 'scenario', 'animal', 'starship'
                            )
                        ),
    display_order       smallint NOT NULL UNIQUE CHECK (display_order > 0)
);

CREATE TABLE rule_attitude (
    rule_id             bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    attitude_code       text NOT NULL UNIQUE CHECK (
                            attitude_code IN (
                                'hostile', 'unfriendly', 'indifferent',
                                'friendly', 'helpful'
                            )
                        ),
    source_order        smallint NOT NULL UNIQUE CHECK (source_order > 0),
    meaning             text NOT NULL CHECK (btrim(meaning) <> '')
);

CREATE TABLE rule_attitude_influence_system (
    rule_id             bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    difficulty_rule_id  bigint NOT NULL REFERENCES rule_difficulty(rule_id),
    success_shift       smallint NOT NULL,
    exceptional_success_shift smallint NOT NULL,
    failure_shift       smallint NOT NULL,
    exceptional_failure_shift smallint NOT NULL,
    usual_attempts_per_scene smallint NOT NULL CHECK (
                            usual_attempts_per_scene > 0
                        ),
    can_force_player_character boolean NOT NULL
);

CREATE TABLE enc_encounter (
    encounter_id        bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id           uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    campaign_id         bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    encounter_type_rule_id bigint NOT NULL REFERENCES rule_encounter_type(rule_id),
    encounter_status    text NOT NULL DEFAULT 'active' CHECK (
                            encounter_status IN ('active', 'resolved')
                        ),
    current_mode        text NOT NULL CHECK (
                            current_mode IN (
                                'social', 'animal_reaction', 'starship',
                                'personal_combat'
                            )
                        ),
    created_at          timestamptz NOT NULL DEFAULT clock_timestamp(),
    resolved_at         timestamptz,
    CHECK (
        (encounter_status = 'active' AND resolved_at IS NULL)
        OR (encounter_status = 'resolved' AND resolved_at IS NOT NULL)
    )
);

CREATE TABLE enc_participant (
    encounter_id        bigint NOT NULL REFERENCES enc_encounter(encounter_id),
    actor_id            bigint NOT NULL REFERENCES actor_actor(actor_id),
    participant_role    text NOT NULL CHECK (
                            participant_role IN (
                                'player_character', 'non_player_character',
                                'animal', 'crew', 'other'
                            )
                        ),
    side_code           text NOT NULL CHECK (btrim(side_code) <> ''),
    aware               boolean,
    joined_at           timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (encounter_id, actor_id)
);

CREATE TABLE enc_attitude_state (
    encounter_id        bigint NOT NULL,
    actor_id            bigint NOT NULL,
    attitude_rule_id    bigint NOT NULL REFERENCES rule_attitude(rule_id),
    set_by              text NOT NULL CHECK (
                            set_by IN (
                                'referee', 'source_rule', 'influence_result',
                                'manual_override'
                            )
                        ),
    changed_at          timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (encounter_id, actor_id),
    FOREIGN KEY (encounter_id, actor_id)
        REFERENCES enc_participant(encounter_id, actor_id)
);

CREATE TABLE enc_mode_transition (
    mode_transition_id  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    encounter_id        bigint NOT NULL REFERENCES enc_encounter(encounter_id),
    transition_order    integer NOT NULL CHECK (transition_order > 0),
    from_mode           text NOT NULL CHECK (
                            from_mode IN (
                                'social', 'animal_reaction', 'starship',
                                'personal_combat'
                            )
                        ),
    to_mode             text NOT NULL CHECK (
                            to_mode IN (
                                'social', 'animal_reaction', 'starship',
                                'personal_combat'
                            )
                        ),
    transition_reason   text NOT NULL CHECK (btrim(transition_reason) <> ''),
    command_id          bigint REFERENCES cmd_command(command_id),
    occurred_at         timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (encounter_id, transition_order),
    CHECK (from_mode <> to_mode)
);

COMMENT ON TABLE enc_encounter IS
    'General encounter aggregate; personal combat is one possible mode.';
COMMENT ON TABLE enc_mode_transition IS
    'Explicit escalation/de-escalation history; narration cannot change mode.';
