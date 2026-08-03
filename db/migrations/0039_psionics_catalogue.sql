CREATE TABLE psi_system (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    characteristic_rule_id bigint NOT NULL
        REFERENCES rule_characteristic(rule_id),
    failed_activation_cost smallint NOT NULL CHECK (failed_activation_cost >= 0),
    recovery_delay_hours smallint NOT NULL CHECK (recovery_delay_hours >= 0),
    recovery_points_per_hour smallint NOT NULL
        CHECK (recovery_points_per_hour > 0),
    combat_action_kind text NOT NULL CHECK (
        combat_action_kind IN ('significant', 'minor', 'free')
    ),
    permits_untrained boolean NOT NULL,
    overexertion_characteristic_rule_id bigint NOT NULL
        REFERENCES rule_characteristic(rule_id)
);

CREATE TABLE psi_talent (
    talent_rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    skill_rule_id bigint NOT NULL UNIQUE REFERENCES rule_skill(rule_id),
    learning_modifier smallint NOT NULL,
    display_order smallint NOT NULL UNIQUE CHECK (display_order > 0),
    self_only boolean NOT NULL DEFAULT false
);

CREATE TABLE psi_power (
    power_rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    talent_rule_id bigint NOT NULL REFERENCES psi_talent(talent_rule_id),
    power_code text NOT NULL CHECK (btrim(power_code) <> ''),
    difficulty_rule_id bigint REFERENCES rule_difficulty(rule_id),
    timing_dice_count smallint CHECK (timing_dice_count > 0),
    timing_die_sides smallint CHECK (timing_die_sides > 1),
    timing_unit text CHECK (
        timing_unit IN ('seconds', 'rounds', 'minutes')
    ),
    base_cost smallint CHECK (base_cost >= 0),
    cost_per_point boolean NOT NULL DEFAULT false,
    adds_range_cost boolean NOT NULL DEFAULT false,
    requires_check boolean NOT NULL DEFAULT true,
    mechanics_complete boolean NOT NULL DEFAULT true,
    throwing_damage_dice smallint CHECK (throwing_damage_dice >= 0),
    throwing_damage_flat smallint CHECK (throwing_damage_flat >= 0),
    display_order smallint NOT NULL CHECK (display_order > 0),
    UNIQUE (talent_rule_id, power_code),
    CHECK (
        (timing_dice_count IS NULL AND timing_die_sides IS NULL
         AND timing_unit IS NULL)
        OR
        (timing_dice_count IS NOT NULL AND timing_die_sides IS NOT NULL
         AND timing_unit IS NOT NULL)
    ),
    CHECK (
        throwing_damage_dice IS NULL OR throwing_damage_flat IS NULL
    )
);

CREATE TABLE psi_range_band (
    range_band_rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    minimum_metres numeric(12,1) NOT NULL CHECK (minimum_metres >= 0),
    maximum_metres numeric(12,1) NOT NULL CHECK (
        maximum_metres > minimum_metres
    ),
    display_order smallint NOT NULL UNIQUE CHECK (display_order > 0)
);

CREATE TABLE psi_talent_range_cost (
    talent_rule_id bigint NOT NULL REFERENCES psi_talent(talent_rule_id),
    range_band_rule_id bigint NOT NULL
        REFERENCES psi_range_band(range_band_rule_id),
    psionic_strength_cost smallint CHECK (psionic_strength_cost >= 0),
    permitted boolean NOT NULL,
    PRIMARY KEY (talent_rule_id, range_band_rule_id),
    CHECK (
        (permitted AND psionic_strength_cost IS NOT NULL)
        OR (NOT permitted AND psionic_strength_cost IS NULL)
    )
);

CREATE TABLE src_psi_talent_range_cost_provenance (
    talent_rule_id bigint NOT NULL REFERENCES psi_talent(talent_rule_id),
    range_band_rule_id bigint NOT NULL
        REFERENCES psi_range_band(range_band_rule_id),
    source_locator_id bigint NOT NULL REFERENCES src_locator(source_locator_id),
    import_candidate_id bigint REFERENCES src_import_candidate(import_candidate_id),
    source_review_id bigint REFERENCES src_review(source_review_id),
    provenance_class text NOT NULL CHECK (
        provenance_class IN (
            'direct', 'corroborating', 'fills_source_gap',
            'interpretation', 'agreed_addition'
        )
    ),
    is_primary_citation boolean NOT NULL DEFAULT false,
    PRIMARY KEY (
        talent_rule_id, range_band_rule_id, source_locator_id,
        provenance_class
    )
);

COMMENT ON TABLE psi_power IS
    'Mechanical power catalogue only; narrative information remains referee prose.';
