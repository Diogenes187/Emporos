CREATE TABLE rule_rule (
    rule_id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id           uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    content_package_id  bigint NOT NULL
                        REFERENCES sys_content_package(content_package_id),
    rule_code           text NOT NULL CHECK (
                            rule_code ~ '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
                        ),
    name                text NOT NULL CHECK (btrim(name) <> ''),
    rule_category       text NOT NULL CHECK (
                            rule_category IN (
                                'characteristic', 'skill', 'skill_specialty',
                                'task', 'difficulty', 'random_table',
                                'career', 'equipment', 'combat',
                                'travel', 'trade', 'ship', 'vehicle',
                                'world', 'encounter', 'psionics', 'other'
                            )
                        ),
    rule_status         text NOT NULL DEFAULT 'draft' CHECK (
                            rule_status IN (
                                'draft', 'review', 'approved',
                                'released', 'superseded', 'withdrawn'
                            )
                        ),
    description         text,
    created_at          timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (content_package_id, rule_code),
    UNIQUE (rule_id, content_package_id)
);

CREATE TABLE rule_interpretation (
    rule_interpretation_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    rule_id             bigint NOT NULL,
    interpretation_type text NOT NULL CHECK (
                            interpretation_type IN (
                                'explicit_source', 'source_option',
                                'agreed_interpretation', 'agreed_addition'
                            )
                        ),
    decision_register_entry text,
    rationale           text,
    UNIQUE (rule_id, interpretation_type, decision_register_entry),
    CHECK (
        interpretation_type IN ('explicit_source', 'source_option')
        OR btrim(COALESCE(decision_register_entry, '')) <> ''
    )
);

CREATE TABLE src_record_provenance (
    record_provenance_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    rule_id             bigint NOT NULL REFERENCES rule_rule(rule_id),
    content_package_id  bigint NOT NULL
                        REFERENCES sys_content_package(content_package_id),
    source_locator_id   bigint NOT NULL
                        REFERENCES src_locator(source_locator_id),
    import_candidate_id bigint
                        REFERENCES src_import_candidate(import_candidate_id),
    source_review_id    bigint REFERENCES src_review(source_review_id),
    provenance_class   text NOT NULL CHECK (
                            provenance_class IN (
                                'direct', 'corroborating', 'fills_source_gap',
                                'interpretation', 'agreed_addition'
                            )
                        ),
    is_primary_citation boolean NOT NULL DEFAULT false,
    recorded_at         timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE NULLS NOT DISTINCT (
        rule_id, source_locator_id, import_candidate_id, provenance_class
    ),
    FOREIGN KEY (rule_id, content_package_id)
        REFERENCES rule_rule(rule_id, content_package_id),
    FOREIGN KEY (import_candidate_id, source_locator_id)
        REFERENCES src_import_candidate(import_candidate_id, source_locator_id)
);

CREATE INDEX src_record_provenance_rule_idx
    ON src_record_provenance(rule_id);
CREATE INDEX src_record_provenance_locator_idx
    ON src_record_provenance(source_locator_id);

CREATE TABLE rule_characteristic (
    rule_id             bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    abbreviation        text NOT NULL CHECK (
                            abbreviation ~ '^[A-Za-z][A-Za-z0-9]{1,7}$'
                        ),
    display_order       smallint NOT NULL CHECK (display_order > 0),
    normal_dice_count   smallint CHECK (
                            normal_dice_count IS NULL OR normal_dice_count > 0
                        ),
    normal_die_sides    smallint CHECK (
                            normal_die_sides IS NULL OR normal_die_sides > 1
                        ),
    minimum_score       smallint,
    maximum_score       smallint,
    CHECK (
        minimum_score IS NULL OR maximum_score IS NULL
        OR minimum_score <= maximum_score
    )
);

CREATE TABLE rule_characteristic_modifier_band (
    characteristic_modifier_band_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    content_package_id  bigint NOT NULL
                        REFERENCES sys_content_package(content_package_id),
    characteristic_rule_id bigint REFERENCES rule_characteristic(rule_id),
    minimum_score       integer NOT NULL,
    maximum_score       integer,
    modifier            integer NOT NULL,
    source_order        integer NOT NULL CHECK (source_order >= 0),
    scope_characteristic_id bigint GENERATED ALWAYS AS (
                            COALESCE(characteristic_rule_id, 0)
                        ) STORED,
    score_range         int4range GENERATED ALWAYS AS (
                            int4range(
                                minimum_score,
                                CASE
                                    WHEN maximum_score IS NULL THEN NULL
                                    ELSE maximum_score + 1
                                END,
                                '[)'
                            )
                        ) STORED,
    CHECK (maximum_score IS NULL OR minimum_score <= maximum_score),
    UNIQUE NULLS NOT DISTINCT (
        content_package_id, characteristic_rule_id, source_order
    ),
    EXCLUDE USING gist (
        content_package_id WITH =,
        scope_characteristic_id WITH =,
        score_range WITH &&
    )
);

CREATE TABLE rule_skill (
    rule_id             bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    cascade_skill       boolean NOT NULL DEFAULT false,
    permits_untrained   boolean NOT NULL DEFAULT true,
    untrained_modifier  integer,
    CHECK (permits_untrained OR untrained_modifier IS NULL)
);

CREATE TABLE rule_skill_specialty (
    specialty_rule_id   bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    parent_skill_rule_id bigint NOT NULL REFERENCES rule_skill(rule_id),
    display_order       integer NOT NULL CHECK (display_order >= 0),
    UNIQUE (parent_skill_rule_id, specialty_rule_id)
);

CREATE TABLE rule_skill_prerequisite (
    skill_prerequisite_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    skill_rule_id       bigint NOT NULL REFERENCES rule_skill(rule_id),
    prerequisite_skill_rule_id bigint REFERENCES rule_skill(rule_id),
    prerequisite_characteristic_rule_id bigint
                        REFERENCES rule_characteristic(rule_id),
    minimum_level       integer,
    rationale           text,
    CHECK (
        (prerequisite_skill_rule_id IS NOT NULL)::integer
        + (prerequisite_characteristic_rule_id IS NOT NULL)::integer = 1
    ),
    CHECK (minimum_level IS NULL OR minimum_level >= 0),
    CHECK (
        prerequisite_skill_rule_id IS NULL
        OR prerequisite_skill_rule_id <> skill_rule_id
    )
);
