CREATE TABLE rule_personal_extreme_range (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    base_range_rule_id bigint NOT NULL REFERENCES combat_range_band(rule_id),
    additional_attack_modifier smallint NOT NULL CHECK (
        additional_attack_modifier=-2
    ),
    minimum_skill_level smallint NOT NULL CHECK (minimum_skill_level=3),
    requires_line_of_sight boolean NOT NULL CHECK (requires_line_of_sight),
    requires_stationary_firer boolean NOT NULL CHECK (
        requires_stationary_firer
    ),
    requires_firing_rest boolean NOT NULL CHECK (requires_firing_rest),
    vehicle_requires_stationary boolean NOT NULL CHECK (
        vehicle_requires_stationary
    ),
    energy_damage_divisor smallint NOT NULL CHECK (energy_damage_divisor=2),
    energy_damage_rounding text NOT NULL CHECK (
        energy_damage_rounding='up'
    ),
    permits_kill_aim boolean NOT NULL CHECK (permits_kill_aim)
);

CREATE TABLE enc_personal_extreme_range_authorization (
    authorization_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    encounter_id bigint NOT NULL REFERENCES enc_personal_combat(encounter_id),
    round_number integer NOT NULL CHECK (round_number>0),
    attacker_actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    target_actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    weapon_rule_id bigint NOT NULL REFERENCES inv_weapon_definition(item_rule_id),
    attack_profile_code text NOT NULL REFERENCES combat_attack_profile,
    rest_reference text NOT NULL CHECK (btrim(rest_reference)<>''),
    line_of_sight boolean NOT NULL CHECK (line_of_sight),
    skill_level smallint NOT NULL CHECK (skill_level>=3),
    attacker_metres_moved numeric NOT NULL CHECK (attacker_metres_moved=0),
    energy_weapon boolean NOT NULL,
    vehicle_id bigint REFERENCES vehicle_vehicle(vehicle_id),
    vehicle_combat_round_id bigint,
    venc_vehicle_id bigint,
    vehicle_movement_status text,
    vehicle_speed_kph numeric,
    authorization_status text NOT NULL DEFAULT 'available' CHECK (
        authorization_status IN ('available','consumed','cancelled')
    ),
    FOREIGN KEY (vehicle_combat_round_id,venc_vehicle_id)
        REFERENCES venc_vehicle_round_state(
            vehicle_combat_round_id,venc_vehicle_id
        ),
    CHECK (
        (vehicle_id IS NULL AND vehicle_combat_round_id IS NULL
         AND venc_vehicle_id IS NULL AND vehicle_movement_status IS NULL
         AND vehicle_speed_kph IS NULL)
        OR
        (vehicle_id IS NOT NULL AND vehicle_combat_round_id IS NOT NULL
         AND venc_vehicle_id IS NOT NULL
         AND vehicle_movement_status='stationary' AND vehicle_speed_kph=0)
    ),
    UNIQUE (encounter_id,round_number,attacker_actor_id,target_actor_id)
);

CREATE TABLE cmd_personal_extreme_range_authorization_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    authorization_id bigint NOT NULL UNIQUE
        REFERENCES enc_personal_extreme_range_authorization(authorization_id)
);

