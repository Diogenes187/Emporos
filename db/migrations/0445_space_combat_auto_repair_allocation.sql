INSERT INTO rule_interpretation(rule_id,interpretation_type,decision_register_entry,rationale)
SELECT rule_id,'agreed_interpretation','CE-SC-011',
 'Raymond approved one autonomous repair check for one complete repair-drone installation and two checks for two or more complete installations; drones allocated to assist crew cannot also make autonomous checks that turn.'
FROM rule_rule WHERE rule_code='combat.space.battlefield-repair';

CREATE TABLE rule_space_combat_auto_repair(
 rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),required_hangar_option_code text NOT NULL REFERENCES rule_ship_hangar_option(hangar_option_code),
 required_software_code text NOT NULL REFERENCES rule_ship_software(software_code),minimum_installations smallint NOT NULL CHECK(minimum_installations=1),
 maximum_checks_per_round smallint NOT NULL CHECK(maximum_checks_per_round=2),check_dice_count smallint NOT NULL CHECK(check_dice_count=2),
 check_die_sides smallint NOT NULL CHECK(check_die_sides=6),standard_check_modifier smallint NOT NULL CHECK(standard_check_modifier=1),
 assist_excludes_autonomous_checks boolean NOT NULL
);
INSERT INTO rule_space_combat_auto_repair
SELECT rule_id,'repair-drones','auto-repair',1,2,2,6,1,true FROM rule_rule WHERE rule_code='combat.space.battlefield-repair';

CREATE TABLE senc_repair_drone_round_allocation(
 repair_drone_round_allocation_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 space_combat_round_id bigint NOT NULL,engagement_id bigint NOT NULL,campaign_id bigint NOT NULL,round_number integer NOT NULL CHECK(round_number>0),
 senc_vessel_id bigint NOT NULL,ship_id bigint NOT NULL,allocation_mode text NOT NULL CHECK(allocation_mode IN('autonomous','assist')),
 installed_drone_sets smallint NOT NULL CHECK(installed_drone_sets>0),autonomous_check_capacity smallint NOT NULL CHECK(autonomous_check_capacity BETWEEN 0 AND 2),
 assisted_action_id bigint,recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(space_combat_round_id,engagement_id,campaign_id) REFERENCES senc_round(space_combat_round_id,engagement_id,campaign_id),
 FOREIGN KEY(senc_vessel_id,engagement_id,campaign_id) REFERENCES senc_vessel(senc_vessel_id,engagement_id,campaign_id),
 FOREIGN KEY(ship_id,campaign_id) REFERENCES ship_ship(ship_id,campaign_id),
 FOREIGN KEY(assisted_action_id,engagement_id,campaign_id) REFERENCES senc_action(space_combat_action_id,engagement_id,campaign_id),
 UNIQUE(space_combat_round_id,senc_vessel_id),
 CHECK((allocation_mode='assist')=(assisted_action_id IS NOT NULL)),
 CHECK((allocation_mode='autonomous' AND autonomous_check_capacity=least(installed_drone_sets,2))
  OR (allocation_mode='assist' AND autonomous_check_capacity=0))
);
CREATE FUNCTION senc_validate_repair_drone_allocation() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE vessel_ship bigint; class_id bigint; actual_round integer; installations integer; assisted record;
BEGIN
 SELECT vessel.ship_id,ship.ship_class_rule_id INTO STRICT vessel_ship,class_id FROM senc_vessel vessel JOIN ship_ship ship USING(ship_id)
 WHERE vessel.senc_vessel_id=NEW.senc_vessel_id AND vessel.engagement_id=NEW.engagement_id AND vessel.campaign_id=NEW.campaign_id;
 SELECT round_number INTO STRICT actual_round FROM senc_round WHERE space_combat_round_id=NEW.space_combat_round_id;
 SELECT coalesce(sum(installation_count),0) INTO installations FROM ship_class_hangar_option
  WHERE ship_class_rule_id=class_id AND hangar_option_code='repair-drones';
 IF vessel_ship<>NEW.ship_id OR actual_round<>NEW.round_number OR installations<1 OR NEW.installed_drone_sets<>installations
  OR NOT EXISTS(SELECT 1 FROM ship_class_software WHERE ship_class_rule_id=class_id AND software_code='auto-repair') THEN
  RAISE EXCEPTION 'Repair-drone allocation requires current vessel, complete drone installation, and Auto-Repair software' USING ERRCODE='23514'; END IF;
 IF NEW.allocation_mode='assist' THEN
  SELECT action.action_code,turn.senc_vessel_id,action.space_combat_round_id INTO assisted FROM senc_action action JOIN senc_crew_turn turn USING(crew_turn_id)
   WHERE action.space_combat_action_id=NEW.assisted_action_id;
  IF assisted.action_code<>'repair-system' OR assisted.senc_vessel_id<>NEW.senc_vessel_id OR assisted.space_combat_round_id<>NEW.space_combat_round_id THEN
   RAISE EXCEPTION 'Repair drones may assist only a same-vessel Repair Damaged System action this round' USING ERRCODE='23514'; END IF;
 END IF; RETURN NEW;
END $$;
CREATE TRIGGER senc_repair_drone_round_allocation_valid BEFORE INSERT ON senc_repair_drone_round_allocation
FOR EACH ROW EXECUTE FUNCTION senc_validate_repair_drone_allocation();
CREATE FUNCTION senc_reject_repair_drone_allocation_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Repair-drone round allocations are immutable'; END $$;
CREATE TRIGGER senc_repair_drone_round_allocation_immutable BEFORE UPDATE OR DELETE ON senc_repair_drone_round_allocation
FOR EACH ROW EXECUTE FUNCTION senc_reject_repair_drone_allocation_mutation();
