CREATE TABLE rule_leadership_coordination (
 rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
 skill_rule_id bigint NOT NULL REFERENCES rule_skill(rule_id),
 pool_uses_effect boolean NOT NULL CHECK(pool_uses_effect),
 minimum_pool_points smallint NOT NULL CHECK(minimum_pool_points=1),
 modifier_per_point smallint NOT NULL CHECK(modifier_per_point=1),
 requires_common_goal boolean NOT NULL CHECK(requires_common_goal)
);
COMMENT ON TABLE rule_leadership_coordination IS 'CE-SKILL-005 paired-source Leadership Coordinating Effort pool.';
