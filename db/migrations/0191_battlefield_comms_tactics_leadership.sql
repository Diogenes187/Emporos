CREATE TABLE rule_personal_communication_method (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    method_code text NOT NULL UNIQUE CHECK (
        method_code IN ('direct','hardlink','radio','laser','maser','meson')
    ),
    can_be_jammed boolean NOT NULL,
    can_be_blocked boolean NOT NULL,
    requires_line_of_sight boolean NOT NULL,
    penetrates_smoke_aerosols boolean NOT NULL,
    forbidden_while_moving boolean NOT NULL
);

CREATE TABLE rule_personal_initiative_support (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    support_code text NOT NULL UNIQUE CHECK (
        support_code IN ('tactics','leadership')
    ),
    skill_rule_id bigint NOT NULL REFERENCES rule_skill(rule_id),
    affects_whole_unit boolean NOT NULL,
    consumes_significant_action boolean NOT NULL,
    requires_communication boolean NOT NULL CHECK (requires_communication),
    bonus_uses_effect boolean NOT NULL CHECK (bonus_uses_effect),
    CHECK (affects_whole_unit<>consumes_significant_action)
);

CREATE TABLE enc_personal_unit_commander (
    encounter_id bigint NOT NULL REFERENCES enc_personal_combat(encounter_id),
    campaign_id bigint NOT NULL,
    side_code text NOT NULL,
    commander_actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    tactics_resolved boolean NOT NULL DEFAULT false,
    PRIMARY KEY (encounter_id,side_code),
    FOREIGN KEY (encounter_id,side_code,campaign_id)
        REFERENCES enc_side(encounter_id,side_code,campaign_id),
    FOREIGN KEY (encounter_id,commander_actor_id,campaign_id)
        REFERENCES enc_participant(encounter_id,actor_id,campaign_id),
    FOREIGN KEY (encounter_id,commander_actor_id)
        REFERENCES enc_personal_combatant(encounter_id,actor_id)
);

CREATE TABLE enc_personal_communication_link (
    encounter_id bigint NOT NULL REFERENCES enc_personal_combat(encounter_id),
    commander_actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    member_actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    method_rule_id bigint NOT NULL
        REFERENCES rule_personal_communication_method(rule_id),
    jammed boolean NOT NULL DEFAULT false,
    blocked boolean NOT NULL DEFAULT false,
    line_of_sight boolean NOT NULL DEFAULT true,
    smoke_or_aerosols boolean NOT NULL DEFAULT false,
    member_moving boolean NOT NULL DEFAULT false,
    communication_active boolean NOT NULL,
    PRIMARY KEY (encounter_id,commander_actor_id,member_actor_id),
    CHECK (commander_actor_id<>member_actor_id),
    FOREIGN KEY (encounter_id,commander_actor_id)
        REFERENCES enc_personal_combatant(encounter_id,actor_id),
    FOREIGN KEY (encounter_id,member_actor_id)
        REFERENCES enc_personal_combatant(encounter_id,actor_id)
);

ALTER TABLE enc_personal_combatant
    ADD COLUMN tactics_bonus integer NOT NULL DEFAULT 0 CHECK (
        tactics_bonus>=0
    ),
    ADD COLUMN tactics_bonus_suspended boolean NOT NULL DEFAULT false,
    ADD COLUMN leadership_bonus integer NOT NULL DEFAULT 0 CHECK (
        leadership_bonus>=0
    ),
    ADD CONSTRAINT enc_personal_combatant_tactics_suspend_check CHECK (
        NOT tactics_bonus_suspended OR tactics_bonus>0
    );

CREATE TABLE cmd_personal_communication_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    encounter_id bigint NOT NULL REFERENCES enc_personal_combat(encounter_id),
    commander_actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    member_actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    method_rule_id bigint NOT NULL
        REFERENCES rule_personal_communication_method(rule_id),
    active_before boolean,
    active_after boolean NOT NULL,
    tactics_suspended_before boolean NOT NULL,
    tactics_suspended_after boolean NOT NULL,
    initiative_before integer NOT NULL,
    initiative_after integer NOT NULL
);

CREATE TABLE cmd_personal_initiative_support_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    encounter_id bigint NOT NULL REFERENCES enc_personal_combat(encounter_id),
    support_rule_id bigint NOT NULL
        REFERENCES rule_personal_initiative_support(rule_id),
    commander_actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    target_actor_id bigint REFERENCES actor_actor(actor_id),
    characteristic_rule_id bigint NOT NULL
        REFERENCES rule_characteristic(rule_id),
    round_number integer NOT NULL CHECK (round_number>0),
    die_one smallint NOT NULL CHECK (die_one BETWEEN 1 AND 6),
    die_two smallint NOT NULL CHECK (die_two BETWEEN 1 AND 6),
    skill_modifier integer NOT NULL,
    characteristic_modifier integer NOT NULL,
    check_total integer NOT NULL,
    target_number integer NOT NULL,
    effect integer NOT NULL,
    applied_bonus integer NOT NULL CHECK (applied_bonus>=0),
    affected_count smallint NOT NULL CHECK (affected_count>=0),
    significant_before smallint,
    significant_after smallint
);

CREATE TABLE cmd_personal_initiative_support_target (
    command_id bigint NOT NULL
        REFERENCES cmd_personal_initiative_support_receipt(command_id),
    actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    communicated boolean NOT NULL,
    initiative_before integer NOT NULL,
    initiative_after integer NOT NULL,
    PRIMARY KEY (command_id,actor_id)
);

