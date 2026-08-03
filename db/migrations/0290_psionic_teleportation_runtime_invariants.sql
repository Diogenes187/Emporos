ALTER TABLE cmd_psi_teleportation_receipt
    DROP CONSTRAINT cmd_psi_teleportation_receipt_check5,
    DROP CONSTRAINT cmd_psi_teleportation_receipt_check6;

ALTER TABLE cmd_psi_teleportation_receipt ADD CHECK (
    (within_single_altitude_limit AND within_hourly_altitude_limit)
    OR (
        environmental_hazard_resolution IS NOT NULL
        AND btrim(environmental_hazard_resolution)<>''
    )
);
ALTER TABLE cmd_psi_teleportation_receipt ADD CHECK (
    NOT fast_vehicle_transition OR (
        vehicle_ramming_resolution IS NOT NULL
        AND btrim(vehicle_ramming_resolution)<>''
    )
);

CREATE OR REPLACE FUNCTION cmd_validate_psi_teleportation_receipt()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE activation cmd_psionic_activation_receipt%ROWTYPE;
DECLARE origin loc_actor_position%ROWTYPE;
DECLARE destination loc_actor_position%ROWTYPE;
DECLARE selected_order smallint;
DECLARE maximum_order smallint;
DECLARE disorientation_draw_total integer;
DECLARE disorientation_draw_count integer;
DECLARE invalid_disorientation_draw_count integer;
DECLARE expected_dice_count smallint;
DECLARE expected_die_sides smallint;
DECLARE expected_multiplier smallint;
DECLARE actor_version bigint;
BEGIN
 SELECT * INTO STRICT activation FROM cmd_psionic_activation_receipt
  WHERE command_id=NEW.activation_command_id;
 SELECT * INTO STRICT origin FROM loc_actor_position
  WHERE actor_position_id=NEW.origin_position_id;
 SELECT * INTO STRICT destination FROM loc_actor_position
  WHERE actor_position_id=NEW.destination_position_id;
 SELECT band.display_order INTO STRICT selected_order FROM psi_range_band band
  WHERE band.range_band_rule_id=activation.range_band_rule_id;
 SELECT maximum.display_order,disorientation.duration_dice_count,
        disorientation.duration_die_sides,
        disorientation.duration_multiplier_seconds
 INTO STRICT maximum_order,expected_dice_count,expected_die_sides,
      expected_multiplier
 FROM rule_psi_teleportation_system system
 JOIN psi_range_band maximum ON maximum.range_band_rule_id=
      system.planetary_maximum_range_rule_id
 LEFT JOIN rule_psi_teleportation_disorientation disorientation
   ON disorientation.range_band_rule_id=activation.range_band_rule_id;
 SELECT COALESCE(sum(result),0),count(*),count(*) FILTER (
          WHERE die_sides IS DISTINCT FROM expected_die_sides
             OR draw_order NOT BETWEEN 1 AND expected_dice_count)
 INTO disorientation_draw_total,disorientation_draw_count,
      invalid_disorientation_draw_count
 FROM cmd_random_draw
 WHERE command_id=NEW.activation_command_id
   AND draw_group='psionic_teleport_disorientation';
 SELECT concurrency_version INTO STRICT actor_version FROM actor_actor
  WHERE actor_id=NEW.actor_id AND campaign_id=NEW.campaign_id;
 IF NOT activation.succeeded OR activation.actor_id<>NEW.actor_id
    OR origin.actor_id<>NEW.actor_id OR origin.campaign_id<>NEW.campaign_id
    OR origin.location_id<>NEW.origin_location_id
    OR origin.position_status<>'departed' OR origin.ended_at<>NEW.teleported_at
    OR origin.source_command_id<>NEW.activation_command_id
    OR destination.actor_id<>NEW.actor_id
    OR destination.campaign_id<>NEW.campaign_id
    OR destination.location_id<>NEW.destination_location_id
    OR destination.position_status<>'current'
    OR destination.effective_at<>NEW.teleported_at
    OR destination.source_command_id<>NEW.activation_command_id
    OR actor_version<>NEW.actor_version_after
    OR (NEW.planetary_surface_jump AND selected_order>maximum_order)
    OR disorientation_draw_count<>COALESCE(expected_dice_count,0)
    OR invalid_disorientation_draw_count<>0
    OR (expected_dice_count IS NULL
        AND NEW.disorientation_seconds IS NOT NULL)
    OR (expected_dice_count IS NOT NULL
        AND NEW.disorientation_seconds IS DISTINCT FROM
            disorientation_draw_total*expected_multiplier) THEN
   RAISE EXCEPTION 'Teleportation receipt does not match activation or position state';
 END IF;
 RETURN NEW;
END; $$;

COMMENT ON FUNCTION cmd_validate_psi_teleportation_receipt() IS
    'Enforces exact CE-PSI-016 movement and Very Distant 2d6x10 receipt evidence.';
