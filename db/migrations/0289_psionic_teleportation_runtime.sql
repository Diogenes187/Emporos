ALTER TABLE cmd_random_draw DROP CONSTRAINT cmd_random_draw_draw_group_check;
ALTER TABLE cmd_random_draw ADD CONSTRAINT cmd_random_draw_draw_group_check CHECK (
    draw_group IN (
        'attack','damage','task','occurrence','encounter_type','initiative',
        'psionic_activation','psionic_timing','career_qualification',
        'career_draft','career_survival','career_mishap','career_injury',
        'career_injury_reduction','career_injury_crisis_cost',
        'career_commission','career_advancement','career_training',
        'career_aging','career_reenlistment','career_benefit',
        'career_benefit_ship_shares','career_aging_crisis_cost',
        'career_medical_employer','career_anagathic_cost',
        'career_anagathic_survival','environment_damage',
        'blind_target','explosion_damage','explosion_dodge',
        'combat_scatter','combat_nearest_tie',
        'grapple_challenger','grapple_opponent','grapple_throw_damage',
        'thrown_scatter_direction','telekinetic_attack',
        'telekinetic_damage','psionic_assault_defense',
        'psionic_assault_damage','psionic_teleport_disorientation'
    )
);

CREATE TABLE cmd_psi_teleportation_receipt (
    activation_command_id bigint PRIMARY KEY REFERENCES
        cmd_psionic_activation_receipt(command_id),
    actor_id bigint NOT NULL,
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    origin_position_id bigint NOT NULL REFERENCES
        loc_actor_position(actor_position_id),
    destination_position_id bigint NOT NULL UNIQUE REFERENCES
        loc_actor_position(actor_position_id),
    origin_location_id bigint NOT NULL,
    destination_location_id bigint NOT NULL,
    destination_knowledge_kind text NOT NULL CHECK (
        destination_knowledge_kind IN (
            'personal_visit','distant_view','telepathic_implant','clairvoyance'
        )
    ),
    destination_knowledge_evidence text NOT NULL CHECK (
        btrim(destination_knowledge_evidence)<>''
    ),
    load_kind text NOT NULL CHECK (
        load_kind IN ('unclothed','light','moderate','heavy')
    ),
    planetary_surface_jump boolean NOT NULL,
    altitude_change_metres numeric NOT NULL,
    hourly_cumulative_altitude_metres numeric NOT NULL CHECK (
        hourly_cumulative_altitude_metres>=abs(altitude_change_metres)
    ),
    within_single_altitude_limit boolean NOT NULL,
    within_hourly_altitude_limit boolean NOT NULL,
    temperature_change_celsius numeric NOT NULL,
    environmental_hazard_resolution text,
    fast_vehicle_transition boolean NOT NULL,
    vehicle_ramming_resolution text,
    disorientation_seconds integer CHECK (
        disorientation_seconds IS NULL OR disorientation_seconds BETWEEN 20 AND 120
    ),
    actor_version_before bigint NOT NULL,
    actor_version_after bigint NOT NULL CHECK (
        actor_version_after=actor_version_before+1
    ),
    teleported_at timestamptz NOT NULL,
    FOREIGN KEY (actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    FOREIGN KEY (origin_location_id,campaign_id)
        REFERENCES loc_location(location_id,campaign_id),
    FOREIGN KEY (destination_location_id,campaign_id)
        REFERENCES loc_location(location_id,campaign_id),
    CHECK (
        within_single_altitude_limit=(abs(altitude_change_metres)<=400)
    ),
    CHECK (
        within_hourly_altitude_limit=(hourly_cumulative_altitude_metres<=600)
    ),
    CHECK (
        temperature_change_celsius=(-altitude_change_metres*2.5/1000)
    ),
    CHECK (
        (within_single_altitude_limit AND within_hourly_altitude_limit)
        OR btrim(environmental_hazard_resolution)<>''
    ),
    CHECK (
        NOT fast_vehicle_transition OR btrim(vehicle_ramming_resolution)<>''
    )
);

CREATE FUNCTION cmd_validate_psi_teleportation_receipt()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE activation cmd_psionic_activation_receipt%ROWTYPE;
DECLARE origin loc_actor_position%ROWTYPE;
DECLARE destination loc_actor_position%ROWTYPE;
DECLARE selected_order smallint;
DECLARE maximum_order smallint;
DECLARE expected_disorientation integer;
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
 SELECT band.display_order INTO STRICT maximum_order
  FROM rule_psi_teleportation_system system
  JOIN psi_range_band band ON band.range_band_rule_id=
       system.planetary_maximum_range_rule_id;
 SELECT sum(result)*10 INTO expected_disorientation FROM cmd_random_draw
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
    OR expected_disorientation IS DISTINCT FROM NEW.disorientation_seconds THEN
   RAISE EXCEPTION 'Teleportation receipt does not match activation or position state';
 END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER cmd_psi_teleportation_receipt_valid
BEFORE INSERT ON cmd_psi_teleportation_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_validate_psi_teleportation_receipt();

CREATE FUNCTION cmd_reject_psi_teleportation_receipt_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Teleportation receipts are immutable'; END; $$;
CREATE TRIGGER cmd_psi_teleportation_receipt_immutable
BEFORE UPDATE OR DELETE ON cmd_psi_teleportation_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_psi_teleportation_receipt_mutation();

CREATE FUNCTION loc_validate_teleport_position_audit()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.source_command_id IS NULL THEN RETURN NULL; END IF;
 PERFORM 1 FROM cmd_command command
  WHERE command.command_id=NEW.source_command_id
    AND command.command_type='activate_psionic_power';
 IF NOT FOUND THEN RETURN NULL; END IF;
 PERFORM 1 FROM cmd_psi_teleportation_receipt receipt
  WHERE receipt.activation_command_id=NEW.source_command_id
    AND (receipt.origin_position_id=NEW.actor_position_id
         OR receipt.destination_position_id=NEW.actor_position_id);
 IF NOT FOUND THEN
   RAISE EXCEPTION 'Teleport position transition requires immutable receipt';
 END IF;
 RETURN NULL;
END; $$;
CREATE CONSTRAINT TRIGGER loc_teleport_position_audit
AFTER INSERT OR UPDATE ON loc_actor_position
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
EXECUTE FUNCTION loc_validate_teleport_position_audit();

COMMENT ON TABLE cmd_psi_teleportation_receipt IS
    'Immutable CE-PSI-016 movement, destination-image, conservation, and hazard snapshot.';
