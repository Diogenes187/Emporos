CREATE OR REPLACE FUNCTION enc_validate_extreme_range_attack()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.extreme_range AND NOT EXISTS (
        SELECT 1 FROM enc_personal_extreme_range_authorization auth
         WHERE auth.authorization_id=NEW.extreme_range_authorization_id
           AND auth.authorization_status='available'
           AND ROW(
             auth.encounter_id,auth.round_number,auth.attacker_actor_id,
             auth.target_actor_id,auth.weapon_rule_id,auth.attack_profile_code,
             auth.rest_reference,auth.line_of_sight,auth.skill_level,
             auth.attacker_metres_moved,auth.energy_weapon,auth.vehicle_id,
             auth.vehicle_combat_round_id,auth.venc_vehicle_id,
             auth.vehicle_movement_status,auth.vehicle_speed_kph
           ) IS NOT DISTINCT FROM ROW(
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

COMMENT ON FUNCTION enc_validate_extreme_range_attack() IS
    'Null-safe equality between authorization and immutable attack snapshots.';
