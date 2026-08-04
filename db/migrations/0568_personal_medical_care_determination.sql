INSERT INTO cmd_command_type VALUES
    ('determine_personal_medical_care','Determine and retain the daily Medical Care allowance');
INSERT INTO cmd_domain_event_type VALUES
    ('personal_medical_care_determined','Daily Medical Care allowance determined');

CREATE TABLE cmd_personal_medical_care_determination (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    patient_actor_id bigint NOT NULL,
    doctor_actor_id bigint NOT NULL,
    medical_facility_id bigint NOT NULL REFERENCES health_medical_facility(medical_facility_id),
    campaign_day_number bigint NOT NULL,
    campaign_second_of_day integer NOT NULL CHECK (campaign_second_of_day BETWEEN 0 AND 86399),
    patient_version bigint NOT NULL,
    medicine_skill_modifier integer NOT NULL,
    endurance_modifier integer NOT NULL,
    available_points integer NOT NULL CHECK (available_points>=0),
    damaged_characteristic_count smallint NOT NULL CHECK (damaged_characteristic_count BETWEEN 1 AND 3),
    even_base_share integer NOT NULL CHECK (even_base_share>=0),
    remainder_points integer NOT NULL CHECK (remainder_points>=0),
    FOREIGN KEY (patient_actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id),
    FOREIGN KEY (doctor_actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id),
    CHECK (available_points=GREATEST(0,2+endurance_modifier+medicine_skill_modifier)),
    CHECK (even_base_share=available_points/damaged_characteristic_count),
    CHECK (remainder_points=mod(available_points,damaged_characteristic_count))
);

CREATE TABLE cmd_personal_medical_care_determination_application (
    determination_command_id bigint PRIMARY KEY REFERENCES cmd_personal_medical_care_determination(command_id),
    treatment_command_id bigint NOT NULL UNIQUE REFERENCES cmd_personal_medical_care_link(command_id)
);

CREATE TRIGGER cmd_personal_medical_care_determination_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_medical_care_determination
FOR EACH ROW EXECUTE FUNCTION cmd_reject_first_aid_determination_mutation();
CREATE TRIGGER cmd_personal_medical_care_determination_application_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_medical_care_determination_application
FOR EACH ROW EXECUTE FUNCTION cmd_reject_first_aid_determination_mutation();

COMMENT ON TABLE cmd_personal_medical_care_determination IS
    'Immutable deterministic daily recovery allowance and even-allocation requirement.';
