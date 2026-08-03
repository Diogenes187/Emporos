CREATE FUNCTION env_validate_disease_schedule() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE disease_case env_disease_case%ROWTYPE;
BEGIN
 SELECT * INTO STRICT disease_case FROM env_disease_case WHERE disease_case_id=NEW.disease_case_id FOR UPDATE;
 IF disease_case.next_check_at IS NOT NULL AND clock_timestamp()<disease_case.next_check_at THEN
  RAISE EXCEPTION 'Disease follow-up check cannot occur before its rolled interval has elapsed' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER env_disease_check_a_schedule BEFORE INSERT ON env_disease_check_receipt FOR EACH ROW EXECUTE FUNCTION env_validate_disease_schedule();
