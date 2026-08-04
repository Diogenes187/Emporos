INSERT INTO cmd_command_type VALUES
    ('determine_personal_surgery','Roll and retain a Surgery outcome before allocating its effect');
INSERT INTO cmd_domain_event_type VALUES
    ('personal_surgery_determined','Surgery outcome determined');

CREATE TABLE cmd_personal_surgery_determination (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    patient_actor_id bigint NOT NULL,
    doctor_actor_id bigint NOT NULL,
    first_aid_command_id bigint NOT NULL REFERENCES cmd_personal_first_aid_link(command_id),
    medical_facility_id bigint NOT NULL REFERENCES health_medical_facility(medical_facility_id),
    campaign_day_number bigint NOT NULL,
    campaign_second_of_day integer NOT NULL CHECK (campaign_second_of_day BETWEEN 0 AND 86399),
    patient_version bigint NOT NULL,
    medicine_skill_modifier integer NOT NULL,
    self_treatment_modifier integer NOT NULL,
    cross_species_modifier integer NOT NULL,
    die_one smallint NOT NULL CHECK (die_one BETWEEN 1 AND 6),
    die_two smallint NOT NULL CHECK (die_two BETWEEN 1 AND 6),
    check_total integer NOT NULL,
    target_number integer NOT NULL CHECK (target_number=8),
    effect integer NOT NULL CHECK (effect=check_total-target_number),
    signed_points integer NOT NULL,
    FOREIGN KEY (patient_actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id),
    FOREIGN KEY (doctor_actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id),
    CHECK (check_total=die_one+die_two+medicine_skill_modifier+self_treatment_modifier+cross_species_modifier),
    CHECK (signed_points=CASE WHEN effect>0 THEN effect*2 ELSE effect END)
);

CREATE TABLE cmd_personal_surgery_determination_application (
    determination_command_id bigint PRIMARY KEY REFERENCES cmd_personal_surgery_determination(command_id),
    treatment_command_id bigint NOT NULL UNIQUE REFERENCES cmd_personal_surgery_link(command_id)
);

CREATE TRIGGER cmd_personal_surgery_determination_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_surgery_determination
FOR EACH ROW EXECUTE FUNCTION cmd_reject_first_aid_determination_mutation();
CREATE TRIGGER cmd_personal_surgery_determination_application_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_surgery_determination_application
FOR EACH ROW EXECUTE FUNCTION cmd_reject_first_aid_determination_mutation();

COMMENT ON TABLE cmd_personal_surgery_determination IS
    'Immutable retained Surgery roll and signed effect awaiting player allocation.';
