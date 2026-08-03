CREATE TABLE rule_check_system (
    rule_id                  bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    dice_count               smallint NOT NULL CHECK (dice_count > 0),
    die_sides                smallint NOT NULL CHECK (die_sides > 1),
    target_number            integer NOT NULL,
    success_on_or_above      boolean NOT NULL DEFAULT true,
    natural_min_auto_failure boolean NOT NULL DEFAULT false,
    natural_max_auto_success boolean NOT NULL DEFAULT false
);

CREATE TABLE rule_difficulty (
    rule_id             bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    modifier            integer NOT NULL,
    display_order       smallint NOT NULL CHECK (display_order > 0),
    is_default          boolean NOT NULL DEFAULT false
);

CREATE UNIQUE INDEX rule_difficulty_modifier_uq
    ON rule_difficulty (modifier);
CREATE UNIQUE INDEX rule_difficulty_display_order_uq
    ON rule_difficulty (display_order);
CREATE UNIQUE INDEX rule_difficulty_one_default_uq
    ON rule_difficulty (is_default) WHERE is_default;

CREATE TABLE rule_effect_band (
    rule_id             bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    minimum_effect      integer,
    maximum_effect      integer,
    outcome_code        text NOT NULL CHECK (
                            outcome_code IN (
                                'exceptional_failure', 'failure',
                                'success', 'exceptional_success'
                            )
                        ),
    successful          boolean NOT NULL,
    display_order       smallint NOT NULL CHECK (display_order > 0),
    effect_range        int4range GENERATED ALWAYS AS (
                            int4range(
                                minimum_effect,
                                CASE
                                    WHEN maximum_effect IS NULL THEN NULL
                                    ELSE maximum_effect + 1
                                END,
                                '[)'
                            )
                        ) STORED,
    CHECK (minimum_effect IS NOT NULL OR maximum_effect IS NOT NULL),
    CHECK (
        minimum_effect IS NULL OR maximum_effect IS NULL
        OR minimum_effect <= maximum_effect
    ),
    UNIQUE (outcome_code),
    UNIQUE (display_order),
    EXCLUDE USING gist (effect_range WITH &&)
);

COMMENT ON TABLE rule_check_system IS
    'Typed governing parameters for a package task/check resolution system.';
COMMENT ON TABLE rule_difficulty IS
    'Named Difficulty modifiers; exactly one imported row is marked default.';
COMMENT ON TABLE rule_effect_band IS
    'Non-overlapping Effect ranges and source-defined outcome classifications.';
