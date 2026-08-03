CREATE TABLE rule_computer_basic_use (
 rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
 skill_rule_id bigint NOT NULL UNIQUE REFERENCES rule_skill(rule_id),
 minimum_skill_level smallint NOT NULL CHECK(minimum_skill_level=0),
 requires_skill_check boolean NOT NULL CHECK(NOT requires_skill_check)
);
CREATE TABLE rule_computer_basic_operation (
 operation_code text PRIMARY KEY CHECK(operation_code ~ '^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$'),
 display_name text NOT NULL UNIQUE CHECK(btrim(display_name)<>''),
 source_order smallint NOT NULL UNIQUE CHECK(source_order BETWEEN 1 AND 4)
);
COMMENT ON TABLE rule_computer_basic_use IS 'CE-SKILL-008 paired-source Computer-0 automatic basic operations.';
