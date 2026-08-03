CREATE TABLE src_law_level_difficulty_provenance (
    law_level_difficulty_id bigint NOT NULL
        REFERENCES rule_law_level_difficulty(law_level_difficulty_id),
    source_locator_id   bigint NOT NULL REFERENCES src_locator(source_locator_id),
    import_candidate_id bigint REFERENCES src_import_candidate(import_candidate_id),
    source_review_id    bigint REFERENCES src_review(source_review_id),
    provenance_class   text NOT NULL CHECK (
                            provenance_class IN (
                                'direct', 'corroborating', 'fills_source_gap',
                                'interpretation', 'agreed_addition'
                            )
                        ),
    is_primary_citation boolean NOT NULL DEFAULT false,
    recorded_at         timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (
        law_level_difficulty_id, source_locator_id, provenance_class
    ),
    FOREIGN KEY (import_candidate_id, source_locator_id)
        REFERENCES src_import_candidate(import_candidate_id, source_locator_id)
);
