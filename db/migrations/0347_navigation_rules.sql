CREATE TABLE rule_navigation_mechanic (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    skill_rule_id bigint NOT NULL UNIQUE REFERENCES rule_skill(rule_id),
    determines_post_jump_location boolean NOT NULL CHECK (determines_post_jump_location),
    plots_normal_space_course boolean NOT NULL CHECK (plots_normal_space_course),
    plots_jump_route boolean NOT NULL CHECK (plots_jump_route),
    safe_jump_requires_route boolean NOT NULL CHECK (safe_jump_requires_route)
);
COMMENT ON TABLE rule_navigation_mechanic IS 'CE-SKILL-011 paired-source Navigation capabilities and safe-Jump route requirement.';
