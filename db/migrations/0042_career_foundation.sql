CREATE TABLE rule_career (
    career_rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    career_code text NOT NULL UNIQUE CHECK (btrim(career_code) <> ''),
    display_order smallint NOT NULL UNIQUE CHECK (display_order > 0)
);

CREATE TABLE rule_career_assignment (
    assignment_rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    career_rule_id bigint NOT NULL REFERENCES rule_career(career_rule_id),
    assignment_code text NOT NULL CHECK (btrim(assignment_code) <> ''),
    display_order smallint NOT NULL CHECK (display_order > 0),
    UNIQUE (career_rule_id, assignment_code),
    UNIQUE (career_rule_id, display_order)
);

CREATE TABLE rule_career_progression (
    career_progression_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    career_rule_id bigint NOT NULL REFERENCES rule_career(career_rule_id),
    assignment_rule_id bigint REFERENCES rule_career_assignment(
        assignment_rule_id
    ),
    qualification_characteristic_rule_id bigint
        REFERENCES rule_characteristic(rule_id),
    qualification_target smallint,
    survival_characteristic_rule_id bigint
        REFERENCES rule_characteristic(rule_id),
    survival_target smallint,
    commission_characteristic_rule_id bigint
        REFERENCES rule_characteristic(rule_id),
    commission_target smallint,
    advancement_characteristic_rule_id bigint
        REFERENCES rule_characteristic(rule_id),
    advancement_target smallint,
    reenlistment_target smallint NOT NULL CHECK (reenlistment_target > 0),
    UNIQUE NULLS NOT DISTINCT (career_rule_id, assignment_rule_id),
    CHECK (
        (qualification_characteristic_rule_id IS NULL)
        = (qualification_target IS NULL)
    ),
    CHECK (
        (survival_characteristic_rule_id IS NULL) = (survival_target IS NULL)
    ),
    CHECK (
        (commission_characteristic_rule_id IS NULL)
        = (commission_target IS NULL)
    ),
    CHECK (
        (advancement_characteristic_rule_id IS NULL)
        = (advancement_target IS NULL)
    )
);

CREATE TABLE rule_career_rank (
    career_rank_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    career_rule_id bigint NOT NULL REFERENCES rule_career(career_rule_id),
    assignment_rule_id bigint REFERENCES rule_career_assignment(
        assignment_rule_id
    ),
    rank_number smallint NOT NULL CHECK (rank_number BETWEEN 0 AND 6),
    title text,
    granted_skill_rule_id bigint REFERENCES rule_skill(rule_id),
    granted_skill_level smallint CHECK (granted_skill_level >= 0),
    source_grant_text text,
    UNIQUE NULLS NOT DISTINCT (
        career_rule_id, assignment_rule_id, rank_number
    ),
    CHECK (
        granted_skill_rule_id IS NOT NULL
        OR granted_skill_level IS NULL
    )
);

CREATE TABLE rule_career_training_entry (
    career_training_entry_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    career_rule_id bigint NOT NULL REFERENCES rule_career(career_rule_id),
    assignment_rule_id bigint REFERENCES rule_career_assignment(
        assignment_rule_id
    ),
    training_table_code text NOT NULL CHECK (
        training_table_code IN (
            'personal_development', 'service', 'specialist',
            'advanced_education'
        )
    ),
    roll_value smallint NOT NULL CHECK (roll_value BETWEEN 1 AND 6),
    outcome_kind text NOT NULL CHECK (
        outcome_kind IN ('skill', 'characteristic', 'text')
    ),
    skill_rule_id bigint REFERENCES rule_skill(rule_id),
    characteristic_rule_id bigint REFERENCES rule_characteristic(rule_id),
    characteristic_increase smallint CHECK (characteristic_increase > 0),
    fixed_skill_level smallint CHECK (fixed_skill_level >= 0),
    source_outcome_text text NOT NULL CHECK (btrim(source_outcome_text) <> ''),
    UNIQUE NULLS NOT DISTINCT (
        career_rule_id, assignment_rule_id, training_table_code, roll_value
    ),
    CHECK (
        (outcome_kind='skill' AND skill_rule_id IS NOT NULL
         AND characteristic_rule_id IS NULL
         AND characteristic_increase IS NULL)
        OR
        (outcome_kind='characteristic' AND skill_rule_id IS NULL
         AND characteristic_rule_id IS NOT NULL
         AND characteristic_increase IS NOT NULL
         AND fixed_skill_level IS NULL)
        OR
        (outcome_kind='text' AND skill_rule_id IS NULL
         AND characteristic_rule_id IS NULL
         AND characteristic_increase IS NULL
         AND fixed_skill_level IS NULL)
    )
);

