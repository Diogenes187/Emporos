CREATE TABLE rule_trade_work_policy (
 rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
 dedicated_work_seconds integer NOT NULL CHECK(dedicated_work_seconds=604800),
 published_technician_monthly_credits integer NOT NULL CHECK(published_technician_monthly_credits=1000),
 adjudicated_weekly_credits integer NOT NULL CHECK(adjudicated_weekly_credits=250),
 weekly_amount_is_campaign_adjudication boolean NOT NULL CHECK(weekly_amount_is_campaign_adjudication)
);
CREATE TABLE rule_trade_work_skill (
 skill_rule_id bigint PRIMARY KEY REFERENCES rule_skill(rule_id),
 rule_id bigint NOT NULL REFERENCES rule_trade_work_policy(rule_id),
 source_order smallint NOT NULL UNIQUE CHECK(source_order BETWEEN 1 AND 4)
);
COMMENT ON TABLE rule_trade_work_policy IS 'CE-SKILL-009 paired-source dedicated trade work; Cr250/week is Raymond-approved from published Cr1000/month technician pay.';
