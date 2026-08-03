ALTER TABLE cmd_command DROP CONSTRAINT cmd_command_command_type_check;
ALTER TABLE cmd_command ADD CONSTRAINT cmd_command_command_type_check CHECK (
    command_type IN (
        'resolve_personal_attack', 'apply_personal_damage',
        'create_encounter', 'transition_encounter_mode',
        'add_encounter_participant', 'set_encounter_attitude',
        'attempt_attitude_influence', 'set_animal_reaction_context',
        'resolve_animal_reaction', 'check_starship_encounter'
    )
);

ALTER TABLE cmd_random_draw DROP CONSTRAINT cmd_random_draw_draw_group_check;
ALTER TABLE cmd_random_draw ADD CONSTRAINT cmd_random_draw_draw_group_check CHECK (
    draw_group IN ('attack', 'damage', 'task', 'occurrence', 'encounter_type')
);

ALTER TABLE cmd_domain_event DROP CONSTRAINT cmd_domain_event_event_type_check;
ALTER TABLE cmd_domain_event ADD CONSTRAINT cmd_domain_event_event_type_check CHECK (
    event_type IN (
        'personal_attack_hit', 'personal_attack_missed',
        'personal_damage_applied', 'encounter_created',
        'encounter_mode_transitioned', 'encounter_participant_added',
        'encounter_attitude_set', 'encounter_attitude_changed',
        'encounter_attitude_unchanged', 'animal_reaction_context_set',
        'animal_reaction_resolved', 'starship_encounter_checked',
        'starship_contact_created'
    )
);

CREATE TABLE enc_starship_contact (
    encounter_id        bigint PRIMARY KEY REFERENCES enc_encounter(encounter_id),
    category_rule_id    bigint REFERENCES rule_starship_encounter_category(rule_id),
    region_context      text NOT NULL CHECK (
                            region_context IN ('deep_space', 'near_planet')
                        ),
    base_range          text NOT NULL CHECK (
                            base_range IN ('very_long', 'medium')
                        ),
    comms_check_total   integer,
    comms_target_number integer,
    comms_succeeded     boolean,
    final_range         text CHECK (
                            final_range IN ('very_long', 'long', 'medium', 'short')
                        ),
    contact_status      text NOT NULL CHECK (
                            contact_status IN (
                                'established', 'requires_referee_category'
                            )
                        ),
    CHECK (
        (comms_check_total IS NULL AND comms_target_number IS NULL
         AND comms_succeeded IS NULL AND final_range IS NULL)
        OR (comms_check_total IS NOT NULL AND comms_target_number IS NOT NULL
            AND comms_succeeded IS NOT NULL AND final_range IS NOT NULL)
    )
);

CREATE TABLE cmd_starship_encounter_receipt (
    command_id          bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    campaign_id         bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    encounter_id        bigint UNIQUE REFERENCES enc_encounter(encounter_id),
    encounter_occurred  boolean NOT NULL,
    occurrence_total    smallint NOT NULL,
    category_roll_total smallint,
    category_rule_id    bigint REFERENCES rule_starship_encounter_category(rule_id),
    type_was_chosen     boolean NOT NULL DEFAULT false,
    referee_choice      boolean NOT NULL DEFAULT false,
    region_context      text NOT NULL,
    comms_skill_modifier integer,
    comms_characteristic_modifier integer,
    comms_circumstance_total integer,
    transponder_modifier integer,
    stealth_modifier    integer,
    CHECK (
        (encounter_occurred AND encounter_id IS NOT NULL AND (
            (type_was_chosen AND category_roll_total IS NULL
             AND category_rule_id IS NOT NULL)
            OR (NOT type_was_chosen AND category_roll_total IS NOT NULL)
        ))
        OR (NOT encounter_occurred AND encounter_id IS NULL
            AND category_roll_total IS NULL AND category_rule_id IS NULL
            AND NOT type_was_chosen AND NOT referee_choice)
    )
);

CREATE TABLE cmd_starship_comms_modifier (
    command_id          bigint NOT NULL
                        REFERENCES cmd_starship_encounter_receipt(command_id),
    modifier_order      smallint NOT NULL CHECK (modifier_order > 0),
    modifier_value      integer NOT NULL,
    PRIMARY KEY (command_id, modifier_order)
);
