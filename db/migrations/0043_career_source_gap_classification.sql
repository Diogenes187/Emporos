ALTER TABLE src_career_progression_provenance
    DROP CONSTRAINT src_career_progression_provenance_provenance_class_check;
ALTER TABLE src_career_progression_provenance
    ADD CONSTRAINT src_career_progression_provenance_provenance_class_check
    CHECK (provenance_class IN ('direct','corroborating','fills_source_gap'));

ALTER TABLE src_career_rank_provenance
    DROP CONSTRAINT src_career_rank_provenance_provenance_class_check;
ALTER TABLE src_career_rank_provenance
    ADD CONSTRAINT src_career_rank_provenance_provenance_class_check
    CHECK (provenance_class IN ('direct','corroborating','fills_source_gap'));

ALTER TABLE src_career_training_entry_provenance
    DROP CONSTRAINT
        src_career_training_entry_provenance_provenance_class_check;
ALTER TABLE src_career_training_entry_provenance
    ADD CONSTRAINT
        src_career_training_entry_provenance_provenance_class_check
    CHECK (provenance_class IN ('direct','corroborating','fills_source_gap'));

ALTER TABLE src_career_benefit_provenance
    DROP CONSTRAINT src_career_benefit_provenance_provenance_class_check;
ALTER TABLE src_career_benefit_provenance
    ADD CONSTRAINT src_career_benefit_provenance_provenance_class_check
    CHECK (provenance_class IN ('direct','corroborating','fills_source_gap'));
