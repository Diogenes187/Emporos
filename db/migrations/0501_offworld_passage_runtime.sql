ALTER TABLE journey_passage ADD COLUMN concurrency_version bigint NOT NULL DEFAULT 1
    CHECK(concurrency_version>0);
ALTER TABLE journey_passage ADD CONSTRAINT journey_passage_campaign_key
    UNIQUE(journey_passage_id,campaign_id);

CREATE TABLE journey_passage_accommodation_assignment(
    passage_accommodation_assignment_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    journey_passage_id bigint NOT NULL UNIQUE,
    campaign_id bigint NOT NULL,
    journey_id bigint NOT NULL,
    ship_id bigint NOT NULL,
    accommodation_kind text NOT NULL CHECK(accommodation_kind IN('stateroom','low-berth','crew-accommodation','hidden')),
    unit_identifier text NOT NULL CHECK(btrim(unit_identifier)<>''),
    occupancy_mode text NOT NULL CHECK(occupancy_mode IN('single','double','working','hidden')),
    assigned_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    source_command_id bigint REFERENCES cmd_command(command_id),
    FOREIGN KEY(journey_passage_id,campaign_id,journey_id)
      REFERENCES journey_passage(journey_passage_id,campaign_id,journey_id),
    FOREIGN KEY(journey_id,campaign_id) REFERENCES journey_journey(journey_id,campaign_id),
    FOREIGN KEY(ship_id,campaign_id) REFERENCES ship_ship(ship_id,campaign_id),
    UNIQUE(passage_accommodation_assignment_id,campaign_id)
);

CREATE TABLE journey_passage_accommodation_release_receipt(
    passage_accommodation_assignment_id bigint PRIMARY KEY,
    campaign_id bigint NOT NULL,
    release_kind text NOT NULL CHECK(release_kind IN('completed','cancelled','bumped')),
    refund_credits bigint NOT NULL DEFAULT 0 CHECK(refund_credits>=0),
    financial_transaction_id bigint UNIQUE,
    released_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    source_command_id bigint REFERENCES cmd_command(command_id),
    FOREIGN KEY(passage_accommodation_assignment_id,campaign_id)
      REFERENCES journey_passage_accommodation_assignment(passage_accommodation_assignment_id,campaign_id),
    FOREIGN KEY(financial_transaction_id,campaign_id)
      REFERENCES fin_transaction(transaction_id,campaign_id),
    CHECK((refund_credits=0)=(financial_transaction_id IS NULL))
);

CREATE VIEW journey_active_passage_accommodation AS
SELECT assignment.*
FROM journey_passage_accommodation_assignment assignment
LEFT JOIN journey_passage_accommodation_release_receipt release
  USING(passage_accommodation_assignment_id)
WHERE release.passage_accommodation_assignment_id IS NULL;

CREATE FUNCTION journey_validate_passage_accommodation()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE passage journey_passage%ROWTYPE; journey_ship bigint; rules rule_passage_operation%ROWTYPE;
        current_occupants integer; used_units integer; capacity integer;
        jump_legs integer; working_actor bigint;
