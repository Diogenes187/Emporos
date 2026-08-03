CREATE TABLE rule_psi_assault (
    power_rule_id bigint PRIMARY KEY REFERENCES psi_power(power_rule_id),
    renders_unconscious_immediately boolean NOT NULL CHECK (
        renders_unconscious_immediately
    ),
    damage_dice_count smallint NOT NULL CHECK (damage_dice_count=2),
    damage_die_sides smallint NOT NULL CHECK (damage_die_sides=6),
    adds_activation_effect_to_damage boolean NOT NULL CHECK (
        adds_activation_effect_to_damage
    ),
    damage_psionic_strength_first boolean NOT NULL CHECK (
        damage_psionic_strength_first
    ),
    damage_intelligence_second boolean NOT NULL CHECK (
        damage_intelligence_second
    ),
    damage_endurance_third boolean NOT NULL CHECK (
        damage_endurance_third
    ),
    psionic_strength_recovers_normally boolean NOT NULL CHECK (
        psionic_strength_recovers_normally
    ),
    endurance_recovers_normally boolean NOT NULL CHECK (
        endurance_recovers_normally
    ),
    intelligence_points_per_day smallint NOT NULL CHECK (
        intelligence_points_per_day=1
    ),
    shielded_target_uses_opposed_telepathy boolean NOT NULL CHECK (
        shielded_target_uses_opposed_telepathy
    ),
    attacker_win_damages_shielded_target boolean NOT NULL CHECK (
        attacker_win_damages_shielded_target
    )
);

COMMENT ON TABLE rule_psi_assault IS
    'CE-PSI-013 website-first Assault mechanics; GitHub prose omits its activation line and shielded-target paragraph.';
