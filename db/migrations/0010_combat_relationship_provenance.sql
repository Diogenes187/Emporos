ALTER TABLE combat_attack_profile
    ADD COLUMN rule_id bigint UNIQUE REFERENCES rule_rule(rule_id);

CREATE TABLE src_attack_profile_difficulty_provenance (
    attack_profile_code text NOT NULL,
    range_band_rule_id bigint NOT NULL,
    source_locator_id bigint NOT NULL REFERENCES src_locator(source_locator_id),
    import_candidate_id bigint REFERENCES src_import_candidate(import_candidate_id),
    source_review_id bigint REFERENCES src_review(source_review_id),
    provenance_class text NOT NULL CHECK (
        provenance_class IN ('direct','corroborating','fills_source_gap',
                             'interpretation','agreed_addition')),
    is_primary_citation boolean NOT NULL DEFAULT false,
    PRIMARY KEY (attack_profile_code, range_band_rule_id,
                 source_locator_id, provenance_class),
    FOREIGN KEY (attack_profile_code, range_band_rule_id)
        REFERENCES combat_attack_profile_difficulty,
    FOREIGN KEY (import_candidate_id, source_locator_id)
        REFERENCES src_import_candidate(import_candidate_id, source_locator_id)
);

CREATE TABLE src_weapon_attack_mode_provenance (
    item_rule_id bigint NOT NULL,
    attack_profile_code text NOT NULL,
    source_locator_id bigint NOT NULL REFERENCES src_locator(source_locator_id),
    import_candidate_id bigint REFERENCES src_import_candidate(import_candidate_id),
    source_review_id bigint REFERENCES src_review(source_review_id),
    provenance_class text NOT NULL CHECK (
        provenance_class IN ('direct','corroborating','fills_source_gap',
                             'interpretation','agreed_addition')),
    is_primary_citation boolean NOT NULL DEFAULT false,
    PRIMARY KEY (item_rule_id, attack_profile_code,
                 source_locator_id, provenance_class),
    FOREIGN KEY (item_rule_id, attack_profile_code)
        REFERENCES inv_weapon_attack_mode,
    FOREIGN KEY (import_candidate_id, source_locator_id)
        REFERENCES src_import_candidate(import_candidate_id, source_locator_id)
);
