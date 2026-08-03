CREATE TABLE camp_wilderness_encounter_table(
 wilderness_encounter_table_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,campaign_id bigint NOT NULL REFERENCES camp_campaign,
 world_profile_id bigint REFERENCES loc_world_profile,table_code text NOT NULL,terrain_code text NOT NULL REFERENCES rule_animal_terrain,
 template_code text NOT NULL CHECK(template_code IN('1d6','2d6')),title text NOT NULL,UNIQUE(campaign_id,table_code),UNIQUE(wilderness_encounter_table_id,campaign_id)
);
CREATE TABLE camp_wilderness_encounter_entry(
 wilderness_encounter_table_id bigint NOT NULL REFERENCES camp_wilderness_encounter_table,roll_total smallint NOT NULL,
 result_kind text NOT NULL CHECK(result_kind IN('animal','event')),animal_definition_id bigint REFERENCES camp_animal_definition,event_description text,
 PRIMARY KEY(wilderness_encounter_table_id,roll_total),CHECK((result_kind='animal' AND animal_definition_id IS NOT NULL AND event_description IS NULL) OR(result_kind='event' AND animal_definition_id IS NULL AND event_description IS NOT NULL))
);
CREATE TABLE cmd_wilderness_table_finalization_receipt(
 wilderness_table_finalization_receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,wilderness_encounter_table_id bigint NOT NULL UNIQUE REFERENCES camp_wilderness_encounter_table,
 campaign_id bigint NOT NULL,entry_count smallint NOT NULL,source_command_id bigint REFERENCES cmd_command,finalized_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(wilderness_encounter_table_id,campaign_id) REFERENCES camp_wilderness_encounter_table(wilderness_encounter_table_id,campaign_id)
);
CREATE TABLE enc_wilderness_occurrence_receipt(
 wilderness_occurrence_receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,campaign_id bigint NOT NULL REFERENCES camp_campaign,
 wilderness_encounter_table_id bigint NOT NULL,check_date date NOT NULL,check_phase text NOT NULL CHECK(check_phase IN('travelling','halted')),
 occurrence_roll smallint NOT NULL CHECK(occurrence_roll BETWEEN 1 AND 6),occurrence_modifier smallint NOT NULL DEFAULT 0,encounter_occurred boolean NOT NULL,
 table_roll_total smallint,result_kind text CHECK(result_kind IN('animal','event')),animal_definition_id bigint REFERENCES camp_animal_definition,event_description text,
 source_command_id bigint REFERENCES cmd_command,checked_at timestamptz NOT NULL DEFAULT clock_timestamp(),UNIQUE(campaign_id,wilderness_encounter_table_id,check_date,check_phase),
 FOREIGN KEY(wilderness_encounter_table_id,campaign_id) REFERENCES camp_wilderness_encounter_table(wilderness_encounter_table_id,campaign_id),
 CHECK((NOT encounter_occurred AND table_roll_total IS NULL AND result_kind IS NULL AND animal_definition_id IS NULL AND event_description IS NULL)
    OR(encounter_occurred AND table_roll_total IS NOT NULL AND result_kind IS NOT NULL AND ((result_kind='animal' AND animal_definition_id IS NOT NULL AND event_description IS NULL) OR(result_kind='event' AND animal_definition_id IS NULL AND event_description IS NOT NULL))))
);

CREATE FUNCTION enc_validate_wilderness_table() RETURNS trigger LANGUAGE plpgsql AS $$DECLARE t camp_wilderness_encounter_table%ROWTYPE;expected_count integer;actual_count integer;bad_count integer;
BEGIN SELECT * INTO STRICT t FROM camp_wilderness_encounter_table WHERE wilderness_encounter_table_id=NEW.wilderness_encounter_table_id;
 expected_count:=CASE t.template_code WHEN '1d6' THEN 6 ELSE 11 END;
 SELECT count(*),count(*) FILTER(WHERE (template.result_kind='event')<>(entry.result_kind='event')) INTO actual_count,bad_count
 FROM camp_wilderness_encounter_entry entry JOIN rule_wilderness_encounter_template template ON template.template_code=t.template_code AND template.roll_total=entry.roll_total
 WHERE entry.wilderness_encounter_table_id=t.wilderness_encounter_table_id;
 IF NEW.campaign_id<>t.campaign_id OR NEW.entry_count<>expected_count OR actual_count<>expected_count OR bad_count<>0 THEN RAISE EXCEPTION 'Wilderness table is incomplete or violates its template' USING ERRCODE='23514';END IF;RETURN NEW;END$$;
