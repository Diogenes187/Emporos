CREATE TABLE rule_personal_weapon_readying (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    default_minor_actions smallint NOT NULL CHECK (default_minor_actions=1),
    time_depends_on_size_and_ease boolean NOT NULL CHECK (
        time_depends_on_size_and_ease),
    weapon_description_governs_specific_time boolean NOT NULL CHECK (
        weapon_description_governs_specific_time),
    especially_fast_or_slow_exceptions_exist boolean NOT NULL CHECK (
        especially_fast_or_slow_exceptions_exist),
    source_specific_profiles_absent boolean NOT NULL CHECK (
        source_specific_profiles_absent),
    referee_override_requires_reason boolean NOT NULL CHECK (
        referee_override_requires_reason)
);

CREATE TABLE inv_weapon_ready_profile (
    weapon_rule_id bigint PRIMARY KEY REFERENCES inv_weapon_definition(item_rule_id),
    ready_minor_actions smallint NOT NULL CHECK (ready_minor_actions>0),
    source_locator_id bigint NOT NULL REFERENCES src_locator(source_locator_id),
    profile_note text NOT NULL CHECK (btrim(profile_note)<>'')
);

COMMENT ON TABLE rule_personal_weapon_readying IS
    'CE-COMBAT-021 published one-minor default plus documented missing specific profiles.';
COMMENT ON TABLE inv_weapon_ready_profile IS
    'Reserved only for explicit per-weapon source exceptions; intentionally empty in v9.1.';