BEGIN
    SELECT * INTO STRICT passage FROM journey_passage
    WHERE journey_passage_id=NEW.journey_passage_id
      AND campaign_id=NEW.campaign_id AND journey_id=NEW.journey_id;
    SELECT ship_id INTO STRICT journey_ship FROM journey_journey
    WHERE journey_id=NEW.journey_id AND campaign_id=NEW.campaign_id;
    SELECT * INTO STRICT rules FROM rule_passage_operation
    WHERE passage_class=passage.passage_class;
    IF journey_ship<>NEW.ship_id OR NEW.accommodation_kind<>rules.accommodation_kind
       OR NEW.occupancy_mode<>(CASE passage.fare_basis
          WHEN 'paid-double' THEN 'double' WHEN 'working' THEN 'working'
          WHEN 'stowaway' THEN 'hidden' ELSE 'single' END) THEN
        RAISE EXCEPTION 'Passage accommodation does not match journey ship, class, or fare basis' USING ERRCODE='23514';
    END IF;
    IF NEW.accommodation_kind IN('stateroom','low-berth') THEN
        PERFORM 1 FROM ship_ship WHERE ship_id=NEW.ship_id FOR UPDATE;
        SELECT count(*) INTO current_occupants FROM journey_active_passage_accommodation active
        JOIN journey_passage existing USING(journey_passage_id)
        WHERE active.journey_id=NEW.journey_id
          AND active.accommodation_kind=NEW.accommodation_kind
          AND active.unit_identifier=NEW.unit_identifier;
        IF (NEW.occupancy_mode='double' AND current_occupants>=2)
           OR (NEW.occupancy_mode<>'double' AND current_occupants>0)
           OR (NEW.occupancy_mode='double' AND EXISTS(
              SELECT 1 FROM journey_active_passage_accommodation active
              JOIN journey_passage existing USING(journey_passage_id)
              WHERE active.journey_id=NEW.journey_id
                AND active.accommodation_kind=NEW.accommodation_kind
                AND active.unit_identifier=NEW.unit_identifier
                AND (active.occupancy_mode<>'double' OR existing.passage_class<>passage.passage_class)
           )) THEN
            RAISE EXCEPTION 'Passage accommodation unit occupancy is inconsistent' USING ERRCODE='23514';
        END IF;
        SELECT count(DISTINCT unit_identifier) INTO used_units
        FROM journey_active_passage_accommodation
        WHERE journey_id=NEW.journey_id AND accommodation_kind=NEW.accommodation_kind;
        IF current_occupants=0 THEN used_units:=used_units+1; END IF;
        SELECT coalesce(characteristic_value,0)::integer INTO capacity
        FROM ship_ship ship LEFT JOIN ship_class_characteristic characteristic
          ON characteristic.ship_class_rule_id=ship.ship_class_rule_id
         AND characteristic.characteristic_code=CASE NEW.accommodation_kind
              WHEN 'stateroom' THEN 'staterooms' ELSE 'low_berths' END
        WHERE ship.ship_id=NEW.ship_id;
        IF used_units>capacity THEN
            RAISE EXCEPTION 'Passage accommodations exceed installed ship capacity' USING ERRCODE='23514';
        END IF;
    ELSIF NEW.accommodation_kind='crew-accommodation' THEN
        SELECT actor_id INTO STRICT working_actor FROM journey_passage
        WHERE journey_passage_id=NEW.journey_passage_id;
        SELECT count(*) INTO jump_legs FROM journey_leg
        WHERE journey_id=NEW.journey_id AND travel_mode='jump'
          AND leg_status NOT IN('skipped','failed');
        IF jump_legs>rules.maximum_working_jumps OR NOT EXISTS(
          SELECT 1 FROM journey_ship_crew_commitment commitment
          JOIN journey_participant participant USING(journey_participant_id,journey_id,campaign_id)
          JOIN ship_crew_assignment assignment USING(crew_assignment_id,ship_id,campaign_id)
          JOIN ship_crew_position position USING(ship_crew_position_id,ship_id,campaign_id)
          JOIN ship_crew_position_definition definition USING(crew_position_rule_id)
          JOIN actor_skill skill ON skill.actor_id=working_actor
             AND skill.skill_rule_id=definition.governing_skill_rule_id
          WHERE commitment.journey_id=NEW.journey_id AND commitment.ship_id=NEW.ship_id
            AND participant.actor_id=working_actor AND commitment.commitment_status='assigned'
            AND assignment.duty_status='active' AND skill.skill_level>=0
        ) THEN
            RAISE EXCEPTION 'Working passage requires position expertise and no more than three jumps' USING ERRCODE='23514';
        END IF;
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER journey_passage_accommodation_valid
BEFORE INSERT OR UPDATE ON journey_passage_accommodation_assignment
FOR EACH ROW EXECUTE FUNCTION journey_validate_passage_accommodation();