CREATE TRIGGER cmd_wilderness_table_finalization_valid BEFORE INSERT ON cmd_wilderness_table_finalization_receipt FOR EACH ROW EXECUTE FUNCTION enc_validate_wilderness_table();

CREATE FUNCTION enc_validate_wilderness_occurrence() RETURNS trigger LANGUAGE plpgsql AS $$DECLARE e camp_wilderness_encounter_entry%ROWTYPE;
BEGIN IF NEW.encounter_occurred<>((NEW.occurrence_roll+NEW.occurrence_modifier)>=5) THEN RAISE EXCEPTION 'Wilderness occurrence result does not match 5+ check' USING ERRCODE='23514';END IF;
 IF NEW.encounter_occurred THEN SELECT * INTO STRICT e FROM camp_wilderness_encounter_entry WHERE wilderness_encounter_table_id=NEW.wilderness_encounter_table_id AND roll_total=NEW.table_roll_total;
  IF NEW.result_kind<>e.result_kind OR NEW.animal_definition_id IS DISTINCT FROM e.animal_definition_id OR NEW.event_description IS DISTINCT FROM e.event_description THEN RAISE EXCEPTION 'Wilderness encounter result does not match table entry' USING ERRCODE='23514';END IF;
 END IF;RETURN NEW;END$$;
CREATE TRIGGER enc_wilderness_occurrence_valid BEFORE INSERT ON enc_wilderness_occurrence_receipt FOR EACH ROW EXECUTE FUNCTION enc_validate_wilderness_occurrence();

CREATE TRIGGER cmd_wilderness_table_finalization_immutable BEFORE UPDATE OR DELETE ON cmd_wilderness_table_finalization_receipt FOR EACH ROW EXECUTE FUNCTION enc_reject_wilderness_mutation();
CREATE TRIGGER enc_wilderness_occurrence_immutable BEFORE UPDATE OR DELETE ON enc_wilderness_occurrence_receipt FOR EACH ROW EXECUTE FUNCTION enc_reject_wilderness_mutation();
CREATE FUNCTION enc_reject_finalized_wilderness_table_mutation() RETURNS trigger LANGUAGE plpgsql AS $$BEGIN IF EXISTS(SELECT 1 FROM cmd_wilderness_table_finalization_receipt r WHERE r.wilderness_encounter_table_id=OLD.wilderness_encounter_table_id) THEN RAISE EXCEPTION 'Wilderness generation records are immutable' USING ERRCODE='55000';END IF;RETURN OLD;END$$;
CREATE TRIGGER camp_finalized_wilderness_table_immutable BEFORE UPDATE OR DELETE ON camp_wilderness_encounter_table FOR EACH ROW EXECUTE FUNCTION enc_reject_finalized_wilderness_table_mutation();
CREATE TRIGGER camp_finalized_wilderness_entry_immutable BEFORE UPDATE OR DELETE ON camp_wilderness_encounter_entry FOR EACH ROW EXECUTE FUNCTION enc_reject_finalized_wilderness_table_mutation();

CREATE VIEW camp_wilderness_encounter_table_summary AS
SELECT t.wilderness_encounter_table_id,t.campaign_id,t.world_profile_id,t.table_code,t.terrain_code,t.template_code,t.title,count(e.*) entry_count,(f.wilderness_table_finalization_receipt_id IS NOT NULL) finalized
FROM camp_wilderness_encounter_table t LEFT JOIN camp_wilderness_encounter_entry e USING(wilderness_encounter_table_id)
LEFT JOIN cmd_wilderness_table_finalization_receipt f USING(wilderness_encounter_table_id) GROUP BY t.wilderness_encounter_table_id,f.wilderness_table_finalization_receipt_id;
