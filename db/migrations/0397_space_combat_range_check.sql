INSERT INTO src_locator(source_work_id,source_artifact_id,locator_type,heading_path,display_citation)
SELECT artifact.source_work_id,artifact.source_artifact_id,'heading',
       'Space Combat > Significant Actions > Range Check',
       CASE work.work_code WHEN 'cepheus-engine.ogn'
         THEN 'Cepheus Engine SRD, Space Combat: Range Check'
         ELSE 'Cepheus Engine v9.1, Space Combat: Range Check' END
FROM src_artifact artifact JOIN src_work work USING(source_work_id)
WHERE (work.work_code='cepheus-engine.ogn' AND artifact.source_uri LIKE '%cepheus-engine-space-combat/')
   OR (work.work_code='cepheus-engine.github-v9.1' AND artifact.source_uri='src/book2/space-combat.md')
ON CONFLICT DO NOTHING;

WITH package AS (SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine')
INSERT INTO rule_rule(content_package_id,rule_code,name,rule_category,rule_status,description)
SELECT content_package_id,'combat.space.range-check','Space Combat Range Check','combat','approved',
       'Opposed Navigation check controlling one range-band change or maintenance.'
FROM package;

CREATE TABLE rule_space_combat_range_check(
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    skill_rule_id bigint NOT NULL REFERENCES rule_skill(rule_id),
    maximum_band_change smallint NOT NULL CHECK(maximum_band_change=1),
    winner_may_increase boolean NOT NULL,
    winner_may_decrease boolean NOT NULL,
    winner_may_maintain boolean NOT NULL,
    opposed_tie_uses_characteristic boolean NOT NULL,
    full_tie_requires_reroll boolean NOT NULL
);
INSERT INTO rule_space_combat_range_check
SELECT range_rule.rule_id,skill.rule_id,1,true,true,true,true,true
FROM rule_rule range_rule CROSS JOIN rule_rule skill
WHERE range_rule.rule_code='combat.space.range-check'
  AND skill.rule_code='skill.navigation';

INSERT INTO src_record_provenance(rule_id,content_package_id,source_locator_id,provenance_class,is_primary_citation)
SELECT rule.rule_id,rule.content_package_id,locator.source_locator_id,
       CASE work.work_code WHEN 'cepheus-engine.ogn' THEN 'direct' ELSE 'corroborating' END,
       work.work_code='cepheus-engine.ogn'
FROM rule_rule rule CROSS JOIN src_locator locator JOIN src_work work USING(source_work_id)
WHERE rule.rule_code='combat.space.range-check'
  AND locator.heading_path='Space Combat > Significant Actions > Range Check'
  AND work.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1');

CREATE TABLE senc_range_check_receipt(
    range_check_receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    engagement_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    space_combat_round_id bigint NOT NULL,
    first_vessel_id bigint NOT NULL,
    second_vessel_id bigint NOT NULL,
    first_action_id bigint NOT NULL UNIQUE,
    second_action_id bigint NOT NULL UNIQUE,
    first_task_command_id bigint NOT NULL UNIQUE REFERENCES cmd_actor_task_receipt(command_id),
    second_task_command_id bigint NOT NULL UNIQUE REFERENCES cmd_actor_task_receipt(command_id),
    first_effect smallint NOT NULL,
    second_effect smallint NOT NULL,
    first_characteristic_value smallint NOT NULL,
    second_characteristic_value smallint NOT NULL,
    winning_vessel_id bigint,
    resolution_status text NOT NULL CHECK(resolution_status IN('resolved','reroll-required')),
    elected_change text CHECK(elected_change IN('increase','decrease','maintain')),
    range_band_before text NOT NULL REFERENCES rule_space_range_band(range_band_code),
    range_band_after text NOT NULL REFERENCES rule_space_range_band(range_band_code),
    range_version_before bigint NOT NULL CHECK(range_version_before>0),
    range_version_after bigint NOT NULL CHECK(range_version_after>0),
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    FOREIGN KEY(space_combat_round_id,engagement_id,campaign_id)
      REFERENCES senc_round(space_combat_round_id,engagement_id,campaign_id),
    FOREIGN KEY(first_vessel_id,engagement_id,campaign_id)
      REFERENCES senc_vessel(senc_vessel_id,engagement_id,campaign_id),
    FOREIGN KEY(second_vessel_id,engagement_id,campaign_id)
      REFERENCES senc_vessel(senc_vessel_id,engagement_id,campaign_id),
    FOREIGN KEY(first_action_id,engagement_id,campaign_id)
      REFERENCES senc_action(space_combat_action_id,engagement_id,campaign_id),
    FOREIGN KEY(second_action_id,engagement_id,campaign_id)
      REFERENCES senc_action(space_combat_action_id,engagement_id,campaign_id),
    FOREIGN KEY(winning_vessel_id,engagement_id,campaign_id)
      REFERENCES senc_vessel(senc_vessel_id,engagement_id,campaign_id),
    CHECK(first_vessel_id<second_vessel_id),
    CHECK(range_version_after=range_version_before+1),
    CHECK((resolution_status='reroll-required' AND winning_vessel_id IS NULL
           AND elected_change IS NULL AND range_band_after=range_band_before)
       OR (resolution_status='resolved' AND winning_vessel_id IS NOT NULL
           AND elected_change IS NOT NULL))
);

CREATE FUNCTION senc_validate_range_check_receipt()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    current_range senc_vessel_range%ROWTYPE;
    first_action record; second_action record;
    first_task record; second_task record;
    expected_winner bigint; before_order smallint; after_order smallint;
BEGIN
    SELECT * INTO STRICT current_range FROM senc_vessel_range
    WHERE engagement_id=NEW.engagement_id AND first_vessel_id=NEW.first_vessel_id
      AND second_vessel_id=NEW.second_vessel_id FOR UPDATE;
    SELECT action.action_code,action.target_vessel_id,turn.senc_vessel_id,
           assignment.actor_id,definition.position_code
    INTO first_action
    FROM senc_action action JOIN senc_crew_turn turn USING(crew_turn_id)
    JOIN ship_crew_assignment assignment USING(crew_assignment_id)
    JOIN ship_crew_position position_state USING(ship_crew_position_id)
    JOIN ship_crew_position_definition definition USING(crew_position_rule_id)
    WHERE action.space_combat_action_id=NEW.first_action_id;
    SELECT action.action_code,action.target_vessel_id,turn.senc_vessel_id,
           assignment.actor_id,definition.position_code
    INTO second_action
    FROM senc_action action JOIN senc_crew_turn turn USING(crew_turn_id)
    JOIN ship_crew_assignment assignment USING(crew_assignment_id)
    JOIN ship_crew_position position_state USING(ship_crew_position_id)
    JOIN ship_crew_position_definition definition USING(crew_position_rule_id)
    WHERE action.space_combat_action_id=NEW.second_action_id;
    SELECT actor_id,effect INTO first_task FROM cmd_actor_task_receipt WHERE command_id=NEW.first_task_command_id;
    SELECT actor_id,effect INTO second_task FROM cmd_actor_task_receipt WHERE command_id=NEW.second_task_command_id;
    IF first_action.action_code<>'range-check' OR second_action.action_code<>'range-check'
       OR first_action.senc_vessel_id<>NEW.first_vessel_id OR second_action.senc_vessel_id<>NEW.second_vessel_id
       OR first_action.target_vessel_id<>NEW.second_vessel_id OR second_action.target_vessel_id<>NEW.first_vessel_id
       OR first_action.position_code<>'navigator' OR second_action.position_code<>'navigator'
       OR first_task.actor_id<>first_action.actor_id OR second_task.actor_id<>second_action.actor_id
       OR first_task.effect<>NEW.first_effect OR second_task.effect<>NEW.second_effect THEN
        RAISE EXCEPTION 'Space combat Range Check participants or task receipts are inconsistent' USING ERRCODE='23514';
    END IF;
    expected_winner:=CASE
      WHEN NEW.first_effect>NEW.second_effect THEN NEW.first_vessel_id
      WHEN NEW.second_effect>NEW.first_effect THEN NEW.second_vessel_id
      WHEN NEW.first_characteristic_value>NEW.second_characteristic_value THEN NEW.first_vessel_id
      WHEN NEW.second_characteristic_value>NEW.first_characteristic_value THEN NEW.second_vessel_id
      ELSE NULL END;
    IF NEW.winning_vessel_id IS DISTINCT FROM expected_winner
       OR (expected_winner IS NULL)<>(NEW.resolution_status='reroll-required')
       OR NEW.range_band_before<>current_range.range_band_code
       OR NEW.range_version_before<>current_range.range_version THEN
        RAISE EXCEPTION 'Space combat Range Check outcome is inconsistent' USING ERRCODE='23514';
    END IF;
    SELECT display_order INTO before_order FROM rule_space_range_band WHERE range_band_code=NEW.range_band_before;
    after_order:=before_order+CASE NEW.elected_change WHEN 'increase' THEN 1 WHEN 'decrease' THEN -1 ELSE 0 END;
    IF expected_winner IS NULL THEN after_order:=before_order; END IF;
    IF NOT EXISTS(SELECT 1 FROM rule_space_range_band WHERE range_band_code=NEW.range_band_after AND display_order=after_order) THEN
        RAISE EXCEPTION 'Space combat Range Check band change is invalid' USING ERRCODE='23514';
    END IF;
    UPDATE senc_vessel_range SET range_band_code=NEW.range_band_after,
      range_version=NEW.range_version_after,updated_at=clock_timestamp()
    WHERE engagement_id=NEW.engagement_id AND first_vessel_id=NEW.first_vessel_id
      AND second_vessel_id=NEW.second_vessel_id;
    RETURN NEW;
END $$;
CREATE TRIGGER senc_range_check_valid BEFORE INSERT ON senc_range_check_receipt
FOR EACH ROW EXECUTE FUNCTION senc_validate_range_check_receipt();
CREATE FUNCTION senc_reject_range_check_receipt_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Space combat Range Check receipts are immutable'; END $$;
CREATE TRIGGER senc_range_check_immutable BEFORE UPDATE OR DELETE ON senc_range_check_receipt
FOR EACH ROW EXECUTE FUNCTION senc_reject_range_check_receipt_mutation();
