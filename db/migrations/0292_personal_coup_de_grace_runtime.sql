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
        'resolve_personal_coup_de_grace'
    )
);

CREATE TABLE cmd_personal_coup_de_grace_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    encounter_id bigint NOT NULL REFERENCES enc_personal_combat(encounter_id),
    actor_id bigint NOT NULL,
    target_actor_id bigint NOT NULL,
    round_number integer NOT NULL CHECK (round_number>0),
    weapon_rule_id bigint NOT NULL REFERENCES inv_weapon_definition(item_rule_id),
    delivery_kind text NOT NULL CHECK (delivery_kind IN ('melee','ranged')),
    range_relationship text NOT NULL CHECK (
        (delivery_kind='melee' AND range_relationship='close-quarters')
        OR (delivery_kind='ranged' AND range_relationship='adjacent')
    ),
    helpless_basis text NOT NULL CHECK (
        helpless_basis IN (
            'unconscious','fully_restrained','incapacitated',
            'referee_adjudication'
        )
    ),
    helpless_evidence text NOT NULL CHECK (btrim(helpless_evidence)<>''),
    significant_actions_before smallint NOT NULL CHECK (
        significant_actions_before>0
    ),
    significant_actions_after smallint NOT NULL CHECK (
        significant_actions_after=significant_actions_before-1
    ),
    strength_before smallint NOT NULL CHECK (strength_before>=0),
    strength_after smallint NOT NULL CHECK (strength_after=0),
    dexterity_before smallint NOT NULL CHECK (dexterity_before>=0),
    dexterity_after smallint NOT NULL CHECK (dexterity_after=0),
    endurance_before smallint NOT NULL CHECK (endurance_before>=0),
    endurance_after smallint NOT NULL CHECK (endurance_after=0),
    actor_version_before bigint NOT NULL,
    actor_version_after bigint NOT NULL CHECK (
        actor_version_after=actor_version_before+1
    ),
    target_version_before bigint NOT NULL,
    target_version_after bigint NOT NULL CHECK (
        target_version_after=target_version_before+1
    ),
    resolved_at timestamptz NOT NULL,
    FOREIGN KEY (actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    FOREIGN KEY (target_actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    FOREIGN KEY (encounter_id,actor_id)
        REFERENCES enc_personal_combatant(encounter_id,actor_id),
    FOREIGN KEY (encounter_id,target_actor_id)
        REFERENCES enc_personal_combatant(encounter_id,actor_id),
    CHECK (actor_id<>target_actor_id),
    CHECK (strength_before+dexterity_before+endurance_before>0)
);

CREATE FUNCTION cmd_validate_personal_coup_de_grace()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE command_type text;
DECLARE combatant enc_personal_combatant%ROWTYPE;
DECLARE strength smallint;
DECLARE dexterity smallint;
DECLARE endurance smallint;
DECLARE actor_version bigint;
DECLARE target_version bigint;
BEGIN
 SELECT command.command_type INTO STRICT command_type FROM cmd_command command
  WHERE command.command_id=NEW.command_id;
 SELECT * INTO STRICT combatant FROM enc_personal_combatant
  WHERE encounter_id=NEW.encounter_id AND actor_id=NEW.actor_id;
 SELECT
   max(state.current_value) FILTER (
     WHERE rule.rule_code='characteristic.strength'),
   max(state.current_value) FILTER (
     WHERE rule.rule_code='characteristic.dexterity'),
   max(state.current_value) FILTER (
     WHERE rule.rule_code='characteristic.endurance')
 INTO strength,dexterity,endurance
 FROM actor_characteristic state
 JOIN rule_rule rule ON rule.rule_id=state.characteristic_rule_id
 WHERE state.actor_id=NEW.target_actor_id;
 SELECT concurrency_version INTO STRICT actor_version FROM actor_actor
  WHERE actor_id=NEW.actor_id;
 SELECT concurrency_version INTO STRICT target_version FROM actor_actor
  WHERE actor_id=NEW.target_actor_id;
 IF command_type<>'resolve_personal_coup_de_grace'
    OR combatant.significant_actions_remaining<>
       NEW.significant_actions_after
    OR strength<>0 OR dexterity<>0 OR endurance<>0
    OR actor_version<>NEW.actor_version_after
    OR target_version<>NEW.target_version_after THEN
   RAISE EXCEPTION 'Coup de Grace receipt does not match command or state';
 END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER cmd_personal_coup_de_grace_valid
BEFORE INSERT ON cmd_personal_coup_de_grace_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_validate_personal_coup_de_grace();

CREATE FUNCTION cmd_reject_personal_coup_de_grace_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Coup de Grace receipts are immutable'; END; $$;
CREATE TRIGGER cmd_personal_coup_de_grace_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_coup_de_grace_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_personal_coup_de_grace_mutation();

COMMENT ON TABLE cmd_personal_coup_de_grace_receipt IS
    'Immutable CE-COMBAT-017 action, weapon, helplessness, and death-state snapshot.';
