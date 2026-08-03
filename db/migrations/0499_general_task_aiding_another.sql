INSERT INTO src_locator (
    source_work_id,source_artifact_id,locator_type,heading_path,display_citation
)
SELECT DISTINCT ON (work.work_code) artifact.source_work_id,
       artifact.source_artifact_id,'heading','Introduction > Aiding Another',
       CASE work.work_code WHEN 'cepheus-engine.ogn'
         THEN 'Cepheus Engine SRD, Introduction: Aiding Another'
         ELSE 'Cepheus Engine v9.1, Introduction: Aiding Another' END
FROM src_artifact artifact JOIN src_work work USING(source_work_id)
WHERE artifact.source_uri IN(
    'https://cepheus-srd.opengamingnetwork.com/','src/introduction.md'
)
ORDER BY work.work_code,artifact.source_artifact_id
ON CONFLICT DO NOTHING;

WITH package AS (
    SELECT content_package_id FROM sys_content_package
    WHERE package_code='cepheus-engine'
)
INSERT INTO rule_rule(
    content_package_id,rule_code,name,rule_category,rule_status,description
)
SELECT content_package_id,'task.aiding-another','Aiding Another','task','approved',
       'A helper check modifies the leader by Effect band; the Referee limits whether and how many helpers may aid.'
FROM package;

CREATE TABLE rule_task_assistance_effect (
    assistance_effect_code text PRIMARY KEY,
    effect_minimum smallint,
    effect_maximum smallint,
    assistance_modifier smallint NOT NULL CHECK (assistance_modifier IN(-2,-1,1,2)),
    CHECK (effect_minimum IS NULL OR effect_maximum IS NULL OR effect_minimum<=effect_maximum)
);

INSERT INTO rule_task_assistance_effect VALUES
    ('exceptional-failure',NULL,-6,-2),
    ('failure',-5,-1,-1),
    ('success',0,5,1),
    ('exceptional-success',6,NULL,2);

INSERT INTO src_record_provenance(
    rule_id,content_package_id,source_locator_id,provenance_class,is_primary_citation
)
SELECT rule.rule_id,rule.content_package_id,locator.source_locator_id,
       CASE work.work_code WHEN 'cepheus-engine.ogn' THEN 'direct' ELSE 'corroborating' END,
       work.work_code='cepheus-engine.ogn'
FROM rule_rule rule CROSS JOIN src_locator locator
JOIN src_work work USING(source_work_id)
WHERE rule.rule_code='task.aiding-another'
  AND locator.heading_path='Introduction > Aiding Another'
  AND work.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1');

CREATE TABLE cmd_task_assistance_receipt (
    task_assistance_receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    leader_task_command_id bigint NOT NULL REFERENCES cmd_actor_task_receipt(command_id),
    helper_task_command_id bigint NOT NULL UNIQUE REFERENCES cmd_actor_task_receipt(command_id),
    assistance_context text NOT NULL CHECK (btrim(assistance_context)<>''),
    assistance_mode text NOT NULL CHECK (assistance_mode IN('same-check','source-prescribed-check')),
    helper_effect smallint NOT NULL,
    assistance_effect_code text NOT NULL REFERENCES rule_task_assistance_effect(assistance_effect_code),
    assistance_modifier smallint NOT NULL CHECK (assistance_modifier IN(-2,-1,1,2)),
    referee_authorized boolean NOT NULL CHECK (referee_authorized),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE(leader_task_command_id,helper_task_command_id),
    CHECK (leader_task_command_id<>helper_task_command_id)
);

CREATE FUNCTION cmd_validate_task_assistance()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE leader cmd_actor_task_receipt%ROWTYPE; helper cmd_actor_task_receipt%ROWTYPE;
        expected_code text; expected_modifier smallint;
BEGIN
    SELECT * INTO STRICT leader FROM cmd_actor_task_receipt
    WHERE command_id=NEW.leader_task_command_id;
    SELECT * INTO STRICT helper FROM cmd_actor_task_receipt
    WHERE command_id=NEW.helper_task_command_id;
    SELECT assistance_effect_code,assistance_modifier
    INTO STRICT expected_code,expected_modifier
    FROM rule_task_assistance_effect
    WHERE (effect_minimum IS NULL OR helper.effect>=effect_minimum)
      AND (effect_maximum IS NULL OR helper.effect<=effect_maximum);
    IF leader.actor_id=helper.actor_id OR NEW.helper_effect<>helper.effect
       OR NEW.assistance_effect_code<>expected_code
       OR NEW.assistance_modifier<>expected_modifier THEN
        RAISE EXCEPTION 'Task assistance does not match distinct actors or the helper Effect band' USING ERRCODE='23514';
    END IF;
    IF NEW.assistance_mode='same-check' AND (
       leader.characteristic_rule_id,leader.skill_rule_id,leader.difficulty_rule_id
    ) IS DISTINCT FROM (
       helper.characteristic_rule_id,helper.skill_rule_id,helper.difficulty_rule_id
    ) THEN
        RAISE EXCEPTION 'General Aiding Another requires the same check' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER cmd_task_assistance_valid
BEFORE INSERT OR UPDATE ON cmd_task_assistance_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_validate_task_assistance();

CREATE FUNCTION cmd_reject_task_assistance_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
    RAISE EXCEPTION 'Task assistance receipts are immutable';
END $$;

CREATE TRIGGER cmd_task_assistance_immutable
BEFORE UPDATE OR DELETE ON cmd_task_assistance_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_task_assistance_mutation();
