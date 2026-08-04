INSERT INTO cmd_command_type VALUES
    ('determine_personal_natural_healing','Determine and retain signed natural healing before allocation');
INSERT INTO cmd_domain_event_type VALUES
    ('personal_natural_healing_determined','Natural healing result determined');

CREATE TABLE cmd_personal_natural_healing_determination (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    actor_id bigint NOT NULL,
    campaign_day_number bigint NOT NULL,
    actor_version bigint NOT NULL,
    lifestyle text NOT NULL CHECK (lifestyle IN ('full_rest','active')),
    injury_status text NOT NULL CHECK (injury_status IN ('wounded','seriously_wounded')),
    endurance_modifier integer NOT NULL,
    healing_die_result smallint CHECK (healing_die_result BETWEEN 1 AND 6),
    signed_points integer NOT NULL,
    FOREIGN KEY (actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id),
    CHECK ((lifestyle='full_rest' AND injury_status='wounded')=(healing_die_result IS NOT NULL)),
    CHECK (signed_points=CASE WHEN injury_status='seriously_wounded' THEN endurance_modifier WHEN lifestyle='full_rest' THEN healing_die_result+endurance_modifier ELSE 1+endurance_modifier END)
);

CREATE TABLE cmd_personal_natural_healing_determination_application (
    determination_command_id bigint PRIMARY KEY REFERENCES cmd_personal_natural_healing_determination(command_id),
    healing_command_id bigint NOT NULL UNIQUE REFERENCES cmd_personal_natural_healing_receipt(command_id)
);

CREATE TRIGGER cmd_personal_natural_healing_determination_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_natural_healing_determination
FOR EACH ROW EXECUTE FUNCTION cmd_reject_first_aid_determination_mutation();
CREATE TRIGGER cmd_personal_natural_healing_determination_application_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_natural_healing_determination_application
FOR EACH ROW EXECUTE FUNCTION cmd_reject_first_aid_determination_mutation();

COMMENT ON TABLE cmd_personal_natural_healing_determination IS
    'Immutable retained daily natural-healing result awaiting signed allocation.';