CREATE FUNCTION enc_validate_personal_communication_link()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE method rule_personal_communication_method%ROWTYPE;
DECLARE commander_side text;
DECLARE member_side text;
BEGIN
    SELECT * INTO STRICT method FROM rule_personal_communication_method
    WHERE rule_id=NEW.method_rule_id;
    SELECT participant.side_code INTO STRICT commander_side
    FROM enc_participant participant
    JOIN enc_personal_unit_commander unit
      ON unit.encounter_id=participant.encounter_id
     AND unit.side_code=participant.side_code
     AND unit.commander_actor_id=participant.actor_id
    WHERE participant.encounter_id=NEW.encounter_id
      AND participant.actor_id=NEW.commander_actor_id;
    SELECT side_code INTO STRICT member_side
    FROM enc_participant
    WHERE encounter_id=NEW.encounter_id
      AND actor_id=NEW.member_actor_id;
    IF commander_side<>member_side THEN
        RAISE EXCEPTION 'Battlefield communication must remain within a unit';
    END IF;
    NEW.communication_active := NOT (
        (method.can_be_jammed AND NEW.jammed)
        OR (method.can_be_blocked AND NEW.blocked)
        OR (method.requires_line_of_sight AND NOT NEW.line_of_sight)
        OR (method.requires_line_of_sight
            AND NOT method.penetrates_smoke_aerosols
            AND NEW.smoke_or_aerosols)
        OR (method.forbidden_while_moving AND NEW.member_moving)
    );
    RETURN NEW;
END;
$$;
CREATE TRIGGER enc_personal_communication_link_derive_active
BEFORE INSERT OR UPDATE ON enc_personal_communication_link
FOR EACH ROW EXECUTE FUNCTION enc_validate_personal_communication_link();

CREATE FUNCTION cmd_reject_personal_support_receipt_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Personal initiative-support receipts are immutable'; END;
$$;
CREATE TRIGGER cmd_personal_communication_receipt_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_communication_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_personal_support_receipt_mutation();
CREATE TRIGGER cmd_personal_initiative_support_receipt_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_initiative_support_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_personal_support_receipt_mutation();
CREATE TRIGGER cmd_personal_initiative_support_target_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_initiative_support_target
FOR EACH ROW EXECUTE FUNCTION cmd_reject_personal_support_receipt_mutation();

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
        'set_battlefield_communication','apply_personal_initiative_support'
    )
);

ALTER TABLE cmd_domain_event
    DROP CONSTRAINT cmd_domain_event_event_type_check;
ALTER TABLE cmd_domain_event
    ADD CONSTRAINT cmd_domain_event_event_type_check CHECK (
        event_type IN (
            'personal_attack_hit','personal_attack_missed',
            'personal_damage_applied','encounter_created',
            'encounter_mode_transitioned','encounter_participant_added',
            'encounter_attitude_set','encounter_attitude_changed',
            'encounter_attitude_unchanged','animal_reaction_context_set',
            'animal_reaction_resolved','starship_encounter_checked',
            'starship_contact_created','personal_combat_initialized',
            'personal_action_spent','personal_action_converted',
            'personal_reaction_declared','personal_turn_completed',
            'personal_combat_round_advanced','personal_attack_declared',
            'personal_turn_begun','personal_combatant_hastened',
            'personal_turn_delayed','delayed_personal_turn_resumed',
            'delayed_personal_turn_forfeited','personal_attack_aimed',
            'personal_stance_changed','personal_cover_set',
            'personal_combatant_moved','personal_attack_kill_aimed',
            'weapon_reload_advanced','weapon_reloaded',
            'psionic_power_activated','psionic_power_failed',
            'psionic_strength_recovered','psionic_strength_unchanged',
            'telepathic_shield_raised','telepathic_shield_lowered',
            'career_entry_qualified','career_entry_failed',
            'career_entry_fallback_resolved','career_basic_training_applied',
            'career_survival_passed','career_survival_failed',
            'career_rank_zero_award_applied','survival_mishap_resolved',
            'career_injury_determined','career_injury_applied',
            'career_injury_crisis_started','injury_crisis_cost_determined',
            'injury_crisis_paid','injury_crisis_death_accepted',
            'career_rank_attempt_declined','career_rank_attempt_failed',
            'career_rank_gained','career_term_training_applied',
            'career_term_completed','career_aging_determined',
            'career_aging_applied','career_aging_crisis_started',
            'career_reenlistment_forced_continue',
            'career_reenlistment_forced_departure',
            'career_reenlistment_choice_offered','career_retirement_required',
            'career_reenlistment_chosen','career_departure_chosen',
            'career_muster_initialized','career_pension_awarded',
            'career_benefit_awarded','career_weapon_benefit_choice_required',
            'career_weapon_item_awarded','career_weapon_skill_awarded',
            'character_creation_completed','aging_crisis_cost_determined',
            'aging_crisis_paid','aging_crisis_death_accepted',
            'career_medical_care_declined','career_medical_care_purchased',
            'career_anagathics_declared','character_final_details_updated',
            'actor_species_assigned','species_great_leap_resolved',
            'species_flyer_moved','species_flyer_fell',
            'actor_task_succeeded','actor_task_failed',
            'species_hive_mentality_resisted',
            'species_hive_mentality_compelled',
            'species_natural_curiosity_resisted',
            'species_natural_curiosity_compelled',
            'species_low_light_visibility_evaluated',
            'species_environmental_exposure_advanced',
            'species_environmental_damage_created',
            'species_environmental_damage_prevented',
            'battlefield_communication_changed',
            'personal_initiative_support_applied'
        )
    );

COMMENT ON TABLE enc_personal_communication_link IS
    'Campaign-safe commander-to-member links with method-specific blockers.';
COMMENT ON TABLE cmd_personal_initiative_support_receipt IS
    'Immutable Tactics and Leadership check facts and applied Effect.';
