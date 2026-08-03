CREATE TABLE rule_personal_extended_action (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    timing_roll_required boolean NOT NULL CHECK (timing_roll_required),
    timing_result_determines_required_rounds boolean NOT NULL CHECK (
        timing_result_determines_required_rounds
    ),
    combat_round_seconds smallint NOT NULL CHECK (combat_round_seconds=6),
    exclusive_activity boolean NOT NULL CHECK (exclusive_activity),
    may_abandon_any_time boolean NOT NULL CHECK (may_abandon_any_time),
    hit_requires_interruption_check boolean NOT NULL CHECK (
        hit_requires_interruption_check
    ),
    interruption_target_number smallint NOT NULL CHECK (
        interruption_target_number=8
    ),
    interruption_uses_task_skill boolean NOT NULL CHECK (
        interruption_uses_task_skill
    ),
    post_armor_damage_is_negative_dm boolean NOT NULL CHECK (
        post_armor_damage_is_negative_dm
    ),
    failed_check_loses_current_round boolean NOT NULL CHECK (
        failed_check_loses_current_round
    ),
    exceptional_failure_maximum_effect smallint NOT NULL CHECK (
        exceptional_failure_maximum_effect=-6
    ),
    exceptional_failure_ruins_task boolean NOT NULL CHECK (
        exceptional_failure_ruins_task
    ),
    ruined_task_restarts_from_beginning boolean NOT NULL CHECK (
        ruined_task_restarts_from_beginning
    )
);

COMMENT ON TABLE rule_personal_extended_action IS
    'CE-COMBAT-018 paired-source timing, exclusivity, interruption, and reset mechanics.';
