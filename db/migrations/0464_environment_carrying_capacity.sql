INSERT INTO src_locator(source_work_id,source_artifact_id,locator_type,heading_path,display_citation)
SELECT artifact.source_work_id,artifact.source_artifact_id,'heading',source.heading_path,
 CASE work.work_code WHEN 'cepheus-engine.ogn' THEN 'Cepheus Engine SRD, Environments and Hazards: '||source.label
 ELSE 'Cepheus Engine v9.1, Environments and Hazards: '||source.label END
FROM src_artifact artifact JOIN src_work work USING(source_work_id)
CROSS JOIN (VALUES('Environments and Hazards > Carrying Capacity','Carrying Capacity'),
 ('Environments and Hazards > Carrying Capacity > Gravity and Carrying Capacity','Gravity and Carrying Capacity')) source(heading_path,label)
WHERE artifact.source_uri IN('src/book3/environments-and-hazards.md',
 'https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-environments-and-hazards/') ON CONFLICT DO NOTHING;
WITH package AS(SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine')
INSERT INTO rule_rule(content_package_id,rule_code,name,rule_category,rule_status,description)
SELECT content_package_id,'environment.carrying-capacity','Carrying Capacity','other','approved',
 'Strength-based load bands, physical penalties, movement, pushing and dragging, and gravity scaling.' FROM package;

CREATE TABLE rule_carrying_load_band (
 rule_id bigint NOT NULL REFERENCES rule_rule(rule_id),load_band_code text NOT NULL,
 display_order smallint NOT NULL UNIQUE CHECK(display_order BETWEEN 1 AND 4),strength_multiplier smallint NOT NULL CHECK(strength_multiplier IN(2,4,6,12)),
 physical_check_dm smallint CHECK(physical_check_dm IN(-2,-1,0)),movement_percent smallint CHECK(movement_percent IN(75,100)),
 fixed_movement_millimeters integer CHECK(fixed_movement_millimeters=1500),may_carry boolean NOT NULL,may_lift_overhead boolean NOT NULL,
 may_lift_off_ground boolean NOT NULL,other_actions_allowed boolean NOT NULL,
 PRIMARY KEY(rule_id,load_band_code),UNIQUE(rule_id,strength_multiplier),
 CHECK(num_nonnulls(movement_percent,fixed_movement_millimeters)=1),
 CHECK((load_band_code='maximum')=(fixed_movement_millimeters IS NOT NULL))
);
INSERT INTO rule_carrying_load_band SELECT rule_id,band,ordering,multiplier,dm,move_percent,fixed_move,carry,overhead,off_ground,actions
FROM rule_rule CROSS JOIN (VALUES
 ('light',1,2,0,100,NULL::integer,true,true,true,true),
 ('medium',2,4,-1,75,NULL,true,true,true,true),
 ('heavy',3,6,-2,75,NULL,true,true,true,true),
 ('maximum',4,12,NULL::smallint,NULL::smallint,1500,false,false,true,false)
) profile(band,ordering,multiplier,dm,move_percent,fixed_move,carry,overhead,off_ground,actions)
WHERE rule_code='environment.carrying-capacity';
CREATE TABLE rule_push_drag_capacity (
 rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),heavy_load_multiplier smallint NOT NULL CHECK(heavy_load_multiplier=5),
 strength_multiplier smallint NOT NULL CHECK(strength_multiplier=30),movement_percent smallint NOT NULL CHECK(movement_percent=50),
 favorable_capacity_multiplier numeric(3,1) NOT NULL CHECK(favorable_capacity_multiplier=2.0),
 adverse_default_multiplier numeric(3,1) NOT NULL CHECK(adverse_default_multiplier=0.5),
 adverse_conditions_may_reduce_further boolean NOT NULL CHECK(adverse_conditions_may_reduce_further)
);
INSERT INTO rule_push_drag_capacity SELECT rule_id,5,30,50,2.0,0.5,true FROM rule_rule WHERE rule_code='environment.carrying-capacity';
CREATE TABLE rule_gravity_carrying_capacity (
 rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),standard_gravity numeric(4,3) NOT NULL CHECK(standard_gravity=1.0),
 adjustment_operation text NOT NULL CHECK(adjustment_operation='divide-standard-load-by-gravity'),gravity_must_be_positive boolean NOT NULL CHECK(gravity_must_be_positive)
);
INSERT INTO rule_gravity_carrying_capacity SELECT rule_id,1.0,'divide-standard-load-by-gravity',true FROM rule_rule WHERE rule_code='environment.carrying-capacity';
INSERT INTO src_record_provenance(rule_id,content_package_id,source_locator_id,provenance_class,is_primary_citation)
SELECT rule.rule_id,rule.content_package_id,locator.source_locator_id,CASE work.work_code WHEN 'cepheus-engine.ogn' THEN 'direct' ELSE 'corroborating' END,
 work.work_code='cepheus-engine.ogn' FROM rule_rule rule CROSS JOIN src_locator locator JOIN src_work work USING(source_work_id)