CREATE TABLE rule_career_benefit (
    career_benefit_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    career_rule_id bigint NOT NULL REFERENCES rule_career(career_rule_id),
    benefit_table_code text NOT NULL CHECK (
        benefit_table_code IN ('cash', 'material')
    ),
    roll_value smallint NOT NULL CHECK (roll_value BETWEEN 1 AND 7),
    cash_credits integer CHECK (cash_credits >= 0),
    source_outcome_text text NOT NULL CHECK (btrim(source_outcome_text) <> ''),
    UNIQUE (career_rule_id, benefit_table_code, roll_value),
    CHECK (
        (benefit_table_code='cash' AND cash_credits IS NOT NULL)
        OR (benefit_table_code='material' AND cash_credits IS NULL)
    )
);

CREATE TABLE src_career_progression_provenance (
    career_progression_id bigint NOT NULL REFERENCES rule_career_progression(
        career_progression_id
    ),
    source_locator_id bigint NOT NULL REFERENCES src_locator(source_locator_id),
    import_candidate_id bigint REFERENCES src_import_candidate(import_candidate_id),
    source_review_id bigint REFERENCES src_review(source_review_id),
    provenance_class text NOT NULL CHECK (
        provenance_class IN ('direct','corroborating')
    ),
    is_primary_citation boolean NOT NULL DEFAULT false,
    PRIMARY KEY (
        career_progression_id, source_locator_id, provenance_class
    )
);

CREATE TABLE src_career_rank_provenance (
    career_rank_id bigint NOT NULL REFERENCES rule_career_rank(career_rank_id),
    source_locator_id bigint NOT NULL REFERENCES src_locator(source_locator_id),
    import_candidate_id bigint REFERENCES src_import_candidate(import_candidate_id),
    source_review_id bigint REFERENCES src_review(source_review_id),
    provenance_class text NOT NULL CHECK (
        provenance_class IN ('direct','corroborating')
    ),
    is_primary_citation boolean NOT NULL DEFAULT false,
    PRIMARY KEY (career_rank_id, source_locator_id, provenance_class)
);

CREATE TABLE src_career_training_entry_provenance (
    career_training_entry_id bigint NOT NULL
        REFERENCES rule_career_training_entry(career_training_entry_id),
    source_locator_id bigint NOT NULL REFERENCES src_locator(source_locator_id),
    import_candidate_id bigint REFERENCES src_import_candidate(import_candidate_id),
    source_review_id bigint REFERENCES src_review(source_review_id),
    provenance_class text NOT NULL CHECK (
        provenance_class IN ('direct','corroborating')
    ),
    is_primary_citation boolean NOT NULL DEFAULT false,
    PRIMARY KEY (
        career_training_entry_id, source_locator_id, provenance_class
    )
);

CREATE TABLE src_career_benefit_provenance (
    career_benefit_id bigint NOT NULL REFERENCES rule_career_benefit(
        career_benefit_id
    ),
    source_locator_id bigint NOT NULL REFERENCES src_locator(source_locator_id),
    import_candidate_id bigint REFERENCES src_import_candidate(import_candidate_id),
    source_review_id bigint REFERENCES src_review(source_review_id),
    provenance_class text NOT NULL CHECK (
        provenance_class IN ('direct','corroborating')
    ),
    is_primary_citation boolean NOT NULL DEFAULT false,
    PRIMARY KEY (career_benefit_id, source_locator_id, provenance_class)
);
