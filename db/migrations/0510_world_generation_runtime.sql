CREATE TABLE loc_hex_generation_receipt(
 hex_generation_receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 campaign_id bigint NOT NULL,subsector_location_id bigint NOT NULL,hex_column smallint NOT NULL CHECK(hex_column BETWEEN 1 AND 8),hex_row smallint NOT NULL CHECK(hex_row BETWEEN 1 AND 10),
 density_code text NOT NULL REFERENCES rule_world_hex_density(density_code),presence_roll smallint NOT NULL CHECK(presence_roll BETWEEN 1 AND 6),density_modifier smallint NOT NULL,
 adjusted_total smallint NOT NULL,system_present boolean NOT NULL,system_location_id bigint,source_command_id bigint REFERENCES cmd_command(command_id),recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(subsector_location_id) REFERENCES loc_subsector(location_id),
 FOREIGN KEY(system_location_id,campaign_id) REFERENCES loc_star_system(location_id,campaign_id),
 UNIQUE(campaign_id,subsector_location_id,hex_column,hex_row),CHECK(system_present=(system_location_id IS NOT NULL))
);

CREATE TABLE loc_world_generation_receipt(
 world_generation_receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 campaign_id bigint NOT NULL,world_profile_id bigint NOT NULL UNIQUE REFERENCES loc_world_profile(world_profile_id),
 size_roll smallint NOT NULL CHECK(size_roll BETWEEN 2 AND 12),atmosphere_roll smallint NOT NULL CHECK(atmosphere_roll BETWEEN 2 AND 12),
 hydrographics_roll smallint NOT NULL CHECK(hydrographics_roll BETWEEN 2 AND 12),hydrographics_modifier smallint NOT NULL,
 population_roll smallint NOT NULL CHECK(population_roll BETWEEN 2 AND 12),population_modifier smallint NOT NULL,
 starport_roll smallint NOT NULL CHECK(starport_roll BETWEEN 2 AND 12),government_roll smallint NOT NULL CHECK(government_roll BETWEEN 2 AND 12),
 law_level_roll smallint NOT NULL CHECK(law_level_roll BETWEEN 2 AND 12),technology_roll smallint NOT NULL CHECK(technology_roll BETWEEN 1 AND 6),
 technology_modifier smallint NOT NULL,technology_minimum smallint NOT NULL CHECK(technology_minimum IN(0,4,5,7)),
 source_command_id bigint REFERENCES cmd_command(command_id),recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 CHECK(campaign_id>0)
);