WHERE rule.rule_code='environment.carrying-capacity' AND locator.heading_path LIKE 'Environments and Hazards > Carrying Capacity%'
 AND work.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1');

INSERT INTO src_issue(issue_code,domain_code,issue_type,review_priority,issue_status,subject_code,title,problem_statement,
 published_value,calculated_value,difference_value,value_unit,reviewer_question,requested_evidence,engine_disposition,resolved_at,resolution_summary)
VALUES('environment.carrying.maximum-load-example','environment','arithmetic_conflict','low','resolved','maximum-load',
 'Strength 7 maximum-load example arithmetic','Both paired publications state a twelve-times-Strength rule but print 94 kg for Strength 7.',
 '94 kg','84 kg',10,'kg','Should the explicit multiplier or the inconsistent worked example govern?',
 'Publisher errata or a corrected printing.','preserve_rule',clock_timestamp(),
 'The explicit general formula governs: 7 multiplied by 12 is 84 kg. The printed 94 kg remains recorded as source arithmetic error.');
INSERT INTO src_issue_locator(source_issue_id,source_locator_id,evidence_role)
SELECT issue.source_issue_id,locator.source_locator_id,CASE work.work_code WHEN 'cepheus-engine.ogn' THEN 'primary' ELSE 'corroborating' END
FROM src_issue issue CROSS JOIN src_locator locator JOIN src_work work USING(source_work_id)
WHERE issue.issue_code='environment.carrying.maximum-load-example'
 AND locator.heading_path='Environments and Hazards > Carrying Capacity'
 AND work.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1');
INSERT INTO rule_interpretation(rule_id,interpretation_type,decision_register_entry,rationale)
SELECT rule_id,'agreed_interpretation','CE-ENV-001',
 'Use the published twelve-times-Strength formula; the Strength 7 example result of 94 kg is arithmetically impossible and is retained in the resolved source issue.'
FROM rule_rule WHERE rule_code='environment.carrying-capacity';