ALTER TABLE enc_personal_attack
    ADD COLUMN extreme_range boolean NOT NULL DEFAULT false,
    ADD COLUMN extreme_range_rest_reference text,
    ADD COLUMN extreme_range_line_of_sight boolean,
    ADD COLUMN extreme_range_skill_level smallint,
    ADD COLUMN extreme_range_attacker_metres_moved numeric,
    ADD COLUMN extreme_range_attack_modifier smallint NOT NULL DEFAULT 0,
    ADD COLUMN extreme_range_energy_weapon boolean NOT NULL DEFAULT false,
    ADD COLUMN extreme_range_vehicle_id bigint REFERENCES vehicle_vehicle(vehicle_id),
    ADD COLUMN extreme_range_vehicle_combat_round_id bigint,
    ADD COLUMN extreme_range_venc_vehicle_id bigint,
    ADD COLUMN extreme_range_vehicle_movement_status text,
    ADD COLUMN extreme_range_vehicle_speed_kph numeric,
    ADD COLUMN extreme_range_authorization_id bigint UNIQUE
        REFERENCES enc_personal_extreme_range_authorization(authorization_id),
    ADD CONSTRAINT enc_personal_attack_extreme_vehicle_state_fk
        FOREIGN KEY (
            extreme_range_vehicle_combat_round_id,
            extreme_range_venc_vehicle_id
        ) REFERENCES venc_vehicle_round_state(
            vehicle_combat_round_id,venc_vehicle_id
        ),
    ADD CONSTRAINT enc_personal_attack_extreme_range_check CHECK (
        (
            NOT extreme_range
            AND extreme_range_rest_reference IS NULL
            AND extreme_range_line_of_sight IS NULL
            AND extreme_range_skill_level IS NULL
            AND extreme_range_attacker_metres_moved IS NULL
            AND extreme_range_attack_modifier=0
            AND NOT extreme_range_energy_weapon
            AND extreme_range_vehicle_id IS NULL
            AND extreme_range_vehicle_combat_round_id IS NULL
            AND extreme_range_venc_vehicle_id IS NULL
            AND extreme_range_vehicle_movement_status IS NULL
            AND extreme_range_vehicle_speed_kph IS NULL
            AND extreme_range_authorization_id IS NULL
        )
        OR (
            extreme_range
            AND btrim(extreme_range_rest_reference)<>''
            AND extreme_range_line_of_sight
            AND extreme_range_skill_level>=3
            AND extreme_range_attacker_metres_moved=0
            AND extreme_range_attack_modifier=-2
            AND extreme_range_authorization_id IS NOT NULL
            AND (
                (
                    extreme_range_vehicle_id IS NULL
                    AND extreme_range_vehicle_combat_round_id IS NULL
                    AND extreme_range_venc_vehicle_id IS NULL
                    AND extreme_range_vehicle_movement_status IS NULL
                    AND extreme_range_vehicle_speed_kph IS NULL
                )
                OR (
                    extreme_range_vehicle_id IS NOT NULL
                    AND extreme_range_vehicle_combat_round_id IS NOT NULL
                    AND extreme_range_venc_vehicle_id IS NOT NULL
                    AND extreme_range_vehicle_movement_status='stationary'
                    AND extreme_range_vehicle_speed_kph=0
                )
            )
        )
    );

CREATE TABLE cmd_personal_extreme_range_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_attack_receipt(command_id),
    personal_attack_id bigint NOT NULL UNIQUE
        REFERENCES enc_personal_attack(personal_attack_id),
    energy_reduction_applied boolean NOT NULL,
    damage_before_energy_reduction integer NOT NULL CHECK (
        damage_before_energy_reduction>=0
    ),
    damage_after_energy_reduction integer NOT NULL CHECK (
        damage_after_energy_reduction>=0
    ),
    CHECK (
        (energy_reduction_applied
         AND damage_after_energy_reduction=
             (damage_before_energy_reduction+1)/2)
        OR
        (NOT energy_reduction_applied
         AND damage_after_energy_reduction=
             damage_before_energy_reduction)
    )
);

ALTER TABLE cmd_attack_receipt
    ADD COLUMN extreme_range_energy_reduction integer NOT NULL DEFAULT 0
        CHECK (extreme_range_energy_reduction>=0);
ALTER TABLE cmd_attack_receipt
    DROP CONSTRAINT cmd_attack_receipt_damage_components_check;
