CREATE TABLE rule_animal_encounter_system (
    rule_id             bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    occurrence_dice_count smallint NOT NULL CHECK (occurrence_dice_count > 0),
    occurrence_die_sides smallint NOT NULL CHECK (occurrence_die_sides > 1),
    occurrence_target   smallint NOT NULL,
    checks_while_travelling smallint NOT NULL CHECK (checks_while_travelling > 0),
    checks_while_halted smallint NOT NULL CHECK (checks_while_halted > 0),
    reaction_dice_count smallint NOT NULL CHECK (reaction_dice_count > 0),
    reaction_die_sides  smallint NOT NULL CHECK (reaction_die_sides > 1),
    stand_when_no_outcome boolean NOT NULL,
    reroll_when_provoked_again boolean NOT NULL
);

CREATE TABLE rule_animal_subtype (
    rule_id             bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    subtype_code        text NOT NULL UNIQUE,
    animal_type         text NOT NULL CHECK (
                            animal_type IN (
                                'carnivore', 'herbivore',
                                'omnivore', 'scavenger'
                            )
                        ),
    display_order       smallint NOT NULL UNIQUE CHECK (display_order > 0)
);

CREATE TABLE rule_animal_reaction_condition (
    animal_reaction_condition_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    subtype_rule_id     bigint NOT NULL REFERENCES rule_animal_subtype(rule_id),
    outcome             text NOT NULL CHECK (outcome IN ('attack', 'flee')),
    condition_kind      text NOT NULL CHECK (
                            condition_kind IN (
                                'roll_at_least', 'roll_at_most',
                                'outnumbers_characters', 'has_surprise',
                                'is_surprised', 'size_dependent_roll'
                            )
                        ),
    threshold           smallint,
    alternate_threshold smallint,
    requires_outnumbers boolean NOT NULL DEFAULT false,
    requires_has_surprise boolean NOT NULL DEFAULT false,
    requires_is_surprised boolean NOT NULL DEFAULT false,
    requires_bigger_than_character boolean,
    requires_outcome_possible boolean NOT NULL DEFAULT false,
    source_order        smallint NOT NULL CHECK (source_order > 0),
    UNIQUE (subtype_rule_id, outcome),
    CHECK (
        (condition_kind IN ('roll_at_least', 'roll_at_most')
         AND threshold IS NOT NULL AND alternate_threshold IS NULL)
        OR (condition_kind = 'size_dependent_roll'
            AND threshold IS NOT NULL AND alternate_threshold IS NOT NULL)
        OR (condition_kind NOT IN (
                'roll_at_least', 'roll_at_most', 'size_dependent_roll')
            AND threshold IS NULL AND alternate_threshold IS NULL)
    )
);

CREATE TABLE src_animal_reaction_condition_provenance (
    animal_reaction_condition_id bigint NOT NULL
        REFERENCES rule_animal_reaction_condition(animal_reaction_condition_id),
    source_locator_id   bigint NOT NULL REFERENCES src_locator(source_locator_id),
    import_candidate_id bigint REFERENCES src_import_candidate(import_candidate_id),
    source_review_id    bigint REFERENCES src_review(source_review_id),
    provenance_class   text NOT NULL CHECK (
                            provenance_class IN ('direct','corroborating')
                        ),
    is_primary_citation boolean NOT NULL DEFAULT false,
    PRIMARY KEY (
        animal_reaction_condition_id, source_locator_id, provenance_class
    ),
    FOREIGN KEY (import_candidate_id, source_locator_id)
        REFERENCES src_import_candidate(import_candidate_id, source_locator_id)
);

COMMENT ON TABLE rule_animal_reaction_condition IS
    'Typed attack/flee conditions; absent outcomes mean stand until provoked.';
