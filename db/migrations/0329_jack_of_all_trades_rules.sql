CREATE TABLE rule_jack_of_all_trades (
 rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
 skill_rule_id bigint NOT NULL UNIQUE REFERENCES rule_skill(rule_id),
 untrained_penalty_reduction_per_level smallint NOT NULL CHECK(untrained_penalty_reduction_per_level=1),
 maximum_resulting_skill_modifier smallint NOT NULL CHECK(maximum_resulting_skill_modifier=0),
 learnable_during_gameplay boolean NOT NULL CHECK(NOT learnable_during_gameplay)
);
COMMENT ON TABLE rule_jack_of_all_trades IS 'CE-SKILL-006 paired-source Jack of All Trades untrained-penalty reduction capped at Skill DM 0.';
