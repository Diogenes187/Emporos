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
        'psionic_assault_damage','psionic_teleport_disorientation',
        'extended_action_timing','extended_action_interruption'
    )
);

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
        'declare_personal_explosion','declare_personal_explosion_reaction',
        'resolve_personal_explosion','authorize_extreme_range',
        'resolve_personal_grapple_check','apply_personal_grapple_option',
        'apply_personal_fatigue','complete_personal_fatigue_rest',
        'resolve_personal_unconscious_recovery',
        'resolve_personal_natural_healing',
        'apply_personal_first_aid','resolve_personal_surgery',
        'apply_personal_medical_care','resolve_personal_mental_healing',
        'resolve_ground_starship_volley_attacks',
        'finalize_ground_starship_volley',
        'equip_personal_armor','unequip_personal_armor',
        'apply_personal_armor_usage','specialize_personal_computer',
        'resolve_personal_coup_de_grace',
        'start_personal_extended_action','advance_personal_extended_action',
        'abandon_personal_extended_action',
        'resolve_personal_extended_action_interruption'
    )
);

CREATE TABLE enc_personal_extended_action (
    extended_action_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    encounter_id bigint NOT NULL REFERENCES enc_personal_combat(encounter_id),
    actor_id bigint NOT NULL,
    task_reference text NOT NULL CHECK (btrim(task_reference)<>''),
    characteristic_rule_id bigint NOT NULL REFERENCES rule_characteristic(rule_id),
    skill_rule_id bigint NOT NULL REFERENCES rule_skill(rule_id),
    time_frame_rule_id bigint NOT NULL REFERENCES rule_time_frame(rule_id),
    required_rounds integer NOT NULL CHECK (required_rounds>0),
    completed_rounds integer NOT NULL CHECK (
        completed_rounds BETWEEN 0 AND required_rounds
    ),
    last_progress_round integer CHECK (last_progress_round>0),
    work_lost_round integer CHECK (work_lost_round>0),
    action_status text NOT NULL CHECK (
        action_status IN ('active','completed','abandoned','ruined')
    ),
    started_round integer NOT NULL CHECK (started_round>0),
    started_at timestamptz NOT NULL,
    ended_at timestamptz,
    source_command_id bigint NOT NULL REFERENCES cmd_command(command_id),
    FOREIGN KEY (encounter_id,actor_id)
        REFERENCES enc_personal_combatant(encounter_id,actor_id),
    CHECK (
        (action_status='active' AND ended_at IS NULL
         AND completed_rounds<required_rounds)
        OR (action_status='completed' AND ended_at IS NOT NULL
            AND completed_rounds=required_rounds)
        OR (action_status IN ('abandoned','ruined') AND ended_at IS NOT NULL)
    )
);
CREATE UNIQUE INDEX enc_one_active_extended_action
    ON enc_personal_extended_action(encounter_id,actor_id)
    WHERE action_status='active';

CREATE TABLE cmd_personal_extended_action_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    extended_action_id bigint NOT NULL REFERENCES
        enc_personal_extended_action(extended_action_id),
    operation text NOT NULL CHECK (
        operation IN ('start','advance','abandon','interrupt')
    ),
    encounter_id bigint NOT NULL,
    actor_id bigint NOT NULL,
    round_number integer NOT NULL CHECK (round_number>0),
    status_before text CHECK (
        status_before IN ('active','completed','abandoned','ruined')
    ),
    status_after text NOT NULL CHECK (
        status_after IN ('active','completed','abandoned','ruined')
    ),
    completed_rounds_before integer NOT NULL CHECK (completed_rounds_before>=0),
    completed_rounds_after integer NOT NULL CHECK (completed_rounds_after>=0),
    required_rounds integer NOT NULL CHECK (required_rounds>0),
    work_counted boolean NOT NULL,
    resolved_at timestamptz NOT NULL,
    FOREIGN KEY (encounter_id,actor_id)
        REFERENCES enc_personal_combatant(encounter_id,actor_id),
    CHECK ((operation='start')=(status_before IS NULL)),
    CHECK (completed_rounds_before<=required_rounds),
    CHECK (completed_rounds_after<=required_rounds),
    CHECK (
        (operation='start' AND completed_rounds_before=0
         AND completed_rounds_after=1 AND work_counted)
        OR (operation='advance' AND status_before='active'
            AND completed_rounds_after=completed_rounds_before+
                CASE WHEN work_counted THEN 1 ELSE 0 END)
        OR (operation='abandon' AND status_before='active'
            AND status_after='abandoned' AND NOT work_counted
            AND completed_rounds_after=completed_rounds_before)
        OR (operation='interrupt' AND status_before='active'
            AND NOT work_counted
            AND completed_rounds_after<=completed_rounds_before)
    ),
    CHECK ((status_after='completed')=
           (completed_rounds_after=required_rounds))
);

