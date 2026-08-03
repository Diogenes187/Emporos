CREATE TABLE rule_personal_combat_procedure (
    rule_id             bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    round_seconds       smallint NOT NULL CHECK (round_seconds > 0),
    initiative_dice_count smallint NOT NULL CHECK (initiative_dice_count > 0),
    initiative_die_sides smallint NOT NULL CHECK (initiative_die_sides > 1),
    aware_unopposed_base smallint NOT NULL,
    initiative_descending boolean NOT NULL,
    tie_break_characteristic_rule_id bigint NOT NULL
                        REFERENCES rule_characteristic(rule_id),
    exact_tie_simultaneous boolean NOT NULL,
    initiative_rerolled_each_round boolean NOT NULL
);

CREATE TABLE rule_personal_action_economy (
    rule_id             bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    significant_actions smallint NOT NULL CHECK (significant_actions >= 0),
    minor_actions_with_significant smallint NOT NULL CHECK (
                            minor_actions_with_significant >= 0
                        ),
    minor_actions_without_significant smallint NOT NULL CHECK (
                            minor_actions_without_significant >= 0
                        ),
    minor_actions_from_significant smallint NOT NULL CHECK (
                            minor_actions_from_significant >= 0
                        ),
    free_actions_unbounded_by_default boolean NOT NULL,
    reactions_unbounded_by_default boolean NOT NULL
);

CREATE TABLE rule_personal_reaction_system (
    rule_id             bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    initiative_cost_per_reaction integer NOT NULL,
    check_modifier_per_reaction integer NOT NULL,
    cumulative          boolean NOT NULL,
    maximum_per_round   smallint,
    maximum_per_attack  smallint NOT NULL CHECK (maximum_per_attack > 0),
    requires_awareness  boolean NOT NULL,
    dodge_attack_modifier integer NOT NULL,
    dodge_with_cover_attack_modifier integer NOT NULL,
    parry_uses_negative_melee_skill boolean NOT NULL
);
