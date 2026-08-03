INSERT INTO src_locator(source_work_id,source_artifact_id,locator_type,heading_path,display_citation)
SELECT artifact.source_work_id,artifact.source_artifact_id,'heading','Environments and Hazards > Diseases',
 CASE work.work_code WHEN 'cepheus-engine.ogn' THEN 'Cepheus Engine SRD, Environments and Hazards: Diseases'
 ELSE 'Cepheus Engine v9.1, Environments and Hazards: Diseases' END
FROM src_artifact artifact JOIN src_work work USING(source_work_id)
WHERE artifact.source_uri IN('src/book3/environments-and-hazards.md',
 'https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-environments-and-hazards/') ON CONFLICT DO NOTHING;

WITH package AS(SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine')
INSERT INTO rule_rule(content_package_id,rule_code,name,rule_category,rule_status,description)
SELECT content_package_id,'environment.diseases','Diseases','other','approved',
 'Endurance resistance checks repeat after rolled intervals on failure; damage reduces the disease profile characteristic and one success ends the disease.' FROM package;

CREATE TABLE rule_disease_profile(
 disease_profile_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 rule_id bigint NOT NULL REFERENCES rule_rule(rule_id),disease_code text NOT NULL UNIQUE,name text NOT NULL,
 resistance_characteristic_rule_id bigint NOT NULL REFERENCES rule_characteristic(rule_id),resistance_dm smallint NOT NULL,
 affected_characteristic_rule_id bigint NOT NULL REFERENCES rule_characteristic(rule_id),damage_dice_count smallint NOT NULL CHECK(damage_dice_count=1),
 damage_die_sides smallint NOT NULL CHECK(damage_die_sides=6),damage_flat_modifier smallint NOT NULL,
 damage_minimum smallint NOT NULL DEFAULT 0 CHECK(damage_minimum=0),interval_dice_count smallint NOT NULL CHECK(interval_dice_count IN(1,2)),
 interval_die_sides smallint NOT NULL CHECK(interval_die_sides=6),interval_unit text NOT NULL CHECK(interval_unit IN('hours','days','weeks')),
 UNIQUE(rule_id,disease_code)
);
INSERT INTO rule_disease_profile(rule_id,disease_code,name,resistance_characteristic_rule_id,resistance_dm,affected_characteristic_rule_id,
 damage_dice_count,damage_die_sides,damage_flat_modifier,interval_dice_count,interval_die_sides,interval_unit)
SELECT disease.rule_id,value.code,value.name,endurance.rule_id,value.dm,endurance.rule_id,1,6,value.damage_modifier,value.interval_dice,6,value.interval_unit
FROM rule_rule disease CROSS JOIN rule_rule endurance CROSS JOIN (VALUES
 ('pneumonia','Pneumonia',0,4,1,'weeks'),('anthrax','Anthrax',-3,2,1,'days'),
 ('regina-flu','Regina Flu',1,-2,1,'days'),('biological-weapon','Biological Weapon',-6,8,1,'hours')
) value(code,name,dm,damage_modifier,interval_dice,interval_unit)
WHERE disease.rule_code='environment.diseases' AND endurance.rule_code='characteristic.endurance';

INSERT INTO src_record_provenance(rule_id,content_package_id,source_locator_id,provenance_class,is_primary_citation)
SELECT rule.rule_id,rule.content_package_id,locator.source_locator_id,
 CASE work.work_code WHEN 'cepheus-engine.ogn' THEN 'direct' ELSE 'corroborating' END,work.work_code='cepheus-engine.ogn'
FROM rule_rule rule CROSS JOIN src_locator locator JOIN src_work work USING(source_work_id)
WHERE rule.rule_code='environment.diseases' AND locator.heading_path='Environments and Hazards > Diseases'
 AND work.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1');

CREATE TABLE env_disease_case(
 disease_case_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
 actor_id bigint NOT NULL,campaign_id bigint NOT NULL,disease_profile_id bigint NOT NULL REFERENCES rule_disease_profile(disease_profile_id),
 case_status text NOT NULL DEFAULT 'active' CHECK(case_status IN('active','fought-off')),next_check_at timestamptz,
 concurrency_version bigint NOT NULL DEFAULT 1 CHECK(concurrency_version>0),contracted_at timestamptz NOT NULL DEFAULT clock_timestamp(),resolved_at timestamptz,
 FOREIGN KEY(actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id),
 CHECK((case_status='active')=(resolved_at IS NULL)),CHECK(case_status='active' OR next_check_at IS NULL)
);
CREATE UNIQUE INDEX env_one_active_disease_case ON env_disease_case(actor_id,disease_profile_id) WHERE case_status='active';

CREATE TABLE env_disease_check_receipt(
 disease_check_receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,disease_case_id bigint NOT NULL REFERENCES env_disease_case(disease_case_id),
 check_sequence integer NOT NULL CHECK(check_sequence>0),task_command_id bigint NOT NULL UNIQUE REFERENCES cmd_actor_task_receipt(command_id),
 task_succeeded boolean NOT NULL,damage_die_result smallint CHECK(damage_die_result BETWEEN 1 AND 6),rolled_damage smallint NOT NULL CHECK(rolled_damage>=0),
 interval_die_total smallint,interval_seconds bigint,characteristic_value_before smallint NOT NULL CHECK(characteristic_value_before>=0),
 characteristic_value_after smallint NOT NULL CHECK(characteristic_value_after>=0),case_version_before bigint NOT NULL,case_version_after bigint NOT NULL,
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),UNIQUE(disease_case_id,check_sequence),
 CHECK(case_version_after=case_version_before+1),
 CHECK((task_succeeded AND damage_die_result IS NULL AND rolled_damage=0 AND interval_die_total IS NULL AND interval_seconds IS NULL
  AND characteristic_value_after=characteristic_value_before)
 OR (NOT task_succeeded AND damage_die_result IS NOT NULL AND interval_die_total IS NOT NULL AND interval_seconds IS NOT NULL
  AND characteristic_value_after<=characteristic_value_before))
);

