CREATE TABLE rule_personal_free_action (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    performed_during_actor_turn boolean NOT NULL CHECK (
        performed_during_actor_turn),
    below_minor_action_threshold boolean NOT NULL CHECK (
        below_minor_action_threshold),
    unbounded_by_default boolean NOT NULL CHECK (unbounded_by_default),
    multiple_may_require_referee_escalation boolean NOT NULL CHECK (
        multiple_may_require_referee_escalation),
    escalation_may_cost_minor_action boolean NOT NULL CHECK (
        escalation_may_cost_minor_action),
    escalation_may_cost_significant_action boolean NOT NULL CHECK (
        escalation_may_cost_significant_action)
);

CREATE TABLE rule_personal_free_action_example (
    free_action_rule_id bigint NOT NULL REFERENCES
        rule_personal_free_action(rule_id),
    example_code text NOT NULL,
    example_order smallint NOT NULL CHECK (example_order>0),
    PRIMARY KEY (free_action_rule_id,example_code),
    UNIQUE (free_action_rule_id,example_order),
    CHECK (example_code IN (
        'shout_warning','push_button','check_watch'))
);

COMMENT ON TABLE rule_personal_free_action IS
    'CE-COMBAT-019 paired-source turn scope, default freedom, and referee escalation.';
COMMENT ON TABLE rule_personal_free_action_example IS
    'Normalized examples explicitly named by both governing sources.';
