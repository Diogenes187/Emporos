ALTER TABLE rule_skill_specialty
    ADD CONSTRAINT rule_skill_specialty_parent_pair_unique
    UNIQUE (specialty_rule_id, parent_skill_rule_id);

CREATE TABLE src_characteristic_modifier_band_provenance (
    modifier_band_provenance_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    characteristic_modifier_band_id bigint NOT NULL
        REFERENCES rule_characteristic_modifier_band(
            characteristic_modifier_band_id
        ),
    source_locator_id   bigint NOT NULL
                        REFERENCES src_locator(source_locator_id),
    import_candidate_id bigint NOT NULL,
    source_review_id    bigint NOT NULL REFERENCES src_review(source_review_id),
    provenance_class    text NOT NULL CHECK (
                            provenance_class IN (
                                'direct', 'corroborating', 'fills_source_gap'
                            )
                        ),
    is_primary_citation boolean NOT NULL DEFAULT false,
    recorded_at         timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (
        characteristic_modifier_band_id, source_locator_id,
        import_candidate_id, provenance_class
    ),
    FOREIGN KEY (import_candidate_id, source_locator_id)
        REFERENCES src_import_candidate(
            import_candidate_id, source_locator_id
        )
);

CREATE TABLE src_skill_specialty_provenance (
    skill_specialty_provenance_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    specialty_rule_id   bigint NOT NULL,
    parent_skill_rule_id bigint NOT NULL,
    source_locator_id   bigint NOT NULL
                        REFERENCES src_locator(source_locator_id),
    import_candidate_id bigint NOT NULL,
    source_review_id    bigint NOT NULL REFERENCES src_review(source_review_id),
    provenance_class    text NOT NULL CHECK (
                            provenance_class IN (
                                'direct', 'corroborating', 'fills_source_gap'
                            )
                        ),
    is_primary_citation boolean NOT NULL DEFAULT false,
    recorded_at         timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (
        specialty_rule_id, parent_skill_rule_id, source_locator_id,
        import_candidate_id, provenance_class
    ),
    FOREIGN KEY (specialty_rule_id, parent_skill_rule_id)
        REFERENCES rule_skill_specialty(
            specialty_rule_id, parent_skill_rule_id
        ),
    FOREIGN KEY (import_candidate_id, source_locator_id)
        REFERENCES src_import_candidate(
            import_candidate_id, source_locator_id
        )
);

