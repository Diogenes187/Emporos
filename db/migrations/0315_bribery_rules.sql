CREATE TABLE rule_bribery_offense (
 rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
 offense_code text NOT NULL UNIQUE CHECK(offense_code IN ('petty','minor','serious','capital')),
 check_modifier smallint NOT NULL CHECK(check_modifier IN (2,0,-2,-4)),
 minimum_bribe_dice smallint NOT NULL CHECK(minimum_bribe_dice=1),
 minimum_bribe_die_sides smallint NOT NULL CHECK(minimum_bribe_die_sides=6),
 credits_per_die smallint NOT NULL CHECK(credits_per_die IN (10,50,100,500)),
 display_order smallint NOT NULL UNIQUE CHECK(display_order BETWEEN 1 AND 4)
);
COMMENT ON TABLE rule_bribery_offense IS 'CE-SKILL-002 paired-source Bribery Checks By Offense table.';
