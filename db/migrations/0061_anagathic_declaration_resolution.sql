ALTER TABLE actor_career_anagathic_term
    DROP CONSTRAINT actor_career_anagathic_term_check,
    ADD CONSTRAINT actor_career_anagathic_term_values_check CHECK (
        (
            uses_anagathics
            AND continuous_course_terms > 0
            AND cost_die BETWEEN 1 AND 6
            AND cost_credits=cost_die*2500
            AND declaration_status IN ('ready','resolved')
        )
        OR
        (
            NOT uses_anagathics
            AND continuous_course_terms=0
            AND cost_die IS NULL
            AND cost_credits=0
        )
    );
