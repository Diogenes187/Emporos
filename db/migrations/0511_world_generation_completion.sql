CREATE TABLE loc_world_travel_zone_event(
 world_travel_zone_event_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 campaign_id bigint NOT NULL,world_profile_id bigint NOT NULL REFERENCES loc_world_profile(world_profile_id),zone_version integer NOT NULL CHECK(zone_version>0),
 zone_code text NOT NULL CHECK(zone_code IN('clear','amber','red')),classification_basis text NOT NULL CHECK(classification_basis IN('generated-candidate','referee-assigned','referee-cleared')),
 amber_candidate_snapshot boolean NOT NULL,source_command_id bigint REFERENCES cmd_command(command_id),recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(world_profile_id,zone_version)
);
CREATE VIEW loc_world_current_travel_zone AS
SELECT DISTINCT ON(world_profile_id) world_travel_zone_event_id,campaign_id,world_profile_id,zone_version,zone_code,classification_basis,amber_candidate_snapshot,source_command_id,recorded_at
FROM loc_world_travel_zone_event ORDER BY world_profile_id,zone_version DESC;

CREATE TABLE loc_world_generation_completion_receipt(
 world_generation_receipt_id bigint PRIMARY KEY REFERENCES loc_world_generation_receipt(world_generation_receipt_id),
 world_profile_id bigint NOT NULL UNIQUE REFERENCES loc_world_profile(world_profile_id),
 world_system_detail_receipt_id bigint NOT NULL UNIQUE REFERENCES loc_world_system_detail_receipt(world_system_detail_receipt_id),
 initial_travel_zone_event_id bigint NOT NULL UNIQUE REFERENCES loc_world_travel_zone_event(world_travel_zone_event_id),
 source_command_id bigint REFERENCES cmd_command(command_id),completed_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE VIEW loc_generated_world_summary AS
SELECT profile.world_profile_id,profile.campaign_id,profile.location_id,profile.starport_code,profile.size_code,profile.atmosphere_code,
       profile.hydrographics_code,profile.population_code,profile.government_code,profile.law_level_code,profile.technology_level,
       detail.population_multiplier,detail.exact_population,detail.planetoid_belt_count,detail.gas_giant_count,detail.base_code,
       zone.zone_code AS current_travel_zone,zone.zone_version AS travel_zone_version
FROM loc_world_generation_completion_receipt completion
JOIN loc_world_profile profile ON profile.world_profile_id=completion.world_profile_id
JOIN loc_world_system_detail_receipt detail ON detail.world_system_detail_receipt_id=completion.world_system_detail_receipt_id
JOIN loc_world_current_travel_zone zone ON zone.world_profile_id=completion.world_profile_id;

CREATE FUNCTION loc_validate_world_travel_zone_event() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE p loc_world_profile%ROWTYPE;detail loc_world_system_detail_receipt%ROWTYPE;expected_version integer;expected_candidate boolean;
BEGIN
 SELECT * INTO STRICT p FROM loc_world_profile WHERE world_profile_id=NEW.world_profile_id;
 IF p.campaign_id<>NEW.campaign_id THEN RAISE EXCEPTION 'Travel-zone event crosses campaign scope' USING ERRCODE='23514';END IF;
 SELECT coalesce(max(zone_version),0)+1 INTO expected_version FROM loc_world_travel_zone_event WHERE world_profile_id=NEW.world_profile_id;
 SELECT amber_zone_candidate INTO expected_candidate FROM loc_world_system_detail_receipt WHERE world_profile_id=NEW.world_profile_id;
 IF expected_candidate IS NULL THEN
  expected_candidate:=p.atmosphere_code>=10 OR p.government_code IN(0,7,10) OR p.law_level_code=0 OR p.law_level_code>=9;
 END IF;
 IF NEW.zone_version<>expected_version OR NEW.amber_candidate_snapshot<>expected_candidate
    OR (NEW.classification_basis='generated-candidate' AND (NEW.zone_version<>1 OR NEW.zone_code<>CASE WHEN expected_candidate THEN 'amber' ELSE 'clear' END))
    OR (NEW.classification_basis='referee-cleared' AND NEW.zone_code<>'clear')
    OR (NEW.classification_basis='referee-assigned' AND NEW.zone_code='clear') THEN
  RAISE EXCEPTION 'Travel-zone event violates version, candidate, or classification basis' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER loc_world_travel_zone_event_valid BEFORE INSERT ON loc_world_travel_zone_event FOR EACH ROW EXECUTE FUNCTION loc_validate_world_travel_zone_event();

CREATE FUNCTION loc_validate_world_generation_completion() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE generation loc_world_generation_receipt%ROWTYPE;final loc_world_generation_final_receipt%ROWTYPE;detail loc_world_system_detail_receipt%ROWTYPE;zone loc_world_travel_zone_event%ROWTYPE;
BEGIN
 SELECT * INTO STRICT generation FROM loc_world_generation_receipt WHERE world_generation_receipt_id=NEW.world_generation_receipt_id;
 SELECT * INTO STRICT final FROM loc_world_generation_final_receipt WHERE world_generation_receipt_id=NEW.world_generation_receipt_id;
 SELECT * INTO STRICT detail FROM loc_world_system_detail_receipt WHERE world_system_detail_receipt_id=NEW.world_system_detail_receipt_id;
 SELECT * INTO STRICT zone FROM loc_world_travel_zone_event WHERE world_travel_zone_event_id=NEW.initial_travel_zone_event_id;
 IF generation.world_profile_id<>NEW.world_profile_id OR final.world_profile_id<>NEW.world_profile_id OR detail.world_profile_id<>NEW.world_profile_id
    OR zone.world_profile_id<>NEW.world_profile_id OR zone.campaign_id<>generation.campaign_id OR zone.zone_version<>1 OR zone.classification_basis<>'generated-candidate' THEN
  RAISE EXCEPTION 'World completion receipt does not join one complete generated-world history' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER loc_world_generation_completion_valid BEFORE INSERT ON loc_world_generation_completion_receipt FOR EACH ROW EXECUTE FUNCTION loc_validate_world_generation_completion();

CREATE TRIGGER loc_world_travel_zone_event_immutable BEFORE UPDATE OR DELETE ON loc_world_travel_zone_event FOR EACH ROW EXECUTE FUNCTION loc_reject_world_generation_mutation();
CREATE TRIGGER loc_world_generation_completion_immutable BEFORE UPDATE OR DELETE ON loc_world_generation_completion_receipt FOR EACH ROW EXECUTE FUNCTION loc_reject_world_generation_mutation();
