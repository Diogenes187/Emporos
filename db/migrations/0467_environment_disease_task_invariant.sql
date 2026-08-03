CREATE OR REPLACE FUNCTION env_finalize_disease_check() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE disease_case env_disease_case%ROWTYPE;profile rule_disease_profile%ROWTYPE;task cmd_actor_task_receipt%ROWTYPE;
 characteristic actor_characteristic%ROWTYPE;average_difficulty_id bigint;expected_damage integer;expected_seconds bigint;unit_seconds bigint;
BEGIN
 SELECT * INTO STRICT disease_case FROM env_disease_case WHERE disease_case_id=NEW.disease_case_id FOR UPDATE;
 SELECT * INTO STRICT profile FROM rule_disease_profile WHERE disease_profile_id=disease_case.disease_profile_id;
 SELECT * INTO STRICT task FROM cmd_actor_task_receipt WHERE command_id=NEW.task_command_id;
 SELECT rule_id INTO STRICT average_difficulty_id FROM rule_rule WHERE rule_code='difficulty.average';
 SELECT * INTO STRICT characteristic FROM actor_characteristic WHERE actor_id=disease_case.actor_id AND characteristic_rule_id=profile.affected_characteristic_rule_id FOR UPDATE;
 IF disease_case.case_status<>'active' OR NEW.check_sequence<>(SELECT count(*)+1 FROM env_disease_check_receipt WHERE disease_case_id=disease_case.disease_case_id)
  OR NEW.case_version_before<>disease_case.concurrency_version OR task.actor_id<>disease_case.actor_id OR task.characteristic_rule_id<>profile.resistance_characteristic_rule_id
  OR task.skill_rule_id IS NOT NULL OR task.difficulty_rule_id<>average_difficulty_id OR task.circumstance_modifier<>profile.resistance_dm
  OR NEW.task_succeeded<>task.succeeded OR NEW.characteristic_value_before<>characteristic.current_value THEN
  RAISE EXCEPTION 'Disease check must match its active case, sequence, version, Average Endurance task, and listed resistance DM' USING ERRCODE='23514'; END IF;
 IF NEW.task_succeeded THEN
  IF NEW.rolled_damage<>0 OR NEW.characteristic_value_after<>characteristic.current_value THEN RAISE EXCEPTION 'Successful disease resistance must deal no damage' USING ERRCODE='23514'; END IF;
  UPDATE env_disease_case SET case_status='fought-off',next_check_at=NULL,resolved_at=clock_timestamp(),concurrency_version=NEW.case_version_after WHERE disease_case_id=disease_case.disease_case_id;
 ELSE
  expected_damage:=greatest(profile.damage_minimum,NEW.damage_die_result+profile.damage_flat_modifier);
  unit_seconds:=CASE profile.interval_unit WHEN 'hours' THEN 3600 WHEN 'days' THEN 86400 ELSE 604800 END;
  expected_seconds:=NEW.interval_die_total::bigint*unit_seconds;
  IF NEW.rolled_damage<>expected_damage OR NEW.interval_die_total<profile.interval_dice_count OR NEW.interval_die_total>profile.interval_dice_count*profile.interval_die_sides
   OR NEW.interval_seconds<>expected_seconds OR NEW.characteristic_value_after<>greatest(0,characteristic.current_value-expected_damage) THEN
   RAISE EXCEPTION 'Failed disease resistance must match published damage, interval dice, and characteristic reduction' USING ERRCODE='23514'; END IF;
  UPDATE actor_characteristic SET current_value=NEW.characteristic_value_after WHERE actor_id=disease_case.actor_id AND characteristic_rule_id=profile.affected_characteristic_rule_id;
  UPDATE env_disease_case SET next_check_at=clock_timestamp()+make_interval(secs=>expected_seconds),concurrency_version=NEW.case_version_after WHERE disease_case_id=disease_case.disease_case_id;
 END IF; RETURN NEW;
END $$;
