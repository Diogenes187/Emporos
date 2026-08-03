CREATE TABLE cmd_starship_subtype_draw(
 command_id bigint NOT NULL REFERENCES cmd_starship_encounter_receipt(command_id),draw_sequence smallint NOT NULL CHECK(draw_sequence>0),
 subtable_code text NOT NULL,die_sides smallint NOT NULL CHECK(die_sides=6),roll_result smallint NOT NULL CHECK(roll_result BETWEEN 1 AND 6),
 result_code text NOT NULL,PRIMARY KEY(command_id,draw_sequence),
 FOREIGN KEY(subtable_code,roll_result) REFERENCES rule_starship_encounter_subtype_roll(subtable_code,roll_total),
 FOREIGN KEY(result_code) REFERENCES rule_starship_encounter_result(result_code)
);
CREATE TABLE cmd_starship_subtype_resolution_receipt(
 command_id bigint PRIMARY KEY REFERENCES cmd_starship_encounter_receipt(command_id),encounter_id bigint NOT NULL UNIQUE REFERENCES enc_starship_contact(encounter_id),
 category_rule_id bigint NOT NULL REFERENCES rule_starship_encounter_category,draw_count smallint NOT NULL CHECK(draw_count>0),
 final_result_code text NOT NULL REFERENCES rule_starship_encounter_result,source_command_id bigint REFERENCES cmd_command(command_id),
 resolved_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE VIEW enc_starship_contact_resolution AS
SELECT c.encounter_id,c.category_rule_id,cat.category_code,r.draw_count,r.final_result_code,result.result_name,result.result_kind,
 result.ship_class_rule_id,ship.class_code,result.effect_code
FROM enc_starship_contact c LEFT JOIN cmd_starship_subtype_resolution_receipt r USING(encounter_id)
LEFT JOIN rule_starship_encounter_category cat ON cat.rule_id=c.category_rule_id
LEFT JOIN rule_starship_encounter_result result ON result.result_code=r.final_result_code
LEFT JOIN ship_class ship ON ship.ship_class_rule_id=result.ship_class_rule_id;

CREATE FUNCTION enc_validate_starship_subtype_draw() RETURNS trigger LANGUAGE plpgsql AS $$DECLARE expected text;
BEGIN SELECT result_code INTO STRICT expected FROM rule_starship_encounter_subtype_roll WHERE subtable_code=NEW.subtable_code AND roll_total=NEW.roll_result;
 IF expected<>NEW.result_code THEN RAISE EXCEPTION 'Starship subtype draw does not match published subtable' USING ERRCODE='23514';END IF;RETURN NEW;END $$;
CREATE TRIGGER cmd_starship_subtype_draw_valid BEFORE INSERT OR UPDATE ON cmd_starship_subtype_draw FOR EACH ROW EXECUTE FUNCTION enc_validate_starship_subtype_draw();

CREATE FUNCTION enc_validate_starship_subtype_resolution() RETURNS trigger LANGUAGE plpgsql AS $$DECLARE contact enc_starship_contact%ROWTYPE;category rule_starship_encounter_category%ROWTYPE;draw record;prior_next text;seen integer:=0;last_result text;
BEGIN SELECT * INTO STRICT contact FROM enc_starship_contact WHERE encounter_id=NEW.encounter_id;SELECT * INTO STRICT category FROM rule_starship_encounter_category WHERE rule_id=NEW.category_rule_id;
 IF contact.category_rule_id<>NEW.category_rule_id THEN RAISE EXCEPTION 'Starship subtype category does not match contact' USING ERRCODE='23514';END IF;
 FOR draw IN SELECT d.*,r.next_subtable_code FROM cmd_starship_subtype_draw d JOIN rule_starship_encounter_result r USING(result_code) WHERE d.command_id=NEW.command_id ORDER BY d.draw_sequence LOOP
  seen:=seen+1;IF draw.draw_sequence<>seen OR (seen=1 AND draw.subtable_code<>category.category_code) OR (seen>1 AND draw.subtable_code<>prior_next) THEN RAISE EXCEPTION 'Starship subtype draw chain is discontinuous' USING ERRCODE='23514';END IF;
  prior_next:=draw.next_subtable_code;last_result:=draw.result_code;
 END LOOP;
 IF seen<>NEW.draw_count OR last_result<>NEW.final_result_code OR prior_next IS NOT NULL THEN RAISE EXCEPTION 'Starship subtype receipt is incomplete or nonterminal' USING ERRCODE='23514';END IF;RETURN NEW;
END $$;
CREATE TRIGGER cmd_starship_subtype_resolution_valid BEFORE INSERT ON cmd_starship_subtype_resolution_receipt FOR EACH ROW EXECUTE FUNCTION enc_validate_starship_subtype_resolution();

CREATE FUNCTION enc_reject_starship_subtype_mutation() RETURNS trigger LANGUAGE plpgsql AS $$BEGIN RAISE EXCEPTION 'Starship subtype receipts are immutable' USING ERRCODE='55000';END $$;
CREATE FUNCTION enc_reject_sealed_starship_subtype_draw_mutation() RETURNS trigger LANGUAGE plpgsql AS $$BEGIN IF EXISTS(SELECT 1 FROM cmd_starship_subtype_resolution_receipt r WHERE r.command_id=OLD.command_id) THEN RAISE EXCEPTION 'Starship subtype receipts are immutable' USING ERRCODE='55000';END IF;RETURN OLD;END $$;
CREATE TRIGGER cmd_starship_subtype_resolution_immutable BEFORE UPDATE OR DELETE ON cmd_starship_subtype_resolution_receipt FOR EACH ROW EXECUTE FUNCTION enc_reject_starship_subtype_mutation();
CREATE TRIGGER cmd_starship_subtype_draw_immutable BEFORE UPDATE OR DELETE ON cmd_starship_subtype_draw FOR EACH ROW EXECUTE FUNCTION enc_reject_sealed_starship_subtype_draw_mutation();
