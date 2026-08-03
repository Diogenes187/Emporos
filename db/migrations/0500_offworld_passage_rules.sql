INSERT INTO src_locator(
    source_work_id,source_artifact_id,locator_type,heading_path,display_citation
)
SELECT DISTINCT ON(work.work_code,source.heading_path)
       artifact.source_work_id,artifact.source_artifact_id,'heading',source.heading_path,
       CASE work.work_code WHEN 'cepheus-engine.ogn'
         THEN 'Cepheus Engine SRD, Off-World Travel: '||source.label
         ELSE 'Cepheus Engine v9.1, Off-World Travel: '||source.label END
FROM src_artifact artifact JOIN src_work work USING(source_work_id)
CROSS JOIN(VALUES
    ('Off-World Travel > Ship''s Passage','Ship''s Passage'),
    ('Off-World Travel > Ship''s Passage > High Passage','High Passage'),
    ('Off-World Travel > Ship''s Passage > Middle Passage','Middle Passage'),
    ('Off-World Travel > Ship''s Passage > Low Passage','Low Passage'),
    ('Off-World Travel > Ship''s Passage > Working Passage','Working Passage'),
    ('Off-World Travel > Ship''s Passage > Stowaway','Stowaway')
) source(heading_path,label)
WHERE artifact.source_uri IN(
    'src/book2/off-world-travel.md',
    'https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-off-world-travel/'
)
ORDER BY work.work_code,source.heading_path,artifact.source_artifact_id
ON CONFLICT DO NOTHING;

WITH package AS(
    SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine'
)
INSERT INTO rule_rule(content_package_id,rule_code,name,rule_category,rule_status,description)
SELECT content_package_id,'travel.ship-passage-operations','Ship Passage Operations',
       'travel','approved','Passage fares, accommodations, steward limits, working passage, and low-berth revival.'
FROM package;

CREATE TABLE rule_passage_operation(
    passage_class text PRIMARY KEY REFERENCES rule_passage_class(passage_class),
    accommodation_kind text NOT NULL CHECK(accommodation_kind IN('stateroom','low-berth','crew-accommodation','hidden')),
    single_fare_credits integer CHECK(single_fare_credits>=0),
    double_occupancy_total_credits integer CHECK(double_occupancy_total_credits>0),
    double_occupancy_per_passenger_credits integer CHECK(double_occupancy_per_passenger_credits>0),
    baggage_allowance_kg integer,
    steward_passengers_per_level_quantum smallint,
    standby_only boolean NOT NULL DEFAULT false,
    bumpable_by_high_passage boolean NOT NULL DEFAULT false,
    maximum_working_jumps smallint,
    requires_position_expertise boolean NOT NULL DEFAULT false,
    low_revival_required boolean NOT NULL DEFAULT false,
    CHECK((double_occupancy_total_credits IS NULL)=(double_occupancy_per_passenger_credits IS NULL)),
    CHECK(double_occupancy_total_credits IS NULL OR double_occupancy_total_credits=2*double_occupancy_per_passenger_credits),
    CHECK(steward_passengers_per_level_quantum IS NULL OR steward_passengers_per_level_quantum>0),
    CHECK(maximum_working_jumps IS NULL OR maximum_working_jumps>0)
);

INSERT INTO rule_passage_operation VALUES
    ('high','stateroom',10000,16000,8000,1000,2,false,false,NULL,false,false),
    ('middle','stateroom',8000,13000,6500,100,5,true,true,NULL,false,false),
    ('low','low-berth',1000,NULL,NULL,10,NULL,false,false,NULL,false,true),
    ('working','crew-accommodation',NULL,NULL,NULL,1000,NULL,false,false,3,true,false),
    ('stowaway','hidden',0,NULL,NULL,NULL,NULL,false,false,NULL,false,false);

CREATE TABLE rule_low_passage_revival(
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    passenger_characteristic_rule_id bigint NOT NULL REFERENCES rule_characteristic(rule_id),
    passenger_difficulty_rule_id bigint NOT NULL REFERENCES rule_difficulty(rule_id),
    failure_causes_death boolean NOT NULL CHECK(failure_causes_death),
    medic_characteristic_rule_id bigint NOT NULL REFERENCES rule_characteristic(rule_id),
    medic_skill_rule_id bigint NOT NULL REFERENCES rule_skill(rule_id),
    medic_difficulty_rule_id bigint NOT NULL REFERENCES rule_difficulty(rule_id),
    medic_uses_aiding_another boolean NOT NULL CHECK(medic_uses_aiding_another)
);

INSERT INTO rule_low_passage_revival
SELECT operation.rule_id,endurance.rule_id,easy.rule_id,true,
       education.rule_id,medicine.rule_id,routine.rule_id,true
FROM rule_rule operation
JOIN rule_rule endurance ON endurance.rule_code='characteristic.endurance'
JOIN rule_rule easy ON easy.rule_code='difficulty.easy'
JOIN rule_rule education ON education.rule_code='characteristic.education'
JOIN rule_rule medicine ON medicine.rule_code='skill.medicine'
JOIN rule_rule routine ON routine.rule_code='difficulty.routine'
WHERE operation.rule_code='travel.ship-passage-operations';

INSERT INTO src_record_provenance(
    rule_id,content_package_id,source_locator_id,provenance_class,is_primary_citation
)
SELECT rule.rule_id,rule.content_package_id,locator.source_locator_id,
       CASE work.work_code WHEN 'cepheus-engine.ogn' THEN 'direct' ELSE 'corroborating' END,
       work.work_code='cepheus-engine.ogn'
FROM rule_rule rule CROSS JOIN src_locator locator JOIN src_work work USING(source_work_id)
WHERE rule.rule_code='travel.ship-passage-operations'
  AND locator.heading_path LIKE 'Off-World Travel > Ship''s Passage%'
  AND work.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1');

ALTER TABLE journey_passage ADD COLUMN fare_basis text NOT NULL DEFAULT 'paid-single'
    CHECK(fare_basis IN('paid-single','paid-double','benefit','working','stowaway'));

CREATE FUNCTION journey_validate_passage_fare_basis()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE rules rule_passage_operation%ROWTYPE; expected_fare integer;
BEGIN
    SELECT * INTO STRICT rules FROM rule_passage_operation
    WHERE passage_class=NEW.passage_class;
    expected_fare:=CASE NEW.fare_basis
      WHEN 'paid-single' THEN rules.single_fare_credits
      WHEN 'paid-double' THEN rules.double_occupancy_per_passenger_credits
      ELSE 0 END;
    IF (NEW.passage_class='working')<>(NEW.fare_basis='working')
       OR (NEW.passage_class='stowaway')<>(NEW.fare_basis='stowaway')
       OR (NEW.fare_basis='paid-double' AND rules.double_occupancy_per_passenger_credits IS NULL)
       OR (NEW.fare_basis LIKE 'paid-%' AND expected_fare IS NULL)
       OR (NEW.fare_basis<>'benefit' AND NEW.fare_minor<>expected_fare)
       OR (NEW.fare_basis='benefit' AND NEW.fare_minor<>0) THEN
        RAISE EXCEPTION 'Passage fare and basis do not match the published passage class' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER journey_passage_fare_basis_valid
BEFORE INSERT OR UPDATE OF passage_class,fare_minor,fare_basis ON journey_passage
FOR EACH ROW EXECUTE FUNCTION journey_validate_passage_fare_basis();
