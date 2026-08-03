ALTER TABLE actor_career_aging
    ALTER COLUMN career_term_id DROP NOT NULL,
    ADD COLUMN career_anagathic_term_id bigint UNIQUE REFERENCES
        actor_career_anagathic_term(career_anagathic_term_id),
    ADD CONSTRAINT actor_career_aging_origin_check CHECK (
        (career_term_id IS NOT NULL)::integer
        + (career_anagathic_term_id IS NOT NULL)::integer = 1
    );
