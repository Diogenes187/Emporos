ALTER TABLE camp_campaign
    ADD COLUMN owner_reference text;

ALTER TABLE camp_campaign ADD CONSTRAINT camp_campaign_owner_reference_check
    CHECK (owner_reference IS NULL OR btrim(owner_reference) <> '');

ALTER TABLE cmd_command DROP CONSTRAINT cmd_command_command_type_check;
ALTER TABLE cmd_command ADD CONSTRAINT cmd_command_command_type_check CHECK (
    command_type IN (
        'resolve_personal_attack', 'apply_personal_damage',
        'create_encounter', 'transition_encounter_mode'
    )
);

ALTER TABLE cmd_domain_event DROP CONSTRAINT cmd_domain_event_event_type_check;
ALTER TABLE cmd_domain_event ADD CONSTRAINT cmd_domain_event_event_type_check CHECK (
    event_type IN (
        'personal_attack_hit', 'personal_attack_missed',
        'personal_damage_applied', 'encounter_created',
        'encounter_mode_transitioned'
    )
);

CREATE TABLE cmd_encounter_receipt (
    command_id          bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    encounter_id        bigint NOT NULL UNIQUE REFERENCES enc_encounter(encounter_id),
    initial_mode        text NOT NULL
);

CREATE TABLE cmd_encounter_transition_receipt (
    command_id          bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    mode_transition_id  bigint NOT NULL UNIQUE
                        REFERENCES enc_mode_transition(mode_transition_id),
    encounter_id        bigint NOT NULL REFERENCES enc_encounter(encounter_id),
    from_mode           text NOT NULL,
    to_mode             text NOT NULL
);