CREATE FUNCTION env_finalize_disease_check() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE disease_case env_disease_case%ROWTYPE;profile rule_disease_profile%ROWTYPE;task cmd_actor_task_receipt%ROWTYPE;
 characteristic actor_characteristic%ROWTYPE;expected_damage integer;expected_seconds bigint;unit_seconds bigint;
BEGIN
 SELECT * INTO STRICT disease_case FROM env_disease_case WHERE disease_case_id=NEW.disease_case_id FOR UPDATE;
 SELECT * INTO STRICT profile FROM rule_disease_profile WHERE disease_profile_id=disease_case.disease_profile_id;
 SELECT * INTO STRICT task FROM cmd_actor_task_receipt WHERE command_id=NEW.task_command_id;
 SELECT * INTO STRICT characteristic FROM actor_characteristic WHERE actor_id=disease_case.actor_id AND characteristic_rule_id=profile.affected_characteristic_rule_id FOR UPDATE;
 IF disease_case.case_status<>'active' OR NEW.check_sequence<>(SELECT count(*)+1 FROM env_disease_check_receipt WHERE disease_case_id=disease_case.disease_case_id)
  OR NEW.case_version_before<>disease_case.concurrency_version OR task.actor_id<>disease_case.actor_id OR task.characteristic_rule_id<>profile.resistance_characteristic_rule_id
  OR task.skill_rule_id IS NOT NULL OR task.difficulty_rule_id IS NOT NULL OR task.circumstance_modifier<>profile.resistance_dm
  OR NEW.task_succeeded<>task.succeeded OR NEW.characteristic_value_before<>characteristic.current_value THEN
  RAISE EXCEPTION 'Disease check must match its active case, sequence, version, characteristic, and listed resistance DM' USING ERRCODE='23514'; END IF;
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
CREATE TRIGGER env_disease_check_final BEFORE INSERT ON env_disease_check_receipt FOR EACH ROW EXECUTE FUNCTION env_finalize_disease_check();

CREATE FUNCTION env_reject_disease_receipt_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Disease check receipts are immutable'; END $$;
CREATE TRIGGER env_disease_check_immutable BEFORE UPDATE OR DELETE ON env_disease_check_receipt FOR EACH ROW EXECUTE FUNCTION env_reject_disease_receipt_mutation();
CREATE FUNCTION env_guard_disease_case() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
 IF pg_trigger_depth()<2 THEN RAISE EXCEPTION 'Disease case changes require an immutable check receipt' USING ERRCODE='23514'; END IF; RETURN NEW; END $$;
CREATE TRIGGER env_disease_case_guard BEFORE UPDATE OR DELETE ON env_disease_case FOR EACH ROW EXECUTE FUNCTION env_guard_disease_case();