CREATE TABLE loc_world_generation_final_receipt(
 world_generation_receipt_id bigint PRIMARY KEY REFERENCES loc_world_generation_receipt(world_generation_receipt_id),
 world_profile_id bigint NOT NULL UNIQUE REFERENCES loc_world_profile(world_profile_id),assigned_trade_code_count smallint NOT NULL CHECK(assigned_trade_code_count>=0),
 source_command_id bigint REFERENCES cmd_command(command_id),finalized_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE loc_world_system_detail_receipt(
 world_system_detail_receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 campaign_id bigint NOT NULL,world_profile_id bigint NOT NULL UNIQUE REFERENCES loc_world_profile(world_profile_id),system_location_id bigint NOT NULL,
 population_multiplier_roll smallint NOT NULL CHECK(population_multiplier_roll BETWEEN 2 AND 12),population_multiplier smallint NOT NULL CHECK(population_multiplier BETWEEN 0 AND 10),exact_population bigint NOT NULL CHECK(exact_population>=0),
 belt_presence_roll smallint NOT NULL CHECK(belt_presence_roll BETWEEN 2 AND 12),belt_count_roll smallint CHECK(belt_count_roll BETWEEN 1 AND 6),planetoid_belt_count smallint NOT NULL CHECK(planetoid_belt_count BETWEEN 0 AND 3),
 gas_presence_roll smallint NOT NULL CHECK(gas_presence_roll BETWEEN 2 AND 12),gas_count_roll smallint CHECK(gas_count_roll BETWEEN 1 AND 6),gas_giant_count smallint NOT NULL CHECK(gas_giant_count BETWEEN 0 AND 4),
 naval_base_roll smallint CHECK(naval_base_roll BETWEEN 2 AND 12),naval_base_present boolean NOT NULL,
 scout_base_roll smallint CHECK(scout_base_roll BETWEEN 2 AND 12),scout_base_present boolean NOT NULL,
 pirate_base_roll smallint CHECK(pirate_base_roll BETWEEN 2 AND 12),pirate_base_present boolean NOT NULL,
 base_code text CHECK(base_code IN('A','G','N','P','S')),amber_zone_candidate boolean NOT NULL,
 source_command_id bigint REFERENCES cmd_command(command_id),recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 CHECK(campaign_id>0),
 FOREIGN KEY(system_location_id,campaign_id) REFERENCES loc_star_system(location_id,campaign_id)
);

CREATE FUNCTION loc_validate_hex_generation_receipt() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE density rule_world_hex_density%ROWTYPE;subsector loc_subsector%ROWTYPE;system_row loc_star_system%ROWTYPE;expected_column integer;expected_row integer;
BEGIN
 SELECT * INTO STRICT density FROM rule_world_hex_density WHERE density_code=NEW.density_code;
 SELECT * INTO STRICT subsector FROM loc_subsector WHERE location_id=NEW.subsector_location_id AND campaign_id=NEW.campaign_id;
 expected_column:=(subsector.subsector_column-1)*8+NEW.hex_column;expected_row:=(subsector.subsector_row-1)*10+NEW.hex_row;
 IF NEW.density_modifier<>density.density_modifier OR NEW.adjusted_total<>NEW.presence_roll+density.density_modifier
    OR NEW.system_present<>(NEW.adjusted_total>=density.presence_target) THEN
  RAISE EXCEPTION 'Hex generation receipt does not match published one-D6 density procedure' USING ERRCODE='23514';
 END IF;
 IF NEW.system_present THEN
  SELECT * INTO STRICT system_row FROM loc_star_system WHERE location_id=NEW.system_location_id AND campaign_id=NEW.campaign_id;
  IF system_row.subsector_location_id<>NEW.subsector_location_id OR system_row.sector_location_id<>subsector.sector_location_id
     OR system_row.hex_column<>expected_column OR system_row.hex_row<>expected_row THEN
   RAISE EXCEPTION 'Generated system does not occupy the recorded subsector hex' USING ERRCODE='23514';
  END IF;
 ELSIF EXISTS(SELECT 1 FROM loc_star_system WHERE campaign_id=NEW.campaign_id AND sector_location_id=subsector.sector_location_id AND hex_column=expected_column AND hex_row=expected_row) THEN
  RAISE EXCEPTION 'Absent hex generation receipt conflicts with an existing system' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER loc_hex_generation_receipt_valid BEFORE INSERT ON loc_hex_generation_receipt FOR EACH ROW EXECUTE FUNCTION loc_validate_hex_generation_receipt();

CREATE FUNCTION loc_validate_world_generation_receipt() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE p loc_world_profile%ROWTYPE;expected_size integer;expected_atmosphere integer;expected_hydro integer;expected_hydro_dm integer;
 expected_population integer;expected_population_dm integer;starport_total integer;expected_starport text;expected_government integer;expected_law integer;
 expected_tech_dm integer;expected_tech_min integer;expected_tech integer;
BEGIN
 SELECT * INTO STRICT p FROM loc_world_profile WHERE world_profile_id=NEW.world_profile_id AND campaign_id=NEW.campaign_id;
 expected_size:=greatest(0,least(10,NEW.size_roll-2));
 expected_atmosphere:=CASE WHEN expected_size=0 THEN 0 ELSE greatest(0,least(15,NEW.atmosphere_roll-7+expected_size)) END;
 expected_hydro_dm:=CASE WHEN expected_atmosphere IN(0,1,10,11,12) THEN -4 WHEN expected_atmosphere=14 THEN -2 ELSE 0 END;
 expected_hydro:=CASE WHEN expected_size<=1 THEN 0 ELSE greatest(0,least(10,NEW.hydrographics_roll-7+expected_size+expected_hydro_dm)) END;
 expected_population_dm:=(CASE WHEN expected_size<=2 THEN -1 ELSE 0 END)+(CASE WHEN expected_atmosphere>=10 THEN -2 WHEN expected_atmosphere=6 THEN 3 WHEN expected_atmosphere IN(5,8) THEN 1 ELSE 0 END)+(CASE WHEN expected_hydro=0 AND expected_atmosphere<3 THEN -2 ELSE 0 END);
 expected_population:=greatest(0,least(10,NEW.population_roll-2+expected_population_dm));
 starport_total:=NEW.starport_roll-7+expected_population;
 SELECT starport_code INTO STRICT expected_starport FROM rule_world_starport_band WHERE minimum_total<=starport_total AND (maximum_total IS NULL OR maximum_total>=starport_total);
 expected_government:=CASE WHEN expected_population=0 THEN 0 ELSE greatest(0,least(15,NEW.government_roll-7+expected_population)) END;
 expected_law:=CASE WHEN expected_government=0 THEN 0 ELSE greatest(0,least(15,NEW.law_level_roll-7+expected_government)) END;
 expected_tech_dm:=(SELECT modifier_value FROM rule_world_starport_technology_modifier WHERE starport_code=expected_starport)
  +(CASE WHEN expected_size<=1 THEN 2 WHEN expected_size<=4 THEN 1 ELSE 0 END)
  +(CASE WHEN expected_atmosphere<=3 OR expected_atmosphere>=10 THEN 1 ELSE 0 END)
  +(CASE WHEN expected_hydro IN(0,9) THEN 1 WHEN expected_hydro=10 THEN 2 ELSE 0 END)
  +(CASE WHEN expected_population BETWEEN 1 AND 5 OR expected_population=9 THEN 1 WHEN expected_population=10 THEN 2 ELSE 0 END)
  +(CASE WHEN expected_government IN(0,5) THEN 1 WHEN expected_government=7 THEN 2 WHEN expected_government IN(13,14) THEN -2 ELSE 0 END);
 expected_tech_min:=0;
 IF expected_hydro IN(0,10) AND expected_population>=6 THEN expected_tech_min:=greatest(expected_tech_min,4);END IF;
 IF expected_atmosphere IN(4,7,9) THEN expected_tech_min:=greatest(expected_tech_min,5);END IF;
 IF expected_atmosphere<=3 OR expected_atmosphere BETWEEN 10 AND 12 THEN expected_tech_min:=greatest(expected_tech_min,7);END IF;
 IF expected_atmosphere IN(13,14) AND expected_hydro=10 THEN expected_tech_min:=greatest(expected_tech_min,7);END IF;
 expected_tech:=CASE WHEN expected_population=0 THEN 0 ELSE greatest(expected_tech_min,greatest(0,NEW.technology_roll+expected_tech_dm)) END;
 IF NEW.hydrographics_modifier<>expected_hydro_dm OR NEW.population_modifier<>expected_population_dm OR NEW.technology_modifier<>expected_tech_dm OR NEW.technology_minimum<>expected_tech_min
    OR (p.starport_code,p.size_code,p.atmosphere_code,p.hydrographics_code,p.population_code,p.government_code,p.law_level_code,p.technology_level)
       IS DISTINCT FROM (expected_starport,expected_size,expected_atmosphere,expected_hydro,expected_population,expected_government,expected_law,expected_tech) THEN
  RAISE EXCEPTION 'World generation receipt does not reproduce its Universal World Profile' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER loc_world_generation_receipt_valid BEFORE INSERT ON loc_world_generation_receipt FOR EACH ROW EXECUTE FUNCTION loc_validate_world_generation_receipt();

CREATE FUNCTION loc_validate_world_generation_final() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE generation loc_world_generation_receipt%ROWTYPE;assigned integer;expected integer;
BEGIN
 SELECT * INTO STRICT generation FROM loc_world_generation_receipt WHERE world_generation_receipt_id=NEW.world_generation_receipt_id;
 SELECT count(*) INTO assigned FROM loc_world_trade_code WHERE world_profile_id=NEW.world_profile_id;
 SELECT count(*) INTO expected FROM loc_trade_code WHERE loc_world_profile_qualifies_for_trade_code(NEW.world_profile_id,trade_code_rule_id);
 IF generation.world_profile_id<>NEW.world_profile_id OR NEW.assigned_trade_code_count<>assigned OR assigned<>expected
    OR EXISTS(SELECT 1 FROM loc_trade_code c WHERE loc_world_profile_qualifies_for_trade_code(NEW.world_profile_id,c.trade_code_rule_id)<>(EXISTS(SELECT 1 FROM loc_world_trade_code a WHERE a.world_profile_id=NEW.world_profile_id AND a.trade_code_rule_id=c.trade_code_rule_id))) THEN
  RAISE EXCEPTION 'World generation final receipt requires the exact published trade-code set' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER loc_world_generation_final_valid BEFORE INSERT ON loc_world_generation_final_receipt FOR EACH ROW EXECUTE FUNCTION loc_validate_world_generation_final();

CREATE FUNCTION loc_validate_world_system_detail() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE p loc_world_profile%ROWTYPE;body loc_celestial_body%ROWTYPE;expected_pop_mod integer;expected_exact bigint;expected_belts integer;expected_gas integer;
 naval_eligible boolean;scout_eligible boolean;pirate_eligible boolean;expected_naval boolean;expected_scout boolean;expected_pirate boolean;expected_base text;expected_amber boolean;
BEGIN
 SELECT * INTO STRICT p FROM loc_world_profile WHERE world_profile_id=NEW.world_profile_id AND campaign_id=NEW.campaign_id;
 SELECT * INTO STRICT body FROM loc_celestial_body WHERE location_id=p.location_id AND campaign_id=NEW.campaign_id;
 IF body.system_location_id<>NEW.system_location_id THEN RAISE EXCEPTION 'World system detail receipt has the wrong stellar system' USING ERRCODE='23514';END IF;
 expected_pop_mod:=CASE WHEN p.population_code=0 THEN 0 ELSE greatest(1,NEW.population_multiplier_roll-2) END;
 expected_exact:=expected_pop_mod*(10::bigint^p.population_code);
 IF p.size_code=0 AND NEW.belt_presence_roll<4 THEN expected_belts:=1;
 ELSIF NEW.belt_presence_roll>=4 THEN expected_belts:=greatest(1,NEW.belt_count_roll-3); ELSE expected_belts:=0;END IF;
 expected_gas:=CASE WHEN NEW.gas_presence_roll>=5 THEN greatest(1,NEW.gas_count_roll-2) ELSE 0 END;
 naval_eligible:=p.starport_code IN('A','B');scout_eligible:=p.starport_code IN('A','B','C','D');
 expected_naval:=naval_eligible AND NEW.naval_base_roll>=8;
 pirate_eligible:=p.starport_code<>'A' AND NOT expected_naval;
 expected_scout:=scout_eligible AND NEW.scout_base_roll+(CASE p.starport_code WHEN 'A' THEN -3 WHEN 'B' THEN -2 WHEN 'C' THEN -1 ELSE 0 END)>=7;
 expected_pirate:=pirate_eligible AND NEW.pirate_base_roll>=12;
 expected_base:=CASE WHEN expected_naval AND expected_scout THEN 'A' WHEN expected_scout AND expected_pirate THEN 'G' WHEN expected_naval THEN 'N' WHEN expected_pirate THEN 'P' WHEN expected_scout THEN 'S' ELSE NULL END;
 expected_amber:=p.atmosphere_code>=10 OR p.government_code IN(0,7,10) OR p.law_level_code=0 OR p.law_level_code>=9;
 IF NEW.population_multiplier<>expected_pop_mod OR NEW.exact_population<>expected_exact
    OR (NEW.belt_count_roll IS NOT NULL)<>(NEW.belt_presence_roll>=4) OR NEW.planetoid_belt_count<>expected_belts
    OR (NEW.gas_count_roll IS NOT NULL)<>(NEW.gas_presence_roll>=5) OR NEW.gas_giant_count<>expected_gas
    OR (NEW.naval_base_roll IS NOT NULL)<>naval_eligible OR NEW.naval_base_present<>expected_naval
    OR (NEW.scout_base_roll IS NOT NULL)<>scout_eligible OR NEW.scout_base_present<>expected_scout
    OR (NEW.pirate_base_roll IS NOT NULL)<>pirate_eligible OR NEW.pirate_base_present<>expected_pirate
    OR NEW.base_code IS DISTINCT FROM expected_base OR NEW.amber_zone_candidate<>expected_amber THEN
  RAISE EXCEPTION 'World system detail receipt does not match published PBG, base, or zone-candidate rules' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER loc_world_system_detail_valid BEFORE INSERT ON loc_world_system_detail_receipt FOR EACH ROW EXECUTE FUNCTION loc_validate_world_system_detail();

CREATE FUNCTION loc_reject_world_generation_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'World generation receipts are immutable';END $$;
CREATE TRIGGER loc_hex_generation_receipt_immutable BEFORE UPDATE OR DELETE ON loc_hex_generation_receipt FOR EACH ROW EXECUTE FUNCTION loc_reject_world_generation_mutation();
CREATE TRIGGER loc_world_generation_receipt_immutable BEFORE UPDATE OR DELETE ON loc_world_generation_receipt FOR EACH ROW EXECUTE FUNCTION loc_reject_world_generation_mutation();
CREATE TRIGGER loc_world_generation_final_immutable BEFORE UPDATE OR DELETE ON loc_world_generation_final_receipt FOR EACH ROW EXECUTE FUNCTION loc_reject_world_generation_mutation();
CREATE TRIGGER loc_world_system_detail_immutable BEFORE UPDATE OR DELETE ON loc_world_system_detail_receipt FOR EACH ROW EXECUTE FUNCTION loc_reject_world_generation_mutation();

CREATE FUNCTION loc_guard_generated_world_profile() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF EXISTS(SELECT 1 FROM loc_world_generation_receipt WHERE world_profile_id=OLD.world_profile_id)
    AND (to_jsonb(OLD)-ARRAY['profile_status','ended_at'])<>(to_jsonb(NEW)-ARRAY['profile_status','ended_at']) THEN
  RAISE EXCEPTION 'Generated Universal World Profile mechanics are immutable; create a new revision' USING ERRCODE='23514';
 END IF;RETURN NEW;
END $$;
CREATE TRIGGER loc_generated_world_profile_guard BEFORE UPDATE ON loc_world_profile FOR EACH ROW EXECUTE FUNCTION loc_guard_generated_world_profile();
