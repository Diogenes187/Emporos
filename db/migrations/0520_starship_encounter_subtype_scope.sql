CREATE OR REPLACE FUNCTION enc_validate_starship_subtype_resolution() RETURNS trigger LANGUAGE plpgsql AS $$DECLARE contact enc_starship_contact%ROWTYPE;parent cmd_starship_encounter_receipt%ROWTYPE;category rule_starship_encounter_category%ROWTYPE;draw record;prior_next text;seen integer:=0;last_result text;
BEGIN
 SELECT * INTO STRICT parent FROM cmd_starship_encounter_receipt WHERE command_id=NEW.command_id;
 SELECT * INTO STRICT contact FROM enc_starship_contact WHERE encounter_id=NEW.encounter_id;
 SELECT * INTO STRICT category FROM rule_starship_encounter_category WHERE rule_id=NEW.category_rule_id;
 IF parent.encounter_id<>NEW.encounter_id OR parent.category_rule_id<>NEW.category_rule_id OR contact.category_rule_id<>NEW.category_rule_id
    OR NEW.source_command_id IS DISTINCT FROM NEW.command_id THEN
  RAISE EXCEPTION 'Starship subtype receipt crosses command, encounter, or category scope' USING ERRCODE='23514';
 END IF;
 FOR draw IN SELECT d.*,r.next_subtable_code FROM cmd_starship_subtype_draw d JOIN rule_starship_encounter_result r USING(result_code) WHERE d.command_id=NEW.command_id ORDER BY d.draw_sequence LOOP
  seen:=seen+1;
  IF draw.draw_sequence<>seen OR (seen=1 AND draw.subtable_code<>category.category_code) OR (seen>1 AND draw.subtable_code<>prior_next) THEN
   RAISE EXCEPTION 'Starship subtype draw chain is discontinuous' USING ERRCODE='23514';
  END IF;
  prior_next:=draw.next_subtable_code;last_result:=draw.result_code;
 END LOOP;
 IF seen<>NEW.draw_count OR last_result<>NEW.final_result_code OR prior_next IS NOT NULL THEN
  RAISE EXCEPTION 'Starship subtype receipt is incomplete or nonterminal' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
