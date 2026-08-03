CREATE TABLE rule_psi_teleportation_system (
    talent_rule_id bigint PRIMARY KEY REFERENCES psi_talent(talent_rule_id),
    effectively_instantaneous boolean NOT NULL CHECK (
        effectively_instantaneous
    ),
    ignores_intervening_matter boolean NOT NULL CHECK (
        ignores_intervening_matter
    ),
    always_moves_psion_body boolean NOT NULL CHECK (always_moves_psion_body),
    independent_items_prohibited boolean NOT NULL CHECK (
        independent_items_prohibited
    ),
    other_individuals_prohibited boolean NOT NULL CHECK (
        other_individuals_prohibited
    ),
    destination_mental_image_required boolean NOT NULL CHECK (
        destination_mental_image_required
    ),
    personal_visit_permitted boolean NOT NULL CHECK (personal_visit_permitted),
    distant_view_permitted boolean NOT NULL CHECK (distant_view_permitted),
    telepathic_implant_permitted boolean NOT NULL CHECK (
        telepathic_implant_permitted
    ),
    clairvoyant_view_permitted boolean NOT NULL CHECK (
        clairvoyant_view_permitted
    ),
    recorded_image_prohibited boolean NOT NULL CHECK (
        recorded_image_prohibited
    ),
    planetary_maximum_range_rule_id bigint NOT NULL
        REFERENCES psi_range_band(range_band_rule_id),
    maximum_safe_single_altitude_metres integer NOT NULL CHECK (
        maximum_safe_single_altitude_metres=400
    ),
    maximum_safe_hourly_altitude_metres integer NOT NULL CHECK (
        maximum_safe_hourly_altitude_metres=600
    ),
    temperature_change_celsius_per_km numeric(3,1) NOT NULL CHECK (
        temperature_change_celsius_per_km=2.5
    ),
    fast_vehicle_uses_ramming_damage boolean NOT NULL CHECK (
        fast_vehicle_uses_ramming_damage
    )
);

CREATE TABLE rule_psi_teleportation_power (
    power_rule_id bigint PRIMARY KEY REFERENCES psi_power(power_rule_id),
    load_kind text NOT NULL UNIQUE CHECK (
        load_kind IN ('unclothed','light','moderate','heavy')
    ),
    includes_clothing_or_possessions boolean NOT NULL,
    display_order smallint NOT NULL UNIQUE CHECK (display_order BETWEEN 1 AND 4)
);

CREATE TABLE rule_psi_teleportation_disorientation (
    talent_rule_id bigint PRIMARY KEY REFERENCES
        rule_psi_teleportation_system(talent_rule_id),
    range_band_rule_id bigint NOT NULL UNIQUE
        REFERENCES psi_range_band(range_band_rule_id),
    duration_dice_count smallint NOT NULL CHECK (duration_dice_count=2),
    duration_die_sides smallint NOT NULL CHECK (duration_die_sides=6),
    duration_multiplier_seconds smallint NOT NULL CHECK (
        duration_multiplier_seconds=10
    )
);

COMMENT ON TABLE rule_psi_teleportation_system IS
    'CE-PSI-016 paired-source destination knowledge, conservation, and safety limits.';
COMMENT ON TABLE rule_psi_teleportation_power IS
    'Published four-level self-teleport load profiles.';
