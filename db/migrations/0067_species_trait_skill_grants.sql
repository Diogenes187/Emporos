CREATE TABLE rule_species_trait_skill_grant (
    species_trait_rule_id bigint NOT NULL REFERENCES
        rule_species_trait(species_trait_rule_id),
    skill_rule_id bigint NOT NULL REFERENCES rule_skill(rule_id),
    granted_level smallint NOT NULL CHECK (granted_level >= 0),
    PRIMARY KEY (species_trait_rule_id,skill_rule_id)
);

INSERT INTO rule_species_trait_skill_grant
    (species_trait_rule_id,skill_rule_id,granted_level)
SELECT trait.species_trait_rule_id,skill.rule_id,0
FROM (VALUES
    ('flyer','skill.athletics'),
    ('great-leaper','skill.athletics'),
    ('natural-weapon','skill.natural-weapons')
) value(trait_code,skill_code)
JOIN rule_species_trait trait ON trait.trait_code=value.trait_code
JOIN rule_rule skill ON skill.rule_code=value.skill_code;

CREATE TABLE actor_species_skill_grant (
    actor_species_assignment_id bigint NOT NULL REFERENCES
        actor_species_assignment(actor_species_assignment_id),
    skill_rule_id bigint NOT NULL REFERENCES rule_skill(rule_id),
    granted_level smallint NOT NULL CHECK (granted_level >= 0),
    prior_skill_level smallint CHECK (prior_skill_level >= 0),
    resulting_skill_level smallint NOT NULL CHECK (resulting_skill_level >= 0),
    PRIMARY KEY (actor_species_assignment_id,skill_rule_id),
    CHECK (
        resulting_skill_level >= granted_level
        AND (
            prior_skill_level IS NULL
            OR resulting_skill_level >= prior_skill_level
        )
    )
);
