CREATE TABLE cmd_personal_explosion_declaration_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    explosion_id bigint NOT NULL UNIQUE REFERENCES enc_personal_explosion(explosion_id),
    encounter_id bigint NOT NULL REFERENCES enc_personal_combat(encounter_id),
    round_number integer NOT NULL CHECK (round_number>0),
    target_count smallint NOT NULL CHECK (target_count>0)
);

CREATE TABLE cmd_personal_explosion_reaction_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    explosion_id bigint NOT NULL REFERENCES enc_personal_explosion(explosion_id),
    actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    reaction_kind text NOT NULL CHECK (reaction_kind IN ('none','dodge','dive')),
    reactions_before smallint NOT NULL CHECK (reactions_before>=0),
    reactions_after smallint NOT NULL CHECK (reactions_after>=reactions_before),
    initiative_before integer NOT NULL,
    initiative_after integer NOT NULL,
    check_modifier_before integer NOT NULL,
    check_modifier_after integer NOT NULL,
    initiative_timing text NOT NULL CHECK (
        initiative_timing IN ('none','current_round','following_round')
    ),
    next_round_adjustment_before integer NOT NULL,
    next_round_adjustment_after integer NOT NULL,
    UNIQUE (explosion_id,actor_id),
    CHECK (
        (reaction_kind='none'
         AND reactions_after=reactions_before
         AND initiative_after=initiative_before
         AND check_modifier_after=check_modifier_before
         AND initiative_timing='none'
         AND next_round_adjustment_after=next_round_adjustment_before)
        OR
        (reaction_kind IN ('dodge','dive')
         AND reactions_after=reactions_before+1
         AND initiative_timing<>'none')
    )
);

CREATE FUNCTION cmd_reject_personal_explosion_receipt_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Personal-explosion receipts are immutable'; END;
$$;

CREATE TRIGGER cmd_personal_explosion_declaration_receipt_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_explosion_declaration_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_personal_explosion_receipt_mutation();
CREATE TRIGGER cmd_personal_explosion_reaction_receipt_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_explosion_reaction_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_personal_explosion_receipt_mutation();
CREATE TRIGGER cmd_personal_explosion_resolution_receipt_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_explosion_resolution_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_personal_explosion_receipt_mutation();
CREATE TRIGGER cmd_personal_explosion_target_receipt_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_explosion_target_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_personal_explosion_receipt_mutation();

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
        'resolve_personal_explosion'
    )
);

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
        'blind_target','explosion_damage','explosion_dodge'
    )
);

COMMENT ON CONSTRAINT health_damage_exactly_one_source_check
    ON health_damage_instance IS
    'Every damage instance has exactly one attack, environmental, or explosion origin.';
COMMENT ON TABLE cmd_personal_explosion_reaction_receipt IS
    'Immutable independent none, dodge, or dive declaration facts.';
