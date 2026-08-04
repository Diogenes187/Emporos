INSERT INTO cmd_command_type VALUES
    ('determine_personal_first_aid','Roll and retain a First Aid outcome before allocating restoration');

INSERT INTO cmd_domain_event_type VALUES
    ('personal_first_aid_determined','First Aid outcome determined');

CREATE TABLE cmd_personal_first_aid_determination (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    patient_actor_id bigint NOT NULL,
    doctor_actor_id bigint NOT NULL,
    damage_instance_id bigint NOT NULL REFERENCES health_damage_instance(damage_instance_id),
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
    elapsed_seconds integer NOT NULL CHECK (elapsed_seconds>=0),
    effectiveness_tier text NOT NULL CHECK (effectiveness_tier IN ('full','late','expired')),
    effect_multiplier integer NOT NULL CHECK (effect_multiplier IN (0,1,2)),
    available_points integer NOT NULL CHECK (available_points>=0),
    FOREIGN KEY (patient_actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id),
    FOREIGN KEY (doctor_actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id),
    CHECK (check_total=die_one+die_two+medicine_skill_modifier+self_treatment_modifier+cross_species_modifier),
    CHECK (available_points=GREATEST(0,effect)*effect_multiplier),
    CHECK (effect_multiplier=CASE effectiveness_tier WHEN 'full' THEN 2 WHEN 'late' THEN 1 ELSE 0 END)
);

CREATE TABLE cmd_personal_first_aid_determination_application (
    determination_command_id bigint PRIMARY KEY REFERENCES cmd_personal_first_aid_determination(command_id),
    treatment_command_id bigint NOT NULL UNIQUE REFERENCES cmd_personal_first_aid_link(command_id)
);

CREATE FUNCTION cmd_reject_first_aid_determination_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'First Aid determination history is immutable'; END;
$$;

CREATE TRIGGER cmd_personal_first_aid_determination_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_first_aid_determination
FOR EACH ROW EXECUTE FUNCTION cmd_reject_first_aid_determination_mutation();

CREATE TRIGGER cmd_personal_first_aid_determination_application_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_first_aid_determination_application
FOR EACH ROW EXECUTE FUNCTION cmd_reject_first_aid_determination_mutation();

COMMENT ON TABLE cmd_personal_first_aid_determination IS
    'Immutable retained First Aid roll and exact restoration budget awaiting player allocation.';
COMMENT ON TABLE cmd_personal_first_aid_determination_application IS
    'One-to-one consumption of a retained First Aid determination by an audited treatment.';
