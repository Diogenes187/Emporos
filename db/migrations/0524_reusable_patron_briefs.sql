INSERT INTO src_locator(source_work_id,source_artifact_id,locator_type,heading_path,display_citation)
SELECT a.source_work_id,a.source_artifact_id,'heading','Social Encounters > Patron Encounters > Format for Patron Encounters',
 CASE w.work_code WHEN 'cepheus-engine.ogn' THEN 'Cepheus Engine SRD, Format for Patron Encounters' ELSE 'Cepheus Engine v9.1, Format for Patron Encounters' END
FROM src_artifact a JOIN src_work w USING(source_work_id)
WHERE (w.work_code='cepheus-engine.github-v9.1' AND a.source_uri='src/book3/social-encounters.md')
 OR (w.work_code='cepheus-engine.ogn' AND a.source_uri='https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-social-encounters/')
ON CONFLICT DO NOTHING;
WITH p AS(SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine')
INSERT INTO rule_rule(content_package_id,rule_code,name,rule_category,rule_status,description)
SELECT content_package_id,'encounter.reusable-patron-format','Reusable Patron Encounter Format','encounter','approved','A reusable patron record identifies patron name and role, required skills and resources, reward, player mission information, and multiple possible referee-truth variants.' FROM p;
INSERT INTO src_record_provenance(rule_id,content_package_id,source_locator_id,provenance_class,is_primary_citation)
SELECT r.rule_id,r.content_package_id,l.source_locator_id,CASE w.work_code WHEN 'cepheus-engine.ogn' THEN 'direct' ELSE 'corroborating' END,w.work_code='cepheus-engine.ogn'
FROM rule_rule r CROSS JOIN src_locator l JOIN src_work w USING(source_work_id) WHERE r.rule_code='encounter.reusable-patron-format' AND l.heading_path='Social Encounters > Patron Encounters > Format for Patron Encounters' AND w.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1');

DO $$ DECLARE d text; BEGIN SELECT pg_get_constraintdef(oid) INTO STRICT d FROM pg_constraint WHERE conrelid='cmd_command'::regclass AND conname='cmd_command_command_type_check'; ALTER TABLE cmd_command DROP CONSTRAINT cmd_command_command_type_check; EXECUTE format('ALTER TABLE cmd_command ADD CONSTRAINT cmd_command_command_type_check %s',replace(d,'CHECK (','CHECK (command_type=''create_patron_brief'' OR ')); END $$;

CREATE TABLE camp_patron_brief(
 patron_brief_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,campaign_id bigint NOT NULL REFERENCES camp_campaign,
 brief_code text NOT NULL CHECK(btrim(brief_code)<>''),brief_status text NOT NULL DEFAULT 'active' CHECK(brief_status IN('active','retired')),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),retired_at timestamptz,UNIQUE(campaign_id,brief_code),UNIQUE(patron_brief_id,campaign_id),CHECK((brief_status='active')=(retired_at IS NULL))
);
CREATE TABLE camp_patron_brief_revision(
 patron_brief_revision_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,patron_brief_id bigint NOT NULL,campaign_id bigint NOT NULL,revision_number integer NOT NULL CHECK(revision_number>0),
 patron_actor_id bigint,patron_d66_result smallint REFERENCES rule_patron_role_roll,patron_name_reference text NOT NULL CHECK(btrim(patron_name_reference)<>''),role_reference text NOT NULL CHECK(btrim(role_reference)<>''),
 reward_summary text NOT NULL CHECK(btrim(reward_summary)<>''),player_mission_summary text NOT NULL CHECK(btrim(player_mission_summary)<>''),created_by_reference text NOT NULL CHECK(btrim(created_by_reference)<>''),created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(patron_brief_id,revision_number),UNIQUE(patron_brief_revision_id,campaign_id),FOREIGN KEY(patron_brief_id,campaign_id) REFERENCES camp_patron_brief(patron_brief_id,campaign_id),FOREIGN KEY(patron_actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id)
);
CREATE TABLE camp_patron_requirement(
 patron_brief_revision_id bigint NOT NULL,campaign_id bigint NOT NULL,requirement_order smallint NOT NULL CHECK(requirement_order>0),requirement_kind text NOT NULL CHECK(requirement_kind IN('skill','resource')),
 skill_rule_id bigint REFERENCES rule_skill(rule_id),requirement_reference text NOT NULL CHECK(btrim(requirement_reference)<>''),PRIMARY KEY(patron_brief_revision_id,requirement_order),
 FOREIGN KEY(patron_brief_revision_id,campaign_id) REFERENCES camp_patron_brief_revision(patron_brief_revision_id,campaign_id),CHECK((requirement_kind='skill')=(skill_rule_id IS NOT NULL))
);
CREATE TABLE camp_patron_truth_variant(
 patron_brief_revision_id bigint NOT NULL,campaign_id bigint NOT NULL,variant_order smallint NOT NULL CHECK(variant_order>0),referee_summary text NOT NULL CHECK(btrim(referee_summary)<>''),
 PRIMARY KEY(patron_brief_revision_id,variant_order),FOREIGN KEY(patron_brief_revision_id,campaign_id) REFERENCES camp_patron_brief_revision(patron_brief_revision_id,campaign_id)
);
CREATE TABLE camp_patron_npc_objective(
 patron_brief_revision_id bigint NOT NULL,campaign_id bigint NOT NULL,objective_order smallint NOT NULL CHECK(objective_order>0),actor_id bigint,
 actor_role_reference text NOT NULL CHECK(btrim(actor_role_reference)<>''),objective_kind text NOT NULL CHECK(objective_kind IN('acquire','deliver','escape','investigate','persuade','protect','rescue','sabotage','survive','travel','other')),
 objective_reference text NOT NULL CHECK(btrim(objective_reference)<>''),priority smallint NOT NULL CHECK(priority BETWEEN 1 AND 5),PRIMARY KEY(patron_brief_revision_id,objective_order),
 FOREIGN KEY(patron_brief_revision_id,campaign_id) REFERENCES camp_patron_brief_revision(patron_brief_revision_id,campaign_id),FOREIGN KEY(actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id)
);
CREATE TABLE cmd_patron_brief_receipt(
 command_id bigint PRIMARY KEY REFERENCES cmd_command,patron_brief_id bigint NOT NULL UNIQUE,patron_brief_revision_id bigint NOT NULL UNIQUE,campaign_id bigint NOT NULL REFERENCES camp_campaign,
 requirement_count smallint NOT NULL CHECK(requirement_count>0),truth_variant_count smallint NOT NULL CHECK(truth_variant_count>=2),npc_objective_count smallint NOT NULL CHECK(npc_objective_count>0),
 FOREIGN KEY(patron_brief_id,campaign_id) REFERENCES camp_patron_brief(patron_brief_id,campaign_id),FOREIGN KEY(patron_brief_revision_id,campaign_id) REFERENCES camp_patron_brief_revision(patron_brief_revision_id,campaign_id)
);
CREATE FUNCTION enc_validate_patron_brief_receipt() RETURNS trigger LANGUAGE plpgsql AS $$DECLARE actual_requirements integer;actual_truths integer;actual_objectives integer;actual_brief bigint;
BEGIN SELECT patron_brief_id INTO STRICT actual_brief FROM camp_patron_brief_revision WHERE patron_brief_revision_id=NEW.patron_brief_revision_id; SELECT count(*) INTO actual_requirements FROM camp_patron_requirement WHERE patron_brief_revision_id=NEW.patron_brief_revision_id; SELECT count(*) INTO actual_truths FROM camp_patron_truth_variant WHERE patron_brief_revision_id=NEW.patron_brief_revision_id; SELECT count(*) INTO actual_objectives FROM camp_patron_npc_objective WHERE patron_brief_revision_id=NEW.patron_brief_revision_id;
 IF actual_brief<>NEW.patron_brief_id OR actual_requirements<>NEW.requirement_count OR actual_truths<>NEW.truth_variant_count OR actual_objectives<>NEW.npc_objective_count THEN RAISE EXCEPTION 'Patron brief receipt does not seal its complete normalized content' USING ERRCODE='23514';END IF;RETURN NEW;END $$;
