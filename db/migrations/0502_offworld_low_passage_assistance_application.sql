CREATE OR REPLACE FUNCTION journey_validate_low_passage_revival()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE passage journey_passage%ROWTYPE; task cmd_actor_task_receipt%ROWTYPE;
        rules rule_low_passage_revival%ROWTYPE; aid cmd_task_assistance_receipt%ROWTYPE;
        helper cmd_actor_task_receipt%ROWTYPE;
BEGIN
    SELECT * INTO STRICT passage FROM journey_passage
    WHERE journey_passage_id=NEW.journey_passage_id AND campaign_id=NEW.campaign_id FOR UPDATE;
    SELECT * INTO STRICT task FROM cmd_actor_task_receipt WHERE command_id=NEW.passenger_task_command_id;
    SELECT * INTO STRICT rules FROM rule_low_passage_revival;
    IF passage.actor_id<>NEW.passenger_actor_id OR passage.passage_class<>'low'
       OR passage.passage_status<>NEW.passage_status_before
       OR passage.concurrency_version<>NEW.passage_version_before
       OR task.actor_id<>NEW.passenger_actor_id OR task.characteristic_rule_id<>rules.passenger_characteristic_rule_id
       OR task.skill_rule_id IS NOT NULL OR task.difficulty_rule_id<>rules.passenger_difficulty_rule_id
       OR task.succeeded<>NEW.passenger_succeeded THEN
        RAISE EXCEPTION 'Low-passage revival does not match passage or Easy Endurance task' USING ERRCODE='23514';
    END IF;
    IF NEW.task_assistance_receipt_id IS NULL THEN
        IF NEW.assistance_modifier<>0 OR task.circumstance_modifier<>0 THEN
            RAISE EXCEPTION 'Unassisted revival has no assistance modifier' USING ERRCODE='23514';
        END IF;
    ELSE
        SELECT * INTO STRICT aid FROM cmd_task_assistance_receipt
        WHERE task_assistance_receipt_id=NEW.task_assistance_receipt_id;
        SELECT * INTO STRICT helper FROM cmd_actor_task_receipt WHERE command_id=aid.helper_task_command_id;
        IF aid.leader_task_command_id<>NEW.passenger_task_command_id
           OR aid.assistance_mode<>'source-prescribed-check'
           OR aid.assistance_context<>'low-passage-revival'
           OR aid.assistance_modifier<>NEW.assistance_modifier
           OR task.circumstance_modifier<>aid.assistance_modifier
           OR helper.characteristic_rule_id<>rules.medic_characteristic_rule_id
           OR helper.skill_rule_id<>rules.medic_skill_rule_id
           OR helper.difficulty_rule_id<>rules.medic_difficulty_rule_id THEN
            RAISE EXCEPTION 'Low-passage aid must be the applied published Routine Education Medicine check' USING ERRCODE='23514';
        END IF;
    END IF;
    UPDATE journey_passage SET passage_status=NEW.passage_status_after,
        concurrency_version=NEW.passage_version_after
    WHERE journey_passage_id=NEW.journey_passage_id;
    RETURN NEW;
END $$;
