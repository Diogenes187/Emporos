CREATE OR REPLACE FUNCTION journey_validate_passage_manifest()
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
      AND skill.skill_rule_id=definition.governing_skill_rule_id
    WHERE assignment.ship_id=NEW.ship_id AND assignment.duty_status='active'
      AND definition.position_code='steward';
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
