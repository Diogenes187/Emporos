CREATE FUNCTION enc_guard_extreme_range_authorization()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP='DELETE' THEN
        RAISE EXCEPTION 'Extreme-range authorizations are retained';
    END IF;
    IF (
        NEW.encounter_id,NEW.round_number,NEW.attacker_actor_id,
        NEW.target_actor_id,NEW.weapon_rule_id,NEW.attack_profile_code,
        NEW.rest_reference,NEW.line_of_sight,NEW.skill_level,
        NEW.attacker_metres_moved,NEW.energy_weapon,NEW.vehicle_id,
        NEW.vehicle_combat_round_id,NEW.venc_vehicle_id,
        NEW.vehicle_movement_status,NEW.vehicle_speed_kph
    ) IS DISTINCT FROM (
        OLD.encounter_id,OLD.round_number,OLD.attacker_actor_id,
        OLD.target_actor_id,OLD.weapon_rule_id,OLD.attack_profile_code,
        OLD.rest_reference,OLD.line_of_sight,OLD.skill_level,
        OLD.attacker_metres_moved,OLD.energy_weapon,OLD.vehicle_id,
        OLD.vehicle_combat_round_id,OLD.venc_vehicle_id,
        OLD.vehicle_movement_status,OLD.vehicle_speed_kph
    ) OR OLD.authorization_status<>'available'
      OR NEW.authorization_status NOT IN ('consumed','cancelled') THEN
        RAISE EXCEPTION 'Extreme-range authorization facts are immutable';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER enc_extreme_range_authorization_guard
BEFORE UPDATE OR DELETE ON enc_personal_extreme_range_authorization
FOR EACH ROW EXECUTE FUNCTION enc_guard_extreme_range_authorization();

CREATE FUNCTION cmd_validate_extreme_range_authorization()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE auth enc_personal_extreme_range_authorization%ROWTYPE;
DECLARE command cmd_command%ROWTYPE;
BEGIN
    SELECT * INTO STRICT auth
      FROM enc_personal_extreme_range_authorization
     WHERE authorization_id=NEW.authorization_id;
    SELECT * INTO STRICT command FROM cmd_command
     WHERE command_id=NEW.command_id;
    IF command.command_type<>'authorize_extreme_range'
       OR NOT EXISTS (
           SELECT 1 FROM enc_encounter encounter
           JOIN camp_campaign campaign
             ON campaign.campaign_id=encounter.campaign_id
          WHERE encounter.encounter_id=auth.encounter_id
            AND campaign.owner_reference=command.initiator_reference
       )
       OR NOT EXISTS (
           SELECT 1 FROM enc_personal_combat combat
           JOIN enc_personal_combatant attacker
             ON attacker.encounter_id=combat.encounter_id
            AND attacker.actor_id=auth.attacker_actor_id
           JOIN enc_personal_combatant target
             ON target.encounter_id=combat.encounter_id
            AND target.actor_id=auth.target_actor_id
          WHERE combat.encounter_id=auth.encounter_id
            AND combat.current_round=auth.round_number
            AND attacker.metres_moved_this_round=0
       )
       OR NOT EXISTS (
           SELECT 1 FROM inv_weapon_attack_mode mode
           JOIN combat_attack_profile profile
             ON profile.attack_profile_code=mode.attack_profile_code
           JOIN actor_skill skill
             ON skill.actor_id=auth.attacker_actor_id
            AND skill.skill_rule_id=COALESCE(
                mode.required_skill_rule_id,profile.required_skill_rule_id)
           JOIN rule_rule distant
             ON distant.rule_code='combat.range.distant'
           JOIN combat_attack_profile_difficulty difficulty
             ON difficulty.attack_profile_code=mode.attack_profile_code
            AND difficulty.range_band_rule_id=distant.rule_id
            AND difficulty.permitted
          WHERE mode.item_rule_id=auth.weapon_rule_id
            AND mode.attack_profile_code=auth.attack_profile_code
            AND skill.skill_level=auth.skill_level
            AND skill.skill_level>=3
       ) THEN
        RAISE EXCEPTION 'Extreme-range authorization lacks referee or rule facts';
    END IF;
    IF auth.vehicle_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM venc_vehicle engaged
        JOIN venc_engagement engagement
          ON engagement.vehicle_engagement_id=engaged.vehicle_engagement_id
        JOIN vehicle_crew_assignment crew
          ON crew.vehicle_id=engaged.vehicle_id
         AND crew.actor_id=auth.attacker_actor_id
         AND crew.duty_status='active'
       WHERE engaged.venc_vehicle_id=auth.venc_vehicle_id
         AND engaged.vehicle_id=auth.vehicle_id
         AND engagement.encounter_id=auth.encounter_id
    ) THEN
        RAISE EXCEPTION 'Extreme-range vehicle is not the firer platform';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER cmd_extreme_range_authorization_validate
