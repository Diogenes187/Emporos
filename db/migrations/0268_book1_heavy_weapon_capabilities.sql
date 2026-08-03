CREATE TABLE rule_book1_heavy_weapon_capability (
 weapon_rule_id bigint PRIMARY KEY REFERENCES rule_book1_heavy_weapon(rule_id),
 minimum_strength smallint,
 attack_modifier_per_strength_shortfall smallint,
 has_gravity_suspension boolean NOT NULL DEFAULT false,
 reload_minor_actions smallint,
 handheld_grenades_interchangeable boolean,
 full_auto_procedure boolean NOT NULL DEFAULT false,
 burst_mode_permitted boolean,
 backblast_distance_metres numeric,
 backblast_damage_dice smallint,
 vehicle_mount_removes_backblast boolean NOT NULL DEFAULT false,
 radiation_dice_count smallint,
 radiation_die_sides smallint,
 radiation_multiplier_rads smallint,
 radiation_affects_unprotected boolean,
 radiation_radius_is_unquantified boolean NOT NULL DEFAULT false,
 CHECK (minimum_strength IS NULL OR minimum_strength IN (9,12)),
 CHECK (attack_modifier_per_strength_shortfall IS NULL
        OR attack_modifier_per_strength_shortfall=-1),
 CHECK (reload_minor_actions IS NULL OR reload_minor_actions IN (2,3)),
 CHECK ((backblast_distance_metres IS NULL AND backblast_damage_dice IS NULL)
        OR (backblast_distance_metres=1.5 AND backblast_damage_dice=3)),
 CHECK ((radiation_dice_count IS NULL AND radiation_die_sides IS NULL
         AND radiation_multiplier_rads IS NULL AND radiation_affects_unprotected IS NULL)
        OR (radiation_dice_count=2 AND radiation_die_sides=6
         AND radiation_multiplier_rads=20 AND radiation_affects_unprotected))
);
CREATE TABLE rule_book1_rocket_impact (
 weapon_rule_id bigint PRIMARY KEY REFERENCES rule_book1_heavy_weapon(rule_id),
 effect_added_to_damage boolean NOT NULL CHECK (NOT effect_added_to_damage),
 blast_radius_metres smallint NOT NULL CHECK (blast_radius_metres=6),
 miss_detonation_die_sides smallint NOT NULL CHECK (miss_detonation_die_sides=6),
 miss_detonation_minimum_roll smallint NOT NULL CHECK (miss_detonation_minimum_roll=4),
 miss_detonation_distance_base_metres smallint NOT NULL CHECK (
  miss_detonation_distance_base_metres=6),
 miss_detonation_distance_effect_coefficient smallint NOT NULL CHECK (
  miss_detonation_distance_effect_coefficient=-1),
 miss_direction_random boolean NOT NULL CHECK (miss_direction_random),
 failed_detonation_leaves_battlefield boolean NOT NULL CHECK (
  failed_detonation_leaves_battlefield)
);
COMMENT ON TABLE rule_book1_heavy_weapon_capability IS
 'CE-EQUIP-035 typed heavy-weapon exceptions; FGMP immediate-vicinity radius remains unquantified.';
