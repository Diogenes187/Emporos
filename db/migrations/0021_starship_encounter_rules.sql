CREATE TABLE rule_starship_encounter_system (
    rule_id             bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    occurrence_dice_count smallint NOT NULL CHECK (occurrence_dice_count > 0),
    occurrence_die_sides smallint NOT NULL CHECK (occurrence_die_sides > 1),
    occurrence_target   smallint NOT NULL,
    check_on_region_entry boolean NOT NULL,
    check_on_region_exit boolean NOT NULL,
    type_dice_count     smallint NOT NULL CHECK (type_dice_count > 0),
    type_die_sides      smallint NOT NULL CHECK (type_die_sides > 1),
    subtype_dice_count  smallint NOT NULL CHECK (subtype_dice_count > 0),
    subtype_die_sides   smallint NOT NULL CHECK (subtype_die_sides > 1),
    deep_space_initial_range text NOT NULL CHECK (
                            deep_space_initial_range = 'very_long'
                        ),
    near_planet_initial_range text NOT NULL CHECK (
                            near_planet_initial_range = 'medium'
                        ),
    failed_comms_moves_one_category_closer boolean NOT NULL,
    active_transponder_detection_modifier integer NOT NULL,
    referee_may_choose_type boolean NOT NULL,
    referee_may_override_nonsensical_result boolean NOT NULL,
    special_encounter_range_override boolean NOT NULL
);

CREATE TABLE rule_starship_encounter_category (
    rule_id             bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    category_code       text NOT NULL UNIQUE CHECK (
                            category_code IN (
                                'alien_vessel', 'derelict', 'space_habitat',
                                'astrogation', 'space_junk',
                                'merchant_vessel', 'personal_vessel',
                                'hostile_vessel', 'military_vessel',
                                'spacecraft'
                            )
                        )
);

CREATE TABLE rule_starship_encounter_roll (
    roll_total          smallint PRIMARY KEY CHECK (roll_total BETWEEN 2 AND 12),
    category_rule_id    bigint REFERENCES rule_starship_encounter_category(rule_id),
    referee_choice      boolean NOT NULL DEFAULT false,
    CHECK (
        (referee_choice AND category_rule_id IS NULL)
        OR (NOT referee_choice AND category_rule_id IS NOT NULL)
    )
);

CREATE TABLE src_starship_encounter_roll_provenance (
    roll_total          smallint NOT NULL
                        REFERENCES rule_starship_encounter_roll(roll_total),
    source_locator_id   bigint NOT NULL REFERENCES src_locator(source_locator_id),
    import_candidate_id bigint REFERENCES src_import_candidate(import_candidate_id),
    source_review_id    bigint REFERENCES src_review(source_review_id),
    provenance_class   text NOT NULL CHECK (
                            provenance_class IN ('direct','corroborating')
                        ),
    is_primary_citation boolean NOT NULL DEFAULT false,
    PRIMARY KEY (roll_total, source_locator_id, provenance_class),
    FOREIGN KEY (import_candidate_id, source_locator_id)
        REFERENCES src_import_candidate(import_candidate_id, source_locator_id)
);

COMMENT ON COLUMN rule_starship_encounter_system.near_planet_initial_range IS
    'Meeting default from Starship Encounters; not a space-combat range ruling.';
