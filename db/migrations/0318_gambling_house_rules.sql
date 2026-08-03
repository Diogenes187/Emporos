CREATE TABLE rule_gambling_house_odds (
 rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
 odds_code text NOT NULL UNIQUE CHECK(odds_code IN ('rigged','remote','small','low','average','high')),
 check_modifier smallint NOT NULL CHECK(check_modifier IN (-8,-6,-4,-2,0,2)),
 payoff_numerator smallint CHECK(payoff_numerator>0),
 payoff_denominator smallint CHECK(payoff_denominator>0),
 maximum_bet_credits bigint CHECK(maximum_bet_credits>0),
 display_order smallint NOT NULL UNIQUE CHECK(display_order BETWEEN 1 AND 6),
 CHECK((odds_code='rigged')=(payoff_numerator IS NULL AND payoff_denominator IS NULL AND maximum_bet_credits IS NULL))
);
COMMENT ON TABLE rule_gambling_house_odds IS 'CE-SKILL-003 paired-source Gambling by Odds of Winning table; payoff ratios remain exact source ratios.';