CREATE TABLE actor_encumbrance_state (
 actor_id bigint PRIMARY KEY,campaign_id bigint NOT NULL,carried_mass_grams bigint NOT NULL CHECK(carried_mass_grams>=0),
 gravity_milligee integer NOT NULL CHECK(gravity_milligee>0),load_band_code text NOT NULL CHECK(load_band_code IN('light','medium','heavy','maximum','beyond-maximum')),
 physical_check_dm smallint,movement_percent smallint,fixed_movement_millimeters integer,other_actions_allowed boolean NOT NULL,
 concurrency_version bigint NOT NULL CHECK(concurrency_version>0),updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id),
 CHECK(num_nonnulls(movement_percent,fixed_movement_millimeters)<=1),
 CHECK((load_band_code='beyond-maximum')=(num_nonnulls(movement_percent,fixed_movement_millimeters)=0))
);
CREATE TABLE actor_encumbrance_receipt (
 actor_encumbrance_receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,actor_id bigint NOT NULL,campaign_id bigint NOT NULL,
 state_version_before bigint NOT NULL CHECK(state_version_before>=0),state_version_after bigint NOT NULL CHECK(state_version_after=state_version_before+1),
 strength_snapshot smallint NOT NULL CHECK(strength_snapshot>=0),carried_mass_grams bigint NOT NULL CHECK(carried_mass_grams>=0),
 gravity_milligee integer NOT NULL CHECK(gravity_milligee>0),light_limit_grams bigint NOT NULL,medium_limit_grams bigint NOT NULL,
 heavy_limit_grams bigint NOT NULL,maximum_limit_grams bigint NOT NULL,load_band_code text NOT NULL,
 physical_check_dm smallint,movement_percent smallint,fixed_movement_millimeters integer,other_actions_allowed boolean NOT NULL,
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),UNIQUE(actor_id,state_version_after),
 FOREIGN KEY(actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id),
 CHECK(light_limit_grams<=medium_limit_grams AND medium_limit_grams<=heavy_limit_grams AND heavy_limit_grams<=maximum_limit_grams)
);
CREATE FUNCTION actor_validate_encumbrance_receipt() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE strength_value smallint;current_state actor_encumbrance_state%ROWTYPE;expected_band text;band rule_carrying_load_band%ROWTYPE;
BEGIN SELECT characteristic.current_value INTO STRICT strength_value FROM actor_characteristic characteristic
 JOIN rule_rule rule ON rule.rule_id=characteristic.characteristic_rule_id
 WHERE characteristic.actor_id=NEW.actor_id AND rule.rule_code='characteristic.strength';
 SELECT * INTO current_state FROM actor_encumbrance_state WHERE actor_id=NEW.actor_id FOR UPDATE;
 IF NEW.strength_snapshot<>strength_value OR NEW.state_version_before<>coalesce(current_state.concurrency_version,0)
  OR NEW.light_limit_grams<>(strength_value::bigint*2*1000000/NEW.gravity_milligee)
  OR NEW.medium_limit_grams<>(strength_value::bigint*4*1000000/NEW.gravity_milligee)
  OR NEW.heavy_limit_grams<>(strength_value::bigint*6*1000000/NEW.gravity_milligee)
  OR NEW.maximum_limit_grams<>(strength_value::bigint*12*1000000/NEW.gravity_milligee) THEN
  RAISE EXCEPTION 'Encumbrance receipt must match current Strength, gravity-adjusted limits, and state version' USING ERRCODE='23514'; END IF;
 expected_band:=CASE WHEN NEW.carried_mass_grams<=NEW.light_limit_grams THEN 'light' WHEN NEW.carried_mass_grams<=NEW.medium_limit_grams THEN 'medium'
  WHEN NEW.carried_mass_grams<=NEW.heavy_limit_grams THEN 'heavy' WHEN NEW.carried_mass_grams<=NEW.maximum_limit_grams THEN 'maximum' ELSE 'beyond-maximum' END;
 SELECT profile.* INTO band FROM rule_carrying_load_band profile JOIN rule_rule rule ON rule.rule_id=profile.rule_id
 WHERE rule.rule_code='environment.carrying-capacity' AND profile.load_band_code=expected_band;
 IF NEW.load_band_code<>expected_band OR NEW.physical_check_dm IS DISTINCT FROM band.physical_check_dm
  OR NEW.movement_percent IS DISTINCT FROM band.movement_percent OR NEW.fixed_movement_millimeters IS DISTINCT FROM band.fixed_movement_millimeters
  OR NEW.other_actions_allowed<>coalesce(band.other_actions_allowed,false) THEN
  RAISE EXCEPTION 'Encumbrance receipt must match its derived published load-band effects' USING ERRCODE='23514'; END IF;
 INSERT INTO actor_encumbrance_state(actor_id,campaign_id,carried_mass_grams,gravity_milligee,load_band_code,physical_check_dm,
  movement_percent,fixed_movement_millimeters,other_actions_allowed,concurrency_version)
 VALUES(NEW.actor_id,NEW.campaign_id,NEW.carried_mass_grams,NEW.gravity_milligee,NEW.load_band_code,NEW.physical_check_dm,
  NEW.movement_percent,NEW.fixed_movement_millimeters,NEW.other_actions_allowed,NEW.state_version_after)
 ON CONFLICT(actor_id) DO UPDATE SET carried_mass_grams=EXCLUDED.carried_mass_grams,gravity_milligee=EXCLUDED.gravity_milligee,
  load_band_code=EXCLUDED.load_band_code,physical_check_dm=EXCLUDED.physical_check_dm,movement_percent=EXCLUDED.movement_percent,
  fixed_movement_millimeters=EXCLUDED.fixed_movement_millimeters,other_actions_allowed=EXCLUDED.other_actions_allowed,
  concurrency_version=EXCLUDED.concurrency_version,updated_at=clock_timestamp(); RETURN NEW; END $$;
CREATE TRIGGER actor_encumbrance_receipt_valid BEFORE INSERT ON actor_encumbrance_receipt FOR EACH ROW EXECUTE FUNCTION actor_validate_encumbrance_receipt();
CREATE FUNCTION actor_reject_encumbrance_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Encumbrance receipts are immutable'; END $$;
CREATE TRIGGER actor_encumbrance_receipt_immutable BEFORE UPDATE OR DELETE ON actor_encumbrance_receipt FOR EACH ROW EXECUTE FUNCTION actor_reject_encumbrance_mutation();
CREATE FUNCTION actor_guard_encumbrance_state() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
 IF pg_trigger_depth()=0 THEN RAISE EXCEPTION 'Encumbrance state changes require an immutable receipt' USING ERRCODE='23514'; END IF; RETURN NEW; END $$;
CREATE TRIGGER actor_encumbrance_state_guard BEFORE INSERT OR UPDATE OR DELETE ON actor_encumbrance_state FOR EACH ROW EXECUTE FUNCTION actor_guard_encumbrance_state();
