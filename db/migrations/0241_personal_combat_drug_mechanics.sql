CREATE TABLE rule_personal_combat_drug_effect (
    drug_rule_id bigint PRIMARY KEY REFERENCES
        inv_personal_drug_definition(item_rule_id),
    initiative_modifier integer NOT NULL CHECK (
        initiative_modifier IN (4,8)),
    free_dodges_per_round integer NOT NULL CHECK (
        free_dodges_per_round IN (1,2)),
    free_dodges_change_initiative boolean NOT NULL CHECK (
        NOT free_dodges_change_initiative),
    damage_reduction integer NOT NULL CHECK (damage_reduction IN (0,2)),
    activation_seconds integer NOT NULL CHECK (
        activation_seconds IN (20,45)),
    activation_rounds integer NOT NULL CHECK (
        activation_rounds IN (4,8)),
    printed_timings_not_equivalent_at_six_seconds boolean NOT NULL CHECK (
        printed_timings_not_equivalent_at_six_seconds),
    approximate_duration_seconds integer NOT NULL CHECK (
        approximate_duration_seconds=600),
    duration_is_approximate boolean NOT NULL CHECK (duration_is_approximate),
    aftermath_code text NOT NULL CHECK (
        aftermath_code IN ('fatigued','damage-and-exhausted')),
    aftermath_damage_dice_count integer NOT NULL CHECK (
        aftermath_damage_dice_count IN (0,2)),
    aftermath_damage_die_sides integer CHECK (
        aftermath_damage_die_sides=6),
    CHECK (
        (initiative_modifier=4 AND free_dodges_per_round=1
         AND damage_reduction=2 AND activation_seconds=20
         AND activation_rounds=4 AND aftermath_code='fatigued'
         AND aftermath_damage_dice_count=0
         AND aftermath_damage_die_sides IS NULL)
        OR
        (initiative_modifier=8 AND free_dodges_per_round=2
         AND damage_reduction=0 AND activation_seconds=45
         AND activation_rounds=8
         AND aftermath_code='damage-and-exhausted'
         AND aftermath_damage_dice_count=2
         AND aftermath_damage_die_sides=6))
);

CREATE TABLE rule_personal_antiradiation_drug (
    drug_rule_id bigint PRIMARY KEY REFERENCES
        inv_personal_drug_definition(item_rule_id),
    may_administer_before_exposure boolean NOT NULL CHECK (
        may_administer_before_exposure),
    post_exposure_window_seconds integer NOT NULL CHECK (
        post_exposure_window_seconds=600),
    absorbed_rads_per_dose integer NOT NULL CHECK (
        absorbed_rads_per_dose=100),
    safe_doses_per_day integer NOT NULL CHECK (safe_doses_per_day=1),
    excess_dose_endurance_damage_dice integer NOT NULL CHECK (
        excess_dose_endurance_damage_dice=1),
    excess_dose_endurance_damage_die_sides integer NOT NULL CHECK (
        excess_dose_endurance_damage_die_sides=6),
    excess_damage_is_per_dose boolean NOT NULL CHECK (
        excess_damage_is_per_dose),
    endurance_damage_is_permanent boolean NOT NULL CHECK (
        endurance_damage_is_permanent)
);

CREATE TABLE rule_personal_stim_drug (
    drug_rule_id bigint PRIMARY KEY REFERENCES
        inv_personal_drug_definition(item_rule_id),
    removes_fatigue boolean NOT NULL CHECK (removes_fatigue),
    damage_equals_use_sequence_since_sleep boolean NOT NULL CHECK (
        damage_equals_use_sequence_since_sleep),
    sleep_resets_use_sequence boolean NOT NULL CHECK (
        sleep_resets_use_sequence)
);

COMMENT ON TABLE rule_personal_combat_drug_effect IS
    'CE-EQUIP-010 preserves dual printed activation timings independently.';
