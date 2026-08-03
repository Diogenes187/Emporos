CREATE TABLE rule_personal_battlefield_condition (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    condition_code text NOT NULL UNIQUE CHECK (
        condition_code IN (
            'low-light','complete-darkness','smoke','thick-smoke',
            'extreme-weather-visibility','extreme-weather-interference'
        )
    ),
    condition_group text NOT NULL CHECK (
        condition_group IN ('light','obscurant','weather')
    ),
    ranged_attack_modifier integer NOT NULL CHECK (
        ranged_attack_modifier IN (-1,-2,-4)
    ),
    doubled_for_laser_weapons boolean NOT NULL,
    sensor_avoidable boolean NOT NULL
);

CREATE TABLE rule_personal_battlefield_sensor (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    sensor_code text NOT NULL UNIQUE CHECK (
        sensor_code IN (
            'bioscanner','infra-red','densitometer',
            'electromagnetic-detector','laser-assisted-targeting',
            'light-intensification','motion-sensor',
            'neural-activity-sensor'
        )
    ),
    qualifies_for_weather_visibility boolean NOT NULL,
    negates_darkness boolean NOT NULL,
    negates_smoke_concealment boolean NOT NULL,
    negates_soft_cover boolean NOT NULL,
    can_be_jammed boolean NOT NULL
);

CREATE TABLE actor_personal_battlefield_sensor (
    actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    campaign_id bigint NOT NULL,
    sensor_rule_id bigint NOT NULL
        REFERENCES rule_personal_battlefield_sensor(rule_id),
    jammed boolean NOT NULL DEFAULT false,
    PRIMARY KEY (actor_id,sensor_rule_id),
    FOREIGN KEY (actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id)
);

CREATE TABLE enc_personal_battlefield_condition (
    encounter_id bigint PRIMARY KEY
        REFERENCES enc_personal_combat(encounter_id),
    light_code text NOT NULL DEFAULT 'normal' CHECK (
        light_code IN ('normal','low-light','complete-darkness')
    ),
    obscurant_code text NOT NULL DEFAULT 'none' CHECK (
        obscurant_code IN ('none','smoke','thick-smoke')
    ),
    extreme_weather boolean NOT NULL DEFAULT false,
    concurrency_version bigint NOT NULL DEFAULT 0 CHECK (
        concurrency_version>=0
    )
);

INSERT INTO enc_personal_battlefield_condition (encounter_id)
SELECT encounter_id FROM enc_personal_combat;

CREATE FUNCTION enc_seed_personal_battlefield_condition()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO enc_personal_battlefield_condition (encounter_id)
    VALUES (NEW.encounter_id);
    RETURN NEW;
END;
$$;
CREATE TRIGGER enc_personal_combat_seed_battlefield_condition
AFTER INSERT ON enc_personal_combat
FOR EACH ROW EXECUTE FUNCTION enc_seed_personal_battlefield_condition();

ALTER TABLE enc_personal_attack
    ADD COLUMN battlefield_light_code text NOT NULL DEFAULT 'normal' CHECK (
        battlefield_light_code IN (
            'normal','low-light','complete-darkness'
        )
    ),
    ADD COLUMN battlefield_obscurant_code text NOT NULL DEFAULT 'none' CHECK (
        battlefield_obscurant_code IN ('none','smoke','thick-smoke')
    ),
    ADD COLUMN battlefield_extreme_weather boolean NOT NULL DEFAULT false,
    ADD COLUMN battlefield_sensor_rule_id bigint
        REFERENCES rule_personal_battlefield_sensor(rule_id),
    ADD COLUMN battlefield_sensor_jammed boolean,
    ADD COLUMN environmental_attack_modifier integer NOT NULL DEFAULT 0 CHECK (
        environmental_attack_modifier BETWEEN -10 AND 0
    ),
    ADD CONSTRAINT enc_personal_attack_sensor_snapshot_check CHECK (
        (battlefield_sensor_rule_id IS NULL
         AND battlefield_sensor_jammed IS NULL)
        OR (battlefield_sensor_rule_id IS NOT NULL
            AND battlefield_sensor_jammed IS NOT NULL)
    );

CREATE FUNCTION enc_reject_battlefield_attack_snapshot_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF (NEW.battlefield_light_code,NEW.battlefield_obscurant_code,
        NEW.battlefield_extreme_weather,NEW.battlefield_sensor_rule_id,
        NEW.battlefield_sensor_jammed,NEW.environmental_attack_modifier)
       IS DISTINCT FROM
       (OLD.battlefield_light_code,OLD.battlefield_obscurant_code,
        OLD.battlefield_extreme_weather,OLD.battlefield_sensor_rule_id,
        OLD.battlefield_sensor_jammed,OLD.environmental_attack_modifier) THEN
        RAISE EXCEPTION 'Battlefield attack snapshots are immutable';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER enc_personal_attack_battlefield_snapshot_immutable
BEFORE UPDATE ON enc_personal_attack
FOR EACH ROW EXECUTE FUNCTION enc_reject_battlefield_attack_snapshot_mutation();

CREATE TABLE cmd_personal_battlefield_condition_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    encounter_id bigint NOT NULL REFERENCES enc_personal_combat(encounter_id),
    light_before text NOT NULL,
    light_after text NOT NULL,
    obscurant_before text NOT NULL,
    obscurant_after text NOT NULL,
    extreme_weather_before boolean NOT NULL,
    extreme_weather_after boolean NOT NULL,
    version_before bigint NOT NULL,
    version_after bigint NOT NULL CHECK (version_after=version_before+1)
);

CREATE FUNCTION cmd_reject_battlefield_condition_receipt_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Battlefield-condition receipts are immutable'; END;
$$;
CREATE TRIGGER cmd_personal_battlefield_condition_receipt_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_battlefield_condition_receipt
FOR EACH ROW
EXECUTE FUNCTION cmd_reject_battlefield_condition_receipt_mutation();

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
        'set_personal_battlefield_conditions'
    )
);

COMMENT ON TABLE enc_personal_battlefield_condition IS
    'Campaign encounter state for source-defined ranged-attack conditions.';
COMMENT ON COLUMN enc_personal_attack.environmental_attack_modifier IS
    'Immutable declaration snapshot of condition and selected-sensor effects.';
