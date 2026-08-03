CREATE OR REPLACE FUNCTION journey_validate_passage_fare_basis()
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
       OR (NEW.fare_basis='benefit' AND NEW.fare_minor<>0)
       OR (rules.baggage_allowance_kg IS NOT NULL
           AND coalesce(NEW.baggage_mass_kg,0)>rules.baggage_allowance_kg) THEN
        RAISE EXCEPTION 'Passage fare, basis, or baggage does not match the published passage class' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;
