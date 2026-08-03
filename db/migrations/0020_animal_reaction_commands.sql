CREATE TABLE actor_animal_profile (
    actor_id            bigint PRIMARY KEY REFERENCES actor_actor(actor_id),
    subtype_rule_id     bigint NOT NULL REFERENCES rule_animal_subtype(rule_id),
    creature_definition_code text NOT NULL CHECK (
                            btrim(creature_definition_code) <> ''
                        )
);

CREATE TABLE enc_animal_reaction_context (
    encounter_id        bigint NOT NULL REFERENCES enc_encounter(encounter_id),
    animal_actor_id     bigint NOT NULL REFERENCES actor_animal_profile(actor_id),
    context_version     integer NOT NULL DEFAULT 1 CHECK (context_version > 0),
    animals_outnumber_characters boolean NOT NULL,
    animal_has_surprise boolean NOT NULL,
    animal_is_surprised boolean NOT NULL,
    animal_bigger_than_character boolean NOT NULL,
    attack_possible     boolean NOT NULL,
    PRIMARY KEY (encounter_id, animal_actor_id),
    CHECK (NOT (animal_has_surprise AND animal_is_surprised))
);

ALTER TABLE cmd_command DROP CONSTRAINT cmd_command_command_type_check;
ALTER TABLE cmd_command ADD CONSTRAINT cmd_command_command_type_check CHECK (
    command_type IN (
        'resolve_personal_attack', 'apply_personal_damage',
        'create_encounter', 'transition_encounter_mode',
        'add_encounter_participant', 'set_encounter_attitude',
        'attempt_attitude_influence', 'set_animal_reaction_context',
        'resolve_animal_reaction'
    )
);

ALTER TABLE cmd_domain_event DROP CONSTRAINT cmd_domain_event_event_type_check;
ALTER TABLE cmd_domain_event ADD CONSTRAINT cmd_domain_event_event_type_check CHECK (
    event_type IN (
        'personal_attack_hit', 'personal_attack_missed',
        'personal_damage_applied', 'encounter_created',
        'encounter_mode_transitioned', 'encounter_participant_added',
        'encounter_attitude_set', 'encounter_attitude_changed',
        'encounter_attitude_unchanged', 'animal_reaction_context_set',
        'animal_reaction_resolved'
    )
);

CREATE TABLE cmd_animal_context_receipt (
    command_id          bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    encounter_id        bigint NOT NULL REFERENCES enc_encounter(encounter_id),
    animal_actor_id     bigint NOT NULL REFERENCES actor_animal_profile(actor_id),
    context_version     integer NOT NULL CHECK (context_version > 0)
);

CREATE TABLE enc_animal_reaction_result (
    animal_reaction_result_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    command_id          bigint NOT NULL UNIQUE REFERENCES cmd_command(command_id),
    encounter_id        bigint NOT NULL REFERENCES enc_encounter(encounter_id),
    animal_actor_id     bigint NOT NULL REFERENCES actor_animal_profile(actor_id),
    provocation_number  integer NOT NULL CHECK (provocation_number > 0),
    context_version     integer NOT NULL CHECK (context_version > 0),
    roll_total          smallint NOT NULL,
    attack_condition_met boolean NOT NULL,
    flee_condition_met boolean NOT NULL,
    reaction_outcome    text NOT NULL CHECK (
                            reaction_outcome IN (
                                'attack', 'flee', 'stand', 'requires_referee'
                            )
                        ),
    UNIQUE (encounter_id, animal_actor_id, provocation_number)
);

COMMENT ON COLUMN enc_animal_reaction_result.reaction_outcome IS
    'Both attack and flee produces requires_referee; source priority is unstated.';
