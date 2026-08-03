ALTER TABLE enc_personal_combat_starting_range
DROP CONSTRAINT enc_personal_combat_starting_range_check;
ALTER TABLE enc_personal_combat_starting_range
ADD CONSTRAINT starting_range_override_reason_check CHECK (
    (selection_basis='referee_override'
     AND referee_override_reason IS NOT NULL
     AND btrim(referee_override_reason)<>'')
    OR (selection_basis<>'referee_override'
        AND referee_override_reason IS NULL)
);

CREATE FUNCTION enc_validate_personal_starting_range()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE selected_order smallint;
DECLARE cap_order smallint;
DECLARE command_type text;
BEGIN
 SELECT display_order INTO STRICT selected_order FROM combat_range_band
  WHERE rule_id=NEW.range_rule_id;
 SELECT band.display_order INTO cap_order
 FROM rule_personal_starting_range_light_cap light
 LEFT JOIN combat_range_band band
   ON band.rule_id=light.maximum_range_rule_id
 WHERE light.light_condition=NEW.light_condition;
 SELECT command.command_type INTO STRICT command_type FROM cmd_command command
  WHERE command.command_id=NEW.source_command_id;
 IF command_type<>'initialize_personal_combat'
    OR (cap_order IS NOT NULL AND selected_order>cap_order)
    OR (NEW.selection_basis<>'referee_override' AND NOT EXISTS (
      SELECT 1 FROM rule_personal_starting_range_option option
      WHERE option.context_code=NEW.context_code
        AND option.range_rule_id=NEW.range_rule_id)) THEN
   RAISE EXCEPTION 'Starting Range does not match source context or light cap';
 END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER enc_personal_combat_starting_range_valid
BEFORE INSERT ON enc_personal_combat_starting_range
FOR EACH ROW EXECUTE FUNCTION enc_validate_personal_starting_range();
