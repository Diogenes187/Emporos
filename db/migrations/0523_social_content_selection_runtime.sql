DO $$ DECLARE d text; BEGIN SELECT pg_get_constraintdef(oid) INTO STRICT d FROM pg_constraint WHERE conrelid='cmd_command'::regclass AND conname='cmd_command_command_type_check'; ALTER TABLE cmd_command DROP CONSTRAINT cmd_command_command_type_check; EXECUTE format('ALTER TABLE cmd_command ADD CONSTRAINT cmd_command_command_type_check %s',replace(d,'CHECK (','CHECK (command_type=''select_social_content'' OR ')); END $$;

CREATE TABLE cmd_social_content_selection_receipt(
 command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
 encounter_id bigint NOT NULL REFERENCES enc_encounter(encounter_id),content_kind text NOT NULL CHECK(content_kind IN('patron','rumor')),
 tens_die smallint NOT NULL CHECK(tens_die BETWEEN 1 AND 6),ones_die smallint NOT NULL CHECK(ones_die BETWEEN 1 AND 6),
 d66_result smallint NOT NULL CHECK(d66_result=tens_die*10+ones_die),patron_d66_result smallint REFERENCES rule_patron_role_roll,
 rumor_d66_result smallint REFERENCES rule_rumor_content_roll,referee_choice boolean NOT NULL,selected_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(encounter_id,campaign_id) REFERENCES enc_encounter(encounter_id,campaign_id),
 CHECK((content_kind='patron' AND patron_d66_result=d66_result AND rumor_d66_result IS NULL) OR (content_kind='rumor' AND rumor_d66_result=d66_result AND patron_d66_result IS NULL))
);
CREATE UNIQUE INDEX cmd_social_content_one_kind_per_encounter ON cmd_social_content_selection_receipt(encounter_id,content_kind);

CREATE FUNCTION enc_validate_social_content_selection() RETURNS trigger LANGUAGE plpgsql AS $$DECLARE actual_kind text;actual_choice boolean;
BEGIN
 SELECT t.encounter_type_code INTO STRICT actual_kind FROM enc_encounter e JOIN rule_encounter_type t ON t.rule_id=e.encounter_type_rule_id WHERE e.encounter_id=NEW.encounter_id;
 IF actual_kind<>NEW.content_kind THEN RAISE EXCEPTION 'Social content kind must match encounter type' USING ERRCODE='23514';END IF;
 IF NEW.content_kind='patron' THEN SELECT referee_choice INTO STRICT actual_choice FROM rule_patron_role_roll WHERE d66_result=NEW.d66_result;
 ELSE SELECT referee_choice INTO STRICT actual_choice FROM rule_rumor_content_roll WHERE d66_result=NEW.d66_result;END IF;
 IF actual_choice<>NEW.referee_choice THEN RAISE EXCEPTION 'Social content referee-choice flag does not match published result' USING ERRCODE='23514';END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER cmd_social_content_selection_valid BEFORE INSERT ON cmd_social_content_selection_receipt FOR EACH ROW EXECUTE FUNCTION enc_validate_social_content_selection();
CREATE FUNCTION enc_reject_social_content_selection_mutation() RETURNS trigger LANGUAGE plpgsql AS $$BEGIN RAISE EXCEPTION 'Social content selection receipts are immutable' USING ERRCODE='55000';END $$;
CREATE TRIGGER cmd_social_content_selection_immutable BEFORE UPDATE OR DELETE ON cmd_social_content_selection_receipt FOR EACH ROW EXECUTE FUNCTION enc_reject_social_content_selection_mutation();

CREATE VIEW enc_social_content_selection AS
SELECT x.encounter_id,x.content_kind,x.d66_result,coalesce(p.role_code,r.content_code) content_code,coalesce(p.role_name,r.content_name) content_name,x.referee_choice,x.command_id
FROM cmd_social_content_selection_receipt x LEFT JOIN rule_patron_role_roll p ON p.d66_result=x.patron_d66_result LEFT JOIN rule_rumor_content_roll r ON r.d66_result=x.rumor_d66_result;
