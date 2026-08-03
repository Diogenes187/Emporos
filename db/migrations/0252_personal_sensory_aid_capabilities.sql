CREATE TABLE rule_personal_sensory_aid_capability (
    sensory_aid_rule_id bigint NOT NULL REFERENCES
        inv_personal_sensory_aid_definition(item_rule_id),
    capability_code text NOT NULL CHECK (btrim(capability_code)<>''),
    operating_duration_seconds integer CHECK (operating_duration_seconds>0),
    duration_is_approximate boolean,
    requires_non_total_darkness boolean NOT NULL DEFAULT false,
    detects_heat_emitting_sources boolean NOT NULL DEFAULT false,
    viewing_distance_is_unquantified boolean NOT NULL DEFAULT false,
    PRIMARY KEY (sensory_aid_rule_id,capability_code),
    CHECK (
        (operating_duration_seconds IS NULL) =
        (duration_is_approximate IS NULL))
);

CREATE TABLE rule_personal_sensory_aid_illumination_mode (
    sensory_aid_rule_id bigint NOT NULL REFERENCES
        inv_personal_sensory_aid_definition(item_rule_id),
    mode_code text NOT NULL CHECK (
        mode_code IN ('radial','wide-cone','tight-beam','area')),
    minimum_tech_level integer,
    clear_radius_metres numeric CHECK (clear_radius_metres>0),
    shadow_radius_metres numeric CHECK (shadow_radius_metres>0),
    beam_length_metres numeric CHECK (beam_length_metres>0),
    beam_end_radius_metres numeric CHECK (beam_end_radius_metres>0),
    later_tech_level_is_unquantified boolean NOT NULL DEFAULT false,
    PRIMARY KEY (sensory_aid_rule_id,mode_code),
    CHECK (
        (mode_code='radial' AND clear_radius_metres IS NOT NULL
         AND beam_length_metres IS NULL AND beam_end_radius_metres IS NULL)
        OR
        (mode_code IN ('wide-cone','tight-beam')
         AND clear_radius_metres IS NULL
         AND shadow_radius_metres IS NULL
         AND beam_length_metres IS NOT NULL
         AND beam_end_radius_metres IS NOT NULL)
        OR
        (mode_code='area' AND clear_radius_metres IS NOT NULL
         AND shadow_radius_metres IS NULL
         AND beam_length_metres IS NULL
         AND beam_end_radius_metres IS NULL)),
    CHECK (
        (minimum_tech_level IS NULL)=later_tech_level_is_unquantified)
);

CREATE TABLE rule_personal_binocular_upgrade (
    binocular_rule_id bigint NOT NULL REFERENCES
        inv_personal_sensory_aid_definition(item_rule_id),
    minimum_tech_level integer NOT NULL CHECK (
        minimum_tech_level IN (8,12)),
    cost_credits bigint NOT NULL CHECK (cost_credits>0),
    image_capture boolean NOT NULL,
    light_intensification boolean NOT NULL,
    portable_radiation_imaging_system boolean NOT NULL,
    spectrum_low_code text,
    spectrum_high_code text,
    PRIMARY KEY (binocular_rule_id,minimum_tech_level),
    CHECK (
        (minimum_tech_level=8 AND cost_credits=750
         AND image_capture AND light_intensification
         AND NOT portable_radiation_imaging_system
         AND spectrum_low_code IS NULL AND spectrum_high_code IS NULL)
        OR
        (minimum_tech_level=12 AND cost_credits=3500
         AND NOT image_capture AND NOT light_intensification
         AND portable_radiation_imaging_system
         AND spectrum_low_code='infrared'
         AND spectrum_high_code='gamma-rays'))
);

COMMENT ON TABLE rule_personal_sensory_aid_capability IS
    'CE-EQUIP-020 normalized Sensory Aids operating capabilities.';
