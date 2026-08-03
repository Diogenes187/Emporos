CREATE TABLE rule_animal_subtype_skill(
 subtype_rule_id bigint NOT NULL REFERENCES rule_animal_subtype,skill_code text NOT NULL,
 PRIMARY KEY(subtype_rule_id,skill_code)
);
INSERT INTO rule_animal_subtype_skill
SELECT s.rule_id,x.skill_code FROM rule_animal_subtype s JOIN (VALUES
 ('carrion-eater','recon'),('chaser','athletics'),('gatherer','recon'),('hunter','survival'),
 ('killer','natural-weapons'),('pouncer','athletics'),('pouncer','recon')
) x(subtype_code,skill_code) USING(subtype_code);

CREATE TABLE camp_animal_definition_skill_source(
 animal_definition_id bigint NOT NULL,skill_code text NOT NULL,source_kind text NOT NULL CHECK(source_kind IN('baseline','rolled-pool','subtype')),
 PRIMARY KEY(animal_definition_id,skill_code,source_kind),
 FOREIGN KEY(animal_definition_id,skill_code) REFERENCES camp_animal_definition_skill(animal_definition_id,skill_code)
);

CREATE FUNCTION enc_validate_animal_subtype_skills() RETURNS trigger LANGUAGE plpgsql AS $$DECLARE d camp_animal_definition%ROWTYPE;missing_count integer;extra_count integer;
BEGIN SELECT * INTO STRICT d FROM camp_animal_definition WHERE animal_definition_id=NEW.animal_definition_id;
 SELECT count(*) INTO missing_count FROM rule_animal_subtype_skill required WHERE required.subtype_rule_id=d.subtype_rule_id AND NOT EXISTS(
  SELECT 1 FROM camp_animal_definition_skill_source actual WHERE actual.animal_definition_id=d.animal_definition_id AND actual.skill_code=required.skill_code AND actual.source_kind='subtype');
 SELECT count(*) INTO extra_count FROM camp_animal_definition_skill_source actual WHERE actual.animal_definition_id=d.animal_definition_id AND actual.source_kind='subtype' AND NOT EXISTS(
  SELECT 1 FROM rule_animal_subtype_skill required WHERE required.subtype_rule_id=d.subtype_rule_id AND required.skill_code=actual.skill_code);
 IF missing_count<>0 OR extra_count<>0 THEN RAISE EXCEPTION 'Animal subtype skill sources do not match published grants' USING ERRCODE='23514';END IF;RETURN NEW;
END $$;
CREATE TRIGGER cmd_animal_generation_subtype_skills_valid BEFORE INSERT ON cmd_animal_generation_receipt FOR EACH ROW EXECUTE FUNCTION enc_validate_animal_subtype_skills();
CREATE TRIGGER camp_generated_animal_skill_source_immutable BEFORE UPDATE OR DELETE ON camp_animal_definition_skill_source FOR EACH ROW EXECUTE FUNCTION enc_reject_generated_animal_mutation();