CREATE TABLE cmd_personal_extended_action_interruption (
    command_id bigint PRIMARY KEY REFERENCES
        cmd_personal_extended_action_receipt(command_id),
    damage_instance_id bigint NOT NULL UNIQUE REFERENCES
        health_damage_instance(damage_instance_id),
    post_armor_damage integer NOT NULL CHECK (post_armor_damage>0),
    skill_modifier integer NOT NULL,
    damage_modifier integer NOT NULL CHECK (
        damage_modifier=-post_armor_damage
    ),
    check_total integer NOT NULL,
    target_number integer NOT NULL CHECK (target_number=8),
    effect integer NOT NULL CHECK (effect=check_total-target_number),
    succeeded boolean NOT NULL CHECK (succeeded=(check_total>=target_number)),
    exceptional_failure boolean NOT NULL CHECK (
        exceptional_failure=(effect<=-6)
    )
);

CREATE FUNCTION cmd_validate_personal_extended_action_receipt()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE stored_command_type text;
DECLARE action enc_personal_extended_action%ROWTYPE;
DECLARE expected_command_type text;
BEGIN
 SELECT command_type INTO STRICT stored_command_type
 FROM cmd_command WHERE command_id=NEW.command_id;
 SELECT * INTO STRICT action FROM enc_personal_extended_action
 WHERE extended_action_id=NEW.extended_action_id;
 expected_command_type := CASE NEW.operation
   WHEN 'start' THEN 'start_personal_extended_action'
   WHEN 'advance' THEN 'advance_personal_extended_action'
   WHEN 'abandon' THEN 'abandon_personal_extended_action'
   WHEN 'interrupt' THEN 'resolve_personal_extended_action_interruption'
 END;
 IF stored_command_type<>expected_command_type
    OR action.encounter_id<>NEW.encounter_id
    OR action.actor_id<>NEW.actor_id
    OR action.action_status<>NEW.status_after
    OR action.completed_rounds<>NEW.completed_rounds_after
    OR action.required_rounds<>NEW.required_rounds THEN
   RAISE EXCEPTION 'Extended Action receipt does not match command or state';
 END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER cmd_personal_extended_action_receipt_valid
BEFORE INSERT ON cmd_personal_extended_action_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_validate_personal_extended_action_receipt();

CREATE FUNCTION cmd_validate_personal_extended_action_interruption()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE draw_total integer;
DECLARE draw_count integer;
BEGIN
 SELECT count(*),sum(result) INTO draw_count,draw_total
 FROM cmd_random_draw WHERE command_id=NEW.command_id
   AND draw_group='extended_action_interruption';
 IF draw_count<>2
    OR NEW.check_total<>draw_total+NEW.skill_modifier+NEW.damage_modifier
    OR NOT EXISTS (
      SELECT 1 FROM cmd_personal_extended_action_receipt receipt
      WHERE receipt.command_id=NEW.command_id
        AND receipt.operation='interrupt') THEN
   RAISE EXCEPTION 'Extended Action interruption does not match random draws';
 END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER cmd_personal_extended_action_interruption_valid
BEFORE INSERT ON cmd_personal_extended_action_interruption
FOR EACH ROW EXECUTE FUNCTION cmd_validate_personal_extended_action_interruption();

CREATE FUNCTION cmd_reject_extended_action_receipt_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Extended Action receipts are immutable'; END; $$;
CREATE TRIGGER cmd_personal_extended_action_receipt_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_extended_action_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_extended_action_receipt_mutation();
CREATE TRIGGER cmd_personal_extended_action_interruption_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_extended_action_interruption
FOR EACH ROW EXECUTE FUNCTION cmd_reject_extended_action_receipt_mutation();

COMMENT ON TABLE enc_personal_extended_action IS
    'Campaign combat aggregate for one exclusive CE-COMBAT-018 task commitment.';
COMMENT ON TABLE cmd_personal_extended_action_receipt IS
    'Immutable start, progress, abandonment, and interruption snapshots.';