CREATE TRIGGER cmd_patron_brief_receipt_valid BEFORE INSERT ON cmd_patron_brief_receipt FOR EACH ROW EXECUTE FUNCTION enc_validate_patron_brief_receipt();
CREATE FUNCTION enc_reject_sealed_patron_content_mutation() RETURNS trigger LANGUAGE plpgsql AS $$DECLARE revision bigint;
BEGIN revision:=OLD.patron_brief_revision_id; IF EXISTS(SELECT 1 FROM cmd_patron_brief_receipt WHERE patron_brief_revision_id=revision) THEN RAISE EXCEPTION 'Sealed patron brief content is immutable' USING ERRCODE='55000';END IF;IF TG_OP='DELETE' THEN RETURN OLD;END IF;RETURN NEW;END $$;
CREATE TRIGGER camp_patron_revision_immutable BEFORE UPDATE OR DELETE ON camp_patron_brief_revision FOR EACH ROW EXECUTE FUNCTION enc_reject_sealed_patron_content_mutation();
CREATE TRIGGER camp_patron_requirement_immutable BEFORE UPDATE OR DELETE ON camp_patron_requirement FOR EACH ROW EXECUTE FUNCTION enc_reject_sealed_patron_content_mutation();
CREATE TRIGGER camp_patron_truth_immutable BEFORE UPDATE OR DELETE ON camp_patron_truth_variant FOR EACH ROW EXECUTE FUNCTION enc_reject_sealed_patron_content_mutation();
CREATE TRIGGER camp_patron_objective_immutable BEFORE UPDATE OR DELETE ON camp_patron_npc_objective FOR EACH ROW EXECUTE FUNCTION enc_reject_sealed_patron_content_mutation();
CREATE TRIGGER cmd_patron_brief_receipt_immutable BEFORE UPDATE OR DELETE ON cmd_patron_brief_receipt FOR EACH ROW EXECUTE FUNCTION enc_reject_social_content_selection_mutation();
