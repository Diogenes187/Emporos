CREATE TABLE rule_time_frame (
    rule_id             bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    dice_count          smallint NOT NULL CHECK (dice_count > 0),
    die_sides           smallint NOT NULL CHECK (die_sides > 1),
    increment_unit      text NOT NULL CHECK (
                            increment_unit IN (
                                'second', 'round', 'minute', 'kilosecond',
                                'hour', 'day', 'week', 'month', 'quarter'
                            )
                        ),
    exact_increment_seconds bigint CHECK (exact_increment_seconds > 0),
    source_description  text NOT NULL CHECK (btrim(source_description) <> ''),
    display_order       smallint NOT NULL UNIQUE CHECK (display_order > 0)
);

CREATE TABLE rule_task_adjustment (
    rule_id             bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    adjustment_kind     text NOT NULL UNIQUE CHECK (
                            adjustment_kind IN (
                                'faster', 'slower', 'extra_action',
                                'helpful_circumstance',
                                'hampering_circumstance'
                            )
                        ),
    modifier_per_step   integer NOT NULL,
    maximum_steps       smallint CHECK (maximum_steps > 0),
    applies_to_all_checks boolean NOT NULL DEFAULT false
);

CREATE TABLE rule_law_level_difficulty (
    law_level_difficulty_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    minimum_law_level   integer NOT NULL CHECK (minimum_law_level >= 0),
    maximum_law_level   integer CHECK (maximum_law_level >= minimum_law_level),
    difficulty_rule_id  bigint NOT NULL REFERENCES rule_difficulty(rule_id),
    display_order       smallint NOT NULL UNIQUE CHECK (display_order > 0),
    law_level_range     int4range GENERATED ALWAYS AS (
                            int4range(
                                minimum_law_level,
                                CASE WHEN maximum_law_level IS NULL THEN NULL
                                     ELSE maximum_law_level + 1 END,
                                '[)'
                            )
                        ) STORED,
    EXCLUDE USING gist (law_level_range WITH &&)
);

COMMENT ON TABLE rule_time_frame IS
    'Source-defined 1D6 task time frames without invented unit precision.';
COMMENT ON TABLE rule_task_adjustment IS
    'Typed task DMs for pace, simultaneous actions, and circumstances.';
COMMENT ON TABLE rule_law_level_difficulty IS
    'Non-overlapping Law Level ranges mapped to canonical Difficulty rules.';
