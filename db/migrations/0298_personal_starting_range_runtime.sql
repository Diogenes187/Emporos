CREATE TABLE enc_personal_combat_starting_range (
    encounter_id bigint PRIMARY KEY REFERENCES enc_personal_combat(encounter_id),
    context_code text NOT NULL REFERENCES rule_personal_starting_range_context,
    light_condition text NOT NULL REFERENCES rule_personal_starting_range_light_cap,
    range_rule_id bigint NOT NULL REFERENCES combat_range_band(rule_id),
    selection_basis text NOT NULL CHECK (
        selection_basis IN ('source_default','source_option','referee_override')),
    referee_override_reason text,
    source_command_id bigint NOT NULL UNIQUE REFERENCES cmd_command(command_id),
    CHECK ((selection_basis='referee_override')=
           (btrim(referee_override_reason)<>''))
);

CREATE FUNCTION enc_reject_personal_starting_range_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Initialized personal-combat starting range is immutable'; END; $$;
CREATE TRIGGER enc_personal_combat_starting_range_immutable
BEFORE UPDATE OR DELETE ON enc_personal_combat_starting_range
FOR EACH ROW EXECUTE FUNCTION enc_reject_personal_starting_range_mutation();

COMMENT ON TABLE enc_personal_combat_starting_range IS
    'Campaign-safe immutable CE-COMBAT-020 context, visibility, range, and referee basis.';