CREATE FUNCTION journey_validate_passage_release()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE passage journey_passage%ROWTYPE; assignment journey_passage_accommodation_assignment%ROWTYPE; tx_status text;
BEGIN
    SELECT * INTO STRICT assignment FROM journey_passage_accommodation_assignment
    WHERE passage_accommodation_assignment_id=NEW.passage_accommodation_assignment_id
      AND campaign_id=NEW.campaign_id;
    SELECT * INTO STRICT passage FROM journey_passage
    WHERE journey_passage_id=assignment.journey_passage_id;
    IF NEW.release_kind='bumped' AND (passage.passage_class<>'middle' OR passage.fare_basis NOT LIKE 'paid-%') THEN
        RAISE EXCEPTION 'Only paid middle passage may be bumped' USING ERRCODE='23514';
    END IF;
    IF NEW.refund_credits<>(CASE WHEN NEW.release_kind='bumped' THEN passage.fare_minor ELSE 0 END) THEN
        RAISE EXCEPTION 'Passage release refund does not match the paid fare' USING ERRCODE='23514';
    END IF;
    IF NEW.financial_transaction_id IS NOT NULL THEN
        SELECT transaction_status INTO STRICT tx_status FROM fin_transaction
        WHERE transaction_id=NEW.financial_transaction_id AND campaign_id=NEW.campaign_id;
        IF tx_status<>'posted' THEN RAISE EXCEPTION 'Passage refund transaction must be posted' USING ERRCODE='23514'; END IF;
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER journey_passage_release_valid
BEFORE INSERT ON journey_passage_accommodation_release_receipt
FOR EACH ROW EXECUTE FUNCTION journey_validate_passage_release();

CREATE TABLE journey_passage_manifest_receipt(
    journey_id bigint PRIMARY KEY,
    campaign_id bigint NOT NULL,
    ship_id bigint NOT NULL,
    high_passengers integer NOT NULL CHECK(high_passengers>=0),
    middle_passengers integer NOT NULL CHECK(middle_passengers>=0),
    low_passengers integer NOT NULL CHECK(low_passengers>=0),
    stateroom_units_used integer NOT NULL CHECK(stateroom_units_used>=0),
    low_berths_used integer NOT NULL CHECK(low_berths_used>=0),
    steward_level_quanta integer NOT NULL CHECK(steward_level_quanta>=0),
    steward_quanta_required integer NOT NULL CHECK(steward_quanta_required>=0),
    finalized_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    source_command_id bigint REFERENCES cmd_command(command_id),
    FOREIGN KEY(journey_id,campaign_id) REFERENCES journey_journey(journey_id,campaign_id),
    FOREIGN KEY(ship_id,campaign_id) REFERENCES ship_ship(ship_id,campaign_id)
);

CREATE FUNCTION journey_validate_passage_manifest()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE actual_ship bigint; active_count integer; passage_count integer; high_count integer;
        middle_count integer; low_count integer; rooms integer; berths integer;
        steward_quanta integer; required_quanta integer; incomplete_double integer;
