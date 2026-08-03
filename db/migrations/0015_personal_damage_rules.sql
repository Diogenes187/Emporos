CREATE TABLE rule_personal_damage_system (
    rule_id             bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    add_attack_effect   boolean NOT NULL,
    armor_reduces_damage boolean NOT NULL,
    exceptional_effect_threshold integer NOT NULL,
    exceptional_minimum_damage integer NOT NULL CHECK (
                            exceptional_minimum_damage > 0
                        ),
    first_characteristic_rule_id bigint NOT NULL
                        REFERENCES rule_characteristic(rule_id),
    overflow_player_choice boolean NOT NULL,
    subsequent_player_choice boolean NOT NULL
);

CREATE TABLE rule_health_outcome (
    rule_id             bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    outcome_code        text NOT NULL UNIQUE CHECK (
                            outcome_code IN (
                                'wounded', 'seriously_wounded',
                                'unconscious', 'dead'
                            )
                        ),
    trigger_metric      text NOT NULL CHECK (
                            trigger_metric IN (
                                'physical_characteristics_damaged',
                                'physical_characteristics_at_zero'
                            )
                        ),
    threshold_count     smallint NOT NULL CHECK (
                            threshold_count BETWEEN 1 AND 3
                        ),
    comparison          text NOT NULL CHECK (
                            comparison IN ('at_least', 'exactly_all')
                        )
);

COMMENT ON TABLE rule_health_outcome IS
    'Source-defined health classifications; damaged and zero counts differ.';