ALTER TABLE cmd_attack_receipt
    ADD CONSTRAINT cmd_attack_receipt_damage_components_check CHECK (
        (
            hit AND raw_damage=
                rolled_damage+effect_damage+kill_aim_damage_bonus+
                weapon_flat_damage_bonus+burst_extra_damage_flat+
                panic_extra_damage_flat-extreme_range_energy_reduction
        )
        OR (
            NOT hit AND rolled_damage=0 AND effect_damage=0
            AND kill_aim_damage_bonus=0 AND weapon_flat_damage_bonus=0
            AND burst_extra_damage_flat=0 AND panic_extra_damage_flat=0
            AND extreme_range_energy_reduction=0
            AND raw_damage=0 AND penetrating_damage=0
        )
    );

CREATE FUNCTION cmd_reject_extreme_range_receipt_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Extreme-range receipts are immutable'; END;
$$;
CREATE TRIGGER cmd_personal_extreme_range_receipt_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_extreme_range_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_extreme_range_receipt_mutation();
CREATE TRIGGER cmd_personal_extreme_range_authorization_receipt_immutable
BEFORE UPDATE OR DELETE
ON cmd_personal_extreme_range_authorization_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_extreme_range_receipt_mutation();

CREATE FUNCTION cmd_validate_extreme_range_receipt()
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
       OR resolved.raw_damage<>NEW.damage_after_energy_reduction THEN
        RAISE EXCEPTION 'Extreme-range receipt does not match attack snapshots';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER cmd_personal_extreme_range_receipt_validate
BEFORE INSERT ON cmd_personal_extreme_range_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_validate_extreme_range_receipt();

COMMENT ON TABLE rule_personal_extreme_range IS
    'Published Extreme Range mechanics plus agreed CE-COMBAT-007 boundary.';
COMMENT ON COLUMN enc_personal_attack.extreme_range_rest_reference IS
    'Immutable referee-auditable firing-rest declaration snapshot.';

ALTER TABLE cmd_command DROP CONSTRAINT cmd_command_command_type_check;
ALTER TABLE cmd_command ADD CONSTRAINT cmd_command_command_type_check CHECK (
    command_type IN (
        'resolve_personal_attack','apply_personal_damage','create_encounter',
        'transition_encounter_mode','add_encounter_participant',
        'set_encounter_attitude','attempt_attitude_influence',
        'set_animal_reaction_context','resolve_animal_reaction',
        'check_starship_encounter','initialize_personal_combat',
        'spend_personal_action','declare_personal_reaction',
        'complete_personal_turn','advance_personal_combat_round',
        'declare_personal_attack','begin_personal_turn',
        'hasten_personal_combatant','delay_personal_turn',
        'resume_delayed_personal_turn','forfeit_delayed_personal_turn',
        'aim_personal_attack','change_personal_stance','set_personal_cover',
        'move_personal_combatant','aim_personal_attack_for_kill',
        'advance_weapon_reload','activate_psionic_power',
        'recover_psionic_strength','set_telepathic_shield',
        'attempt_career_entry','resolve_failed_career_entry',
        'apply_career_basic_training','attempt_career_survival',
        'apply_career_rank_zero_award','resolve_survival_mishap',
        'determine_career_injury','apply_career_injury',
        'determine_injury_crisis_cost','resolve_injury_crisis',
        'resolve_career_rank_attempt','apply_career_term_training',
        'complete_career_term','determine_career_aging','apply_career_aging',
        'determine_career_reenlistment','decide_career_reenlistment',
        'initialize_career_muster','roll_career_benefit',
        'resolve_career_weapon_benefit','finish_character_creation',
        'determine_aging_crisis_cost','resolve_aging_crisis',
        'resolve_career_medical_care','declare_career_anagathics',
        'update_character_final_details','assign_actor_species',
        'resolve_species_great_leap','move_species_flyer',
        'resolve_actor_task','resolve_species_hive_mentality',
        'resolve_species_naturally_curious',
        'evaluate_species_low_light_visibility',
        'advance_species_environmental_exposure',
        'set_battlefield_communication','apply_personal_initiative_support',
        'set_personal_battlefield_conditions',
        'declare_personal_explosion',
        'declare_personal_explosion_reaction',
        'resolve_personal_explosion','authorize_extreme_range'
    )
);
