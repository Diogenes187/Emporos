ALTER TABLE cmd_personal_computer_specialization_receipt
    DROP COLUMN surcharge_credits;
ALTER TABLE cmd_personal_computer_specialization_receipt
    ADD COLUMN surcharge_quarter_credits bigint NOT NULL CHECK (
        surcharge_quarter_credits=base_computer_cost_credits*added_rating
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
        'declare_personal_explosion',
        'declare_personal_explosion_reaction',
        'resolve_personal_explosion','authorize_extreme_range',
        'resolve_personal_grapple_check','apply_personal_grapple_option',
        'apply_personal_fatigue','complete_personal_fatigue_rest',
        'resolve_personal_unconscious_recovery',
        'resolve_personal_natural_healing',
        'apply_personal_first_aid','resolve_personal_surgery',
        'apply_personal_medical_care',
        'resolve_personal_mental_healing',
        'resolve_ground_starship_volley_attacks',
        'finalize_ground_starship_volley',
        'equip_personal_armor','unequip_personal_armor',
        'apply_personal_armor_usage',
        'specialize_personal_computer'
    )
);

CREATE FUNCTION cmd_validate_personal_computer_specialization_command()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS (
   SELECT 1 FROM cmd_command command
    WHERE command.command_id=NEW.command_id
      AND command.command_type='specialize_personal_computer'
 ) THEN
   RAISE EXCEPTION
     'Computer specialization receipt requires specialization command';
 END IF;
 RETURN NEW;
END;
$$;
CREATE TRIGGER cmd_personal_computer_specialization_command_valid
BEFORE INSERT ON cmd_personal_computer_specialization_receipt
FOR EACH ROW EXECUTE FUNCTION
    cmd_validate_personal_computer_specialization_command();

COMMENT ON COLUMN
    cmd_personal_computer_specialization_receipt.surcharge_quarter_credits IS
    'Exact surcharge in quarter-Credit units; avoids unstated rounding.';
