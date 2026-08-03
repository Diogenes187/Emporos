ALTER TABLE cmd_species_hive_mentality_receipt
    ADD CONSTRAINT cmd_hive_mentality_difficulty_range_check CHECK (
        difficulty_modifier BETWEEN -2 AND 2
    );