BEGIN
    SELECT ship_id INTO STRICT actual_ship FROM journey_journey
    WHERE journey_id=NEW.journey_id AND campaign_id=NEW.campaign_id FOR UPDATE;
    SELECT count(*) FILTER(WHERE passage_class='high'),
           count(*) FILTER(WHERE passage_class='middle'),
           count(*) FILTER(WHERE passage_class='low'),count(*)
    INTO high_count,middle_count,low_count,passage_count
    FROM journey_passage WHERE journey_id=NEW.journey_id
      AND passage_status IN('booked','boarded');
    SELECT count(*),count(DISTINCT unit_identifier) FILTER(WHERE accommodation_kind='stateroom'),
           count(DISTINCT unit_identifier) FILTER(WHERE accommodation_kind='low-berth')
    INTO active_count,rooms,berths FROM journey_active_passage_accommodation
    WHERE journey_id=NEW.journey_id;
    SELECT count(*) INTO incomplete_double FROM(
      SELECT unit_identifier FROM journey_active_passage_accommodation
      WHERE journey_id=NEW.journey_id AND occupancy_mode='double'
      GROUP BY unit_identifier HAVING count(*)<>2
    ) incomplete;
    SELECT coalesce(sum(skill.skill_level+1),0) INTO steward_quanta
    FROM ship_crew_assignment assignment
    JOIN ship_crew_position position USING(ship_crew_position_id,ship_id,campaign_id)
    JOIN ship_crew_position_definition definition USING(crew_position_rule_id)
    JOIN actor_skill skill ON skill.actor_id=assignment.actor_id
    JOIN rule_skill steward_skill ON steward_skill.rule_id=skill.skill_rule_id
    WHERE assignment.ship_id=NEW.ship_id AND assignment.duty_status='active'
      AND definition.position_code='steward' AND steward_skill.skill_code='steward';
    required_quanta:=(high_count+1)/2+(middle_count+4)/5;
    IF actual_ship<>NEW.ship_id OR active_count<>passage_count OR incomplete_double<>0
       OR steward_quanta<required_quanta
       OR (NEW.high_passengers,NEW.middle_passengers,NEW.low_passengers,
           NEW.stateroom_units_used,NEW.low_berths_used,NEW.steward_level_quanta,
           NEW.steward_quanta_required)
          IS DISTINCT FROM
          (high_count,middle_count,low_count,rooms,berths,steward_quanta,required_quanta) THEN
        RAISE EXCEPTION 'Passage manifest does not match accommodations, ship, or steward capacity' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER journey_passage_manifest_valid BEFORE INSERT OR UPDATE ON journey_passage_manifest_receipt
FOR EACH ROW EXECUTE FUNCTION journey_validate_passage_manifest();

CREATE FUNCTION journey_require_passage_manifest()
RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
    IF NEW.journey_status IN('ready','underway') AND OLD.journey_status<>NEW.journey_status
       AND EXISTS(SELECT 1 FROM journey_passage WHERE journey_id=NEW.journey_id AND passage_status IN('booked','boarded'))
       AND NOT EXISTS(SELECT 1 FROM journey_passage_manifest_receipt WHERE journey_id=NEW.journey_id) THEN
        RAISE EXCEPTION 'Passenger journey requires a finalized passage manifest' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER journey_passage_manifest_required
BEFORE UPDATE OF journey_status ON journey_journey
FOR EACH ROW EXECUTE FUNCTION journey_require_passage_manifest();

CREATE TABLE journey_low_passage_revival_receipt(
    journey_passage_id bigint PRIMARY KEY,
    campaign_id bigint NOT NULL,
    passenger_actor_id bigint NOT NULL,
    passenger_task_command_id bigint NOT NULL UNIQUE REFERENCES cmd_actor_task_receipt(command_id),
    task_assistance_receipt_id bigint UNIQUE REFERENCES cmd_task_assistance_receipt(task_assistance_receipt_id),
    assistance_modifier smallint NOT NULL DEFAULT 0 CHECK(assistance_modifier IN(-2,-1,0,1,2)),
    passenger_succeeded boolean NOT NULL,
    passage_status_before text NOT NULL CHECK(passage_status_before='boarded'),
    passage_status_after text NOT NULL CHECK(passage_status_after IN('completed','failed_revival')),
    passage_version_before bigint NOT NULL,
    passage_version_after bigint NOT NULL CHECK(passage_version_after=passage_version_before+1),
    revived_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    source_command_id bigint REFERENCES cmd_command(command_id),
    FOREIGN KEY(journey_passage_id,campaign_id)
      REFERENCES journey_passage(journey_passage_id,campaign_id),
    FOREIGN KEY(passenger_actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id),
    CHECK(passenger_succeeded=(passage_status_after='completed'))
);

