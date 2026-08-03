INSERT INTO src_locator(source_work_id,source_artifact_id,locator_type,heading_path,display_citation)
SELECT artifact.source_work_id,artifact.source_artifact_id,'heading',
       'Space Combat > Significant Actions > Increase Initiative',
       CASE work.work_code WHEN 'cepheus-engine.ogn'
         THEN 'Cepheus Engine SRD, Space Combat: Increase Initiative'
         ELSE 'Cepheus Engine v9.1, Space Combat: Increase Initiative' END
FROM src_artifact artifact JOIN src_work work USING(source_work_id)
WHERE (work.work_code='cepheus-engine.ogn' AND artifact.source_uri LIKE '%cepheus-engine-space-combat/')
   OR (work.work_code='cepheus-engine.github-v9.1' AND artifact.source_uri='src/book2/space-combat.md')
ON CONFLICT DO NOTHING;

WITH package AS (SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine')
INSERT INTO rule_rule(content_package_id,rule_code,name,rule_category,rule_status,description)
SELECT content_package_id,'combat.space.increase-initiative','Increase Space Combat Initiative',
       'combat','approved','Captain Leadership action granting a positive Effect bonus for the following turn only.'
FROM package;

CREATE TABLE rule_space_combat_increase_initiative(
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    skill_rule_id bigint NOT NULL REFERENCES rule_skill(rule_id),
    difficulty_rule_id bigint NOT NULL REFERENCES rule_difficulty(rule_id),
    applies_following_round_only boolean NOT NULL,
    consumes_significant_action_on_failure boolean NOT NULL,
    minimum_initiative_modifier smallint NOT NULL CHECK(minimum_initiative_modifier=0),
    uses_positive_effect boolean NOT NULL
);
INSERT INTO rule_space_combat_increase_initiative
SELECT action.rule_id,skill.rule_id,difficulty.rule_id,true,true,0,true
FROM rule_rule action CROSS JOIN rule_rule skill CROSS JOIN rule_rule difficulty
WHERE action.rule_code='combat.space.increase-initiative'
  AND skill.rule_code='skill.leadership'
  AND difficulty.rule_code='difficulty.average';

INSERT INTO rule_interpretation(rule_id,interpretation_type,decision_register_entry,rationale)
SELECT rule_id,'agreed_interpretation','CE-SC-002',
       'A failed or zero-Effect Leadership check spends the action but cannot reduce Initiative; only positive Effect applies to the following turn.'
FROM rule_rule WHERE rule_code='combat.space.increase-initiative';

INSERT INTO src_record_provenance(rule_id,content_package_id,source_locator_id,provenance_class,is_primary_citation)
SELECT rule.rule_id,rule.content_package_id,locator.source_locator_id,
       CASE work.work_code WHEN 'cepheus-engine.ogn' THEN 'direct' ELSE 'corroborating' END,
       work.work_code='cepheus-engine.ogn'
FROM rule_rule rule CROSS JOIN src_locator locator JOIN src_work work USING(source_work_id)
WHERE rule.rule_code='combat.space.increase-initiative'
  AND locator.heading_path='Space Combat > Significant Actions > Increase Initiative'
  AND work.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1');

CREATE TABLE senc_increase_initiative_receipt(
    increase_initiative_receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    engagement_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    senc_vessel_id bigint NOT NULL,
    source_round_id bigint NOT NULL,
    source_round_number integer NOT NULL CHECK(source_round_number>0),
    applies_round_number integer NOT NULL CHECK(applies_round_number>1),
    action_id bigint NOT NULL UNIQUE,
    captain_assignment_id bigint NOT NULL,
    captain_ship_id bigint NOT NULL,
    task_command_id bigint NOT NULL UNIQUE REFERENCES cmd_actor_task_receipt(command_id),
    task_effect smallint NOT NULL,
    initiative_bonus smallint NOT NULL CHECK(initiative_bonus>=0),
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    FOREIGN KEY(senc_vessel_id,engagement_id,campaign_id)
      REFERENCES senc_vessel(senc_vessel_id,engagement_id,campaign_id),
    FOREIGN KEY(source_round_id,engagement_id,campaign_id)
      REFERENCES senc_round(space_combat_round_id,engagement_id,campaign_id),
    FOREIGN KEY(action_id,engagement_id,campaign_id)
      REFERENCES senc_action(space_combat_action_id,engagement_id,campaign_id),
    FOREIGN KEY(captain_assignment_id,captain_ship_id,campaign_id)
      REFERENCES ship_crew_assignment(crew_assignment_id,ship_id,campaign_id),
    UNIQUE(engagement_id,senc_vessel_id,source_round_number),
    CHECK(applies_round_number=source_round_number+1),
    CHECK(initiative_bonus=greatest(task_effect,0))
);

CREATE FUNCTION senc_validate_increase_initiative_receipt()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    action_row record; task_row record; round_number integer;
    leadership bigint; average bigint;
BEGIN
    SELECT action.action_code,turn.senc_vessel_id,turn.crew_assignment_id,
           assignment.ship_id,assignment.actor_id,assignment.duty_status,
           definition.position_code,action.space_combat_round_id
    INTO action_row
    FROM senc_action action JOIN senc_crew_turn turn USING(crew_turn_id)
    JOIN ship_crew_assignment assignment USING(crew_assignment_id)
    JOIN ship_crew_position position_state USING(ship_crew_position_id)
    JOIN ship_crew_position_definition definition USING(crew_position_rule_id)
    WHERE action.space_combat_action_id=NEW.action_id;
    SELECT actor_id,skill_rule_id,difficulty_rule_id,effect INTO task_row
    FROM cmd_actor_task_receipt WHERE command_id=NEW.task_command_id;
    SELECT rule_id INTO STRICT leadership FROM rule_rule WHERE rule_code='skill.leadership';
    SELECT rule_id INTO STRICT average FROM rule_rule WHERE rule_code='difficulty.average';
    SELECT r.round_number INTO round_number FROM senc_round r
    WHERE r.space_combat_round_id=NEW.source_round_id;
    IF action_row.action_code<>'increase-initiative'
       OR action_row.senc_vessel_id<>NEW.senc_vessel_id
       OR action_row.crew_assignment_id<>NEW.captain_assignment_id
       OR action_row.ship_id<>NEW.captain_ship_id
       OR action_row.duty_status<>'active' OR action_row.position_code<>'master'
       OR action_row.space_combat_round_id<>NEW.source_round_id
       OR task_row.actor_id<>action_row.actor_id
       OR task_row.skill_rule_id<>leadership OR task_row.difficulty_rule_id<>average
       OR task_row.effect<>NEW.task_effect
       OR round_number<>NEW.source_round_number THEN
        RAISE EXCEPTION 'Increase Initiative receipt does not match its Captain action and Leadership check'
          USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER senc_increase_initiative_valid BEFORE INSERT ON senc_increase_initiative_receipt
FOR EACH ROW EXECUTE FUNCTION senc_validate_increase_initiative_receipt();
CREATE FUNCTION senc_reject_increase_initiative_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Increase Initiative receipts are immutable'; END $$;
CREATE TRIGGER senc_increase_initiative_immutable BEFORE UPDATE OR DELETE ON senc_increase_initiative_receipt
FOR EACH ROW EXECUTE FUNCTION senc_reject_increase_initiative_mutation();

CREATE OR REPLACE FUNCTION senc_open_next_round(p_engagement_id bigint)
RETURNS bigint LANGUAGE plpgsql AS $$
DECLARE engagement senc_engagement%ROWTYPE; next_round integer; new_round_id bigint;
BEGIN
    SELECT * INTO STRICT engagement FROM senc_engagement
    WHERE engagement_id=p_engagement_id FOR UPDATE;
    IF engagement.engagement_status<>'active' THEN
        RAISE EXCEPTION 'Space combat round requires an active engagement' USING ERRCODE='23514';
    END IF;
    IF EXISTS(SELECT 1 FROM senc_round WHERE engagement_id=p_engagement_id
              AND round_status IN('open','resolving_damage')) THEN
        RAISE EXCEPTION 'Space combat engagement already has an unfinished round' USING ERRCODE='23514';
    END IF;
    IF EXISTS(SELECT 1 FROM senc_vessel WHERE engagement_id=p_engagement_id
              AND vessel_status='engaged' AND initiative_current IS NULL) THEN
        RAISE EXCEPTION 'Every engaged vessel requires initiative before opening a round' USING ERRCODE='23514';
    END IF;
    IF NOT EXISTS(SELECT 1 FROM senc_vessel WHERE engagement_id=p_engagement_id
                  AND vessel_status='engaged') THEN
        RAISE EXCEPTION 'Space combat round requires an engaged vessel' USING ERRCODE='23514';
    END IF;
    next_round:=coalesce(engagement.current_round,0)+1;
    INSERT INTO senc_round(engagement_id,campaign_id,round_number)
    VALUES(engagement.engagement_id,engagement.campaign_id,next_round)
    RETURNING space_combat_round_id INTO new_round_id;
    WITH effective AS (
      SELECT v.*,
             v.initiative_current+coalesce((
               SELECT bonus.initiative_bonus FROM senc_increase_initiative_receipt bonus
               WHERE bonus.engagement_id=v.engagement_id
                 AND bonus.senc_vessel_id=v.senc_vessel_id
                 AND bonus.applies_round_number=next_round
             ),0) AS effective_initiative
      FROM senc_vessel v WHERE v.engagement_id=p_engagement_id AND v.vessel_status='engaged'
    )
    INSERT INTO senc_vessel_turn_order_receipt(
      space_combat_round_id,engagement_id,campaign_id,senc_vessel_id,
      initiative_snapshot,thrust_snapshot,turn_order_rank,simultaneous_group_size)
    SELECT new_round_id,v.engagement_id,v.campaign_id,v.senc_vessel_id,
      v.effective_initiative,v.thrust_current,
      dense_rank() OVER(ORDER BY v.effective_initiative DESC,v.thrust_current DESC)::smallint,
      count(*) OVER(PARTITION BY v.effective_initiative,v.thrust_current)::smallint
    FROM effective v;
    UPDATE senc_engagement SET current_round=next_round WHERE engagement_id=p_engagement_id;
    RETURN new_round_id;
END $$;
