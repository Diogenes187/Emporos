CREATE TABLE rule_liaison_negotiation (
 rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
 skill_rule_id bigint NOT NULL UNIQUE REFERENCES rule_skill(rule_id),
 minimum_participants smallint NOT NULL CHECK(minimum_participants=2),
 opposed_checks_required boolean NOT NULL CHECK(opposed_checks_required),
 highest_total_gains_advantage boolean NOT NULL CHECK(highest_total_gains_advantage),
 ties_require_referee_resolution boolean NOT NULL CHECK(ties_require_referee_resolution)
);
COMMENT ON TABLE rule_liaison_negotiation IS 'CE-SKILL-007 paired-source opposed Liaison negotiation with explicit unresolved ties.';