CREATE TABLE actor_low_passage_death_state(
    actor_id bigint PRIMARY KEY REFERENCES actor_actor(actor_id),
    journey_passage_id bigint NOT NULL UNIQUE REFERENCES journey_low_passage_revival_receipt(journey_passage_id),
    died_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE FUNCTION journey_validate_low_passage_revival()
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
        IF NEW.assistance_modifier<>0 THEN RAISE EXCEPTION 'Unassisted revival has no assistance modifier' USING ERRCODE='23514'; END IF;
    ELSE
        SELECT * INTO STRICT aid FROM cmd_task_assistance_receipt
        WHERE task_assistance_receipt_id=NEW.task_assistance_receipt_id;
        SELECT * INTO STRICT helper FROM cmd_actor_task_receipt WHERE command_id=aid.helper_task_command_id;
        IF aid.leader_task_command_id<>NEW.passenger_task_command_id
           OR aid.assistance_mode<>'source-prescribed-check'
           OR aid.assistance_context<>'low-passage-revival'
           OR aid.assistance_modifier<>NEW.assistance_modifier
           OR helper.characteristic_rule_id<>rules.medic_characteristic_rule_id
           OR helper.skill_rule_id<>rules.medic_skill_rule_id
           OR helper.difficulty_rule_id<>rules.medic_difficulty_rule_id THEN
            RAISE EXCEPTION 'Low-passage aid must be the published Routine Education Medicine check' USING ERRCODE='23514';
        END IF;
    END IF;
    UPDATE journey_passage SET passage_status=NEW.passage_status_after,
        concurrency_version=NEW.passage_version_after
    WHERE journey_passage_id=NEW.journey_passage_id;
    RETURN NEW;
END $$;

CREATE TRIGGER journey_low_passage_revival_valid
BEFORE INSERT ON journey_low_passage_revival_receipt
FOR EACH ROW EXECUTE FUNCTION journey_validate_low_passage_revival();

CREATE FUNCTION journey_apply_low_passage_death()
RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
    IF NOT NEW.passenger_succeeded THEN
        INSERT INTO actor_low_passage_death_state(actor_id,journey_passage_id)
        VALUES(NEW.passenger_actor_id,NEW.journey_passage_id);
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER journey_low_passage_death_apply
AFTER INSERT ON journey_low_passage_revival_receipt
FOR EACH ROW EXECUTE FUNCTION journey_apply_low_passage_death();

CREATE FUNCTION journey_reject_passage_receipt_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Passage receipts are immutable'; END $$;
CREATE TRIGGER journey_passage_assignment_immutable BEFORE UPDATE OR DELETE ON journey_passage_accommodation_assignment FOR EACH ROW EXECUTE FUNCTION journey_reject_passage_receipt_mutation();
CREATE TRIGGER journey_passage_release_immutable BEFORE UPDATE OR DELETE ON journey_passage_accommodation_release_receipt FOR EACH ROW EXECUTE FUNCTION journey_reject_passage_receipt_mutation();
CREATE TRIGGER journey_passage_manifest_immutable BEFORE UPDATE OR DELETE ON journey_passage_manifest_receipt FOR EACH ROW EXECUTE FUNCTION journey_reject_passage_receipt_mutation();
CREATE TRIGGER journey_low_passage_revival_immutable BEFORE UPDATE OR DELETE ON journey_low_passage_revival_receipt FOR EACH ROW EXECUTE FUNCTION journey_reject_passage_receipt_mutation();
CREATE TRIGGER actor_low_passage_death_immutable BEFORE UPDATE OR DELETE ON actor_low_passage_death_state FOR EACH ROW EXECUTE FUNCTION journey_reject_passage_receipt_mutation();