BEFORE INSERT ON cmd_personal_extreme_range_authorization_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_validate_extreme_range_authorization();

CREATE FUNCTION enc_validate_extreme_range_attack()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.extreme_range AND NOT EXISTS (
        SELECT 1 FROM enc_personal_extreme_range_authorization auth
         WHERE auth.authorization_id=NEW.extreme_range_authorization_id
           AND auth.authorization_status='available'
           AND (
             auth.encounter_id,auth.round_number,auth.attacker_actor_id,
             auth.target_actor_id,auth.weapon_rule_id,auth.attack_profile_code,
             auth.rest_reference,auth.line_of_sight,auth.skill_level,
             auth.attacker_metres_moved,auth.energy_weapon,auth.vehicle_id,
             auth.vehicle_combat_round_id,auth.venc_vehicle_id,
             auth.vehicle_movement_status,auth.vehicle_speed_kph
           )=(
             NEW.encounter_id,NEW.round_number,NEW.attacker_actor_id,
             NEW.target_actor_id,NEW.weapon_rule_id,NEW.attack_profile_code,
             NEW.extreme_range_rest_reference,
             NEW.extreme_range_line_of_sight,
             NEW.extreme_range_skill_level,
             NEW.extreme_range_attacker_metres_moved,
             NEW.extreme_range_energy_weapon,NEW.extreme_range_vehicle_id,
             NEW.extreme_range_vehicle_combat_round_id,
             NEW.extreme_range_venc_vehicle_id,
             NEW.extreme_range_vehicle_movement_status,
             NEW.extreme_range_vehicle_speed_kph
           )
    ) THEN
        RAISE EXCEPTION 'Extreme-range attack does not match authorization';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER enc_personal_attack_extreme_range_validate
BEFORE INSERT ON enc_personal_attack
FOR EACH ROW EXECUTE FUNCTION enc_validate_extreme_range_attack();

CREATE FUNCTION enc_guard_extreme_range_attack_snapshot()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF (
        NEW.extreme_range,NEW.extreme_range_rest_reference,
        NEW.extreme_range_line_of_sight,NEW.extreme_range_skill_level,
        NEW.extreme_range_attacker_metres_moved,
        NEW.extreme_range_attack_modifier,NEW.extreme_range_energy_weapon,
        NEW.extreme_range_vehicle_id,
        NEW.extreme_range_vehicle_combat_round_id,
        NEW.extreme_range_venc_vehicle_id,
        NEW.extreme_range_vehicle_movement_status,
        NEW.extreme_range_vehicle_speed_kph,
        NEW.extreme_range_authorization_id
    ) IS DISTINCT FROM (
        OLD.extreme_range,OLD.extreme_range_rest_reference,
        OLD.extreme_range_line_of_sight,OLD.extreme_range_skill_level,
        OLD.extreme_range_attacker_metres_moved,
        OLD.extreme_range_attack_modifier,OLD.extreme_range_energy_weapon,
        OLD.extreme_range_vehicle_id,
        OLD.extreme_range_vehicle_combat_round_id,
        OLD.extreme_range_venc_vehicle_id,
        OLD.extreme_range_vehicle_movement_status,
        OLD.extreme_range_vehicle_speed_kph,
        OLD.extreme_range_authorization_id
    ) THEN
        RAISE EXCEPTION 'Extreme-range attack snapshots are immutable';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER enc_personal_attack_extreme_range_snapshot_immutable
BEFORE UPDATE ON enc_personal_attack
FOR EACH ROW EXECUTE FUNCTION enc_guard_extreme_range_attack_snapshot();

CREATE OR REPLACE FUNCTION cmd_validate_extreme_range_receipt()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE attack enc_personal_attack%ROWTYPE;
DECLARE resolved cmd_attack_receipt%ROWTYPE;
BEGIN
    SELECT * INTO STRICT attack FROM enc_personal_attack
     WHERE personal_attack_id=NEW.personal_attack_id;
    SELECT * INTO STRICT resolved FROM cmd_attack_receipt
     WHERE command_id=NEW.command_id;
    IF NOT attack.extreme_range
       OR resolved.personal_attack_id<>attack.personal_attack_id
       OR NEW.energy_reduction_applied<>attack.extreme_range_energy_weapon
       OR resolved.raw_damage<>NEW.damage_after_energy_reduction
       OR resolved.extreme_range_energy_reduction<>
          NEW.damage_before_energy_reduction-NEW.damage_after_energy_reduction
    THEN
        RAISE EXCEPTION 'Extreme-range receipt does not match attack snapshots';
    END IF;
    RETURN NEW;
END;
$$;
