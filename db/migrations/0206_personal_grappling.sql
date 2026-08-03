CREATE TABLE rule_personal_grapple (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    skill_rule_id bigint NOT NULL REFERENCES rule_skill(rule_id),
    range_rule_id bigint NOT NULL REFERENCES combat_range_band(rule_id),
    action_cost smallint NOT NULL CHECK (action_cost=1),
    damage_base smallint NOT NULL CHECK (damage_base=2),
    disarm_take_minimum_effect smallint NOT NULL CHECK (
        disarm_take_minimum_effect=6
    ),
    maximum_displacement_metres numeric NOT NULL CHECK (
        maximum_displacement_metres=3
    ),
    throw_damage_dice smallint NOT NULL CHECK (throw_damage_dice=1),
    throw_damage_die_sides smallint NOT NULL CHECK (
        throw_damage_die_sides=6
    ),
    ties_have_no_winner boolean NOT NULL CHECK (ties_have_no_winner),
    armor_applies boolean NOT NULL CHECK (NOT armor_applies)
);

CREATE TABLE rule_personal_grapple_option (
    option_code text PRIMARY KEY CHECK (
        option_code IN (
            'continue','disarm','drag','escape','damage','knock_prone','throw'
        )
    ),
    display_order smallint NOT NULL UNIQUE CHECK (display_order>0),
    may_continue_grapple boolean NOT NULL,
    always_ends_grapple boolean NOT NULL,
    causes_displacement boolean NOT NULL,
    causes_damage boolean NOT NULL
);

CREATE TABLE enc_personal_grapple (
    grapple_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    encounter_id bigint NOT NULL REFERENCES enc_personal_combat(encounter_id),
    participant_a_actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    participant_b_actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    grapple_status text NOT NULL CHECK (
        grapple_status IN ('pending_option','active','ended')
    ),
    pending_check_command_id bigint UNIQUE REFERENCES cmd_command(command_id),
    pending_winner_actor_id bigint REFERENCES actor_actor(actor_id),
    check_sequence smallint NOT NULL CHECK (check_sequence>0),
    started_round integer NOT NULL CHECK (started_round>0),
    ended_round integer CHECK (ended_round>0),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    ended_at timestamptz,
    UNIQUE (
        encounter_id,participant_a_actor_id,participant_b_actor_id,created_at
    ),
    CHECK (participant_a_actor_id<participant_b_actor_id),
    CHECK (
        (grapple_status='pending_option'
         AND pending_check_command_id IS NOT NULL
         AND pending_winner_actor_id IS NOT NULL
         AND ended_round IS NULL AND ended_at IS NULL)
        OR (grapple_status='active'
            AND pending_check_command_id IS NULL
            AND pending_winner_actor_id IS NULL
            AND ended_round IS NULL AND ended_at IS NULL)
        OR (grapple_status='ended' AND pending_check_command_id IS NULL
            AND pending_winner_actor_id IS NULL
            AND ended_round IS NOT NULL AND ended_at IS NOT NULL)
    )
);

CREATE TABLE enc_personal_grapple_active_actor (
    actor_id bigint PRIMARY KEY REFERENCES actor_actor(actor_id),
    encounter_id bigint NOT NULL REFERENCES enc_personal_combat(encounter_id),
    grapple_id bigint NOT NULL REFERENCES enc_personal_grapple(grapple_id),
    UNIQUE (grapple_id,actor_id)
);

CREATE TABLE cmd_personal_grapple_check_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    grapple_id bigint NOT NULL REFERENCES enc_personal_grapple(grapple_id),
    encounter_id bigint NOT NULL REFERENCES enc_personal_combat(encounter_id),
    round_number integer NOT NULL CHECK (round_number>0),
    check_sequence smallint NOT NULL CHECK (check_sequence>0),
    initial_attempt boolean NOT NULL,
    challenger_actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    opponent_actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    challenger_characteristic_rule_id bigint NOT NULL
        REFERENCES rule_characteristic(rule_id),
    opponent_characteristic_rule_id bigint NOT NULL
        REFERENCES rule_characteristic(rule_id),
    challenger_skill_level smallint,
    opponent_skill_level smallint,
    challenger_skill_modifier integer NOT NULL,
    opponent_skill_modifier integer NOT NULL,
    challenger_characteristic_modifier integer NOT NULL,
    opponent_characteristic_modifier integer NOT NULL,
    challenger_circumstance_modifier integer NOT NULL,
    opponent_circumstance_modifier integer NOT NULL,
    challenger_total integer NOT NULL,
    opponent_total integer NOT NULL,
    winner_actor_id bigint REFERENCES actor_actor(actor_id),
    effect integer NOT NULL CHECK (effect>=0),
    significant_before smallint NOT NULL CHECK (significant_before>0),
    significant_after smallint NOT NULL CHECK (significant_after>=0),
    status_before text NOT NULL CHECK (
        status_before IN ('none','active')
    ),
    status_after text NOT NULL CHECK (
        status_after IN ('none','active','pending_option')
    ),
    UNIQUE (grapple_id,check_sequence),
    CHECK (challenger_actor_id<>opponent_actor_id),
    CHECK (
        (winner_actor_id IS NULL AND challenger_total=opponent_total
         AND effect=0 AND status_after=status_before)
        OR (winner_actor_id=challenger_actor_id
            AND challenger_total>opponent_total
            AND effect=challenger_total-opponent_total
            AND status_after='pending_option')
        OR (winner_actor_id=opponent_actor_id
            AND opponent_total>challenger_total
            AND effect=opponent_total-challenger_total
            AND status_after='pending_option')
    )
);

CREATE TABLE cmd_personal_grapple_option_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    check_command_id bigint NOT NULL UNIQUE
        REFERENCES cmd_personal_grapple_check_receipt(command_id),
    grapple_id bigint NOT NULL REFERENCES enc_personal_grapple(grapple_id),
    encounter_id bigint NOT NULL REFERENCES enc_personal_combat(encounter_id),
    round_number integer NOT NULL CHECK (round_number>0),
    winner_actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    loser_actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    option_code text NOT NULL REFERENCES rule_personal_grapple_option,
    effect integer NOT NULL CHECK (effect>0),
    continue_grapple boolean NOT NULL,
    displacement_metres numeric NOT NULL CHECK (
        displacement_metres BETWEEN 0 AND 3
    ),
    raw_damage integer NOT NULL CHECK (raw_damage>=0),
    damage_instance_id bigint UNIQUE
        REFERENCES health_damage_instance(damage_instance_id),
    stance_before_rule_id bigint REFERENCES rule_personal_stance(rule_id),
    stance_after_rule_id bigint REFERENCES rule_personal_stance(rule_id),
    item_instance_id bigint REFERENCES inv_item_instance(item_instance_id),
    item_outcome text CHECK (item_outcome IN ('taken','floor')),
    transfer_id bigint REFERENCES inv_transfer(transfer_id),
    grapple_status_after text NOT NULL CHECK (
        grapple_status_after IN ('active','ended')
    ),
    CHECK (winner_actor_id<>loser_actor_id),
    CHECK ((raw_damage>0)=(damage_instance_id IS NOT NULL)),
    CHECK ((item_instance_id IS NOT NULL)=(item_outcome IS NOT NULL)),
    CHECK ((item_instance_id IS NOT NULL)=(transfer_id IS NOT NULL)),
    CHECK (
        (continue_grapple AND grapple_status_after='active')
        OR (NOT continue_grapple AND grapple_status_after='ended')
    ),
    CHECK (
        (option_code='continue' AND continue_grapple
         AND displacement_metres=0 AND raw_damage=0)
        OR (option_code='disarm' AND displacement_metres=0
            AND raw_damage=0 AND item_instance_id IS NOT NULL)
        OR (option_code='drag' AND raw_damage=0)
        OR (option_code='escape' AND NOT continue_grapple
            AND displacement_metres=0 AND raw_damage=0)
        OR (option_code='damage' AND displacement_metres=0
            AND raw_damage=2+effect)
        OR (option_code='knock_prone' AND displacement_metres=0
            AND raw_damage=0 AND stance_before_rule_id IS NOT NULL
            AND stance_after_rule_id IS NOT NULL)
        OR (option_code='throw' AND NOT continue_grapple
            AND raw_damage BETWEEN 1 AND 6)
    )
);

CREATE TABLE enc_personal_grapple_state_transition (
    grapple_id bigint NOT NULL REFERENCES enc_personal_grapple(grapple_id),
    transition_order smallint NOT NULL CHECK (transition_order>0),
    command_id bigint NOT NULL UNIQUE REFERENCES cmd_command(command_id),
    state_before text NOT NULL CHECK (
        state_before IN ('none','active','pending_option')
    ),
    state_after text NOT NULL CHECK (
        state_after IN ('none','active','pending_option','ended')
    ),
    PRIMARY KEY (grapple_id,transition_order)
);

ALTER TABLE health_damage_instance
    ADD COLUMN grapple_option_command_id bigint
        REFERENCES cmd_command(command_id),
    ADD CONSTRAINT health_damage_instance_grapple_target_unique
        UNIQUE (grapple_option_command_id,target_actor_id);
ALTER TABLE health_damage_instance
    DROP CONSTRAINT health_damage_exactly_one_source_check,
    ADD CONSTRAINT health_damage_exactly_one_source_check CHECK (
        num_nonnulls(
            attack_command_id,environmental_command_id,
            explosion_command_id,grapple_option_command_id
        )=1
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
        'blind_target','explosion_damage','explosion_dodge',
        'combat_scatter','combat_nearest_tie',
        'grapple_challenger','grapple_opponent','grapple_throw_damage'
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
        'declare_personal_explosion',
        'declare_personal_explosion_reaction',
        'resolve_personal_explosion','authorize_extreme_range',
        'resolve_personal_grapple_check','apply_personal_grapple_option'
    )
);

CREATE FUNCTION cmd_reject_grapple_history_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Grappling history is immutable'; END;
$$;
CREATE TRIGGER cmd_personal_grapple_check_receipt_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_grapple_check_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_grapple_history_mutation();
CREATE TRIGGER cmd_personal_grapple_option_receipt_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_grapple_option_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_grapple_history_mutation();
CREATE TRIGGER enc_personal_grapple_transition_immutable
BEFORE UPDATE OR DELETE ON enc_personal_grapple_state_transition
FOR EACH ROW EXECUTE FUNCTION cmd_reject_grapple_history_mutation();

CREATE FUNCTION enc_validate_grapple_active_actor()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE grapple enc_personal_grapple%ROWTYPE;
BEGIN
 SELECT * INTO STRICT grapple FROM enc_personal_grapple
  WHERE grapple_id=NEW.grapple_id;
 IF NEW.encounter_id<>grapple.encounter_id
    OR NEW.actor_id NOT IN (
        grapple.participant_a_actor_id,grapple.participant_b_actor_id)
    OR grapple.grapple_status NOT IN ('active','pending_option') THEN
   RAISE EXCEPTION 'Invalid active grapple participant';
 END IF;
 RETURN NEW;
END;
$$;
CREATE TRIGGER enc_personal_grapple_active_actor_validate
BEFORE INSERT OR UPDATE ON enc_personal_grapple_active_actor
FOR EACH ROW EXECUTE FUNCTION enc_validate_grapple_active_actor();

CREATE FUNCTION enc_guard_personal_grapple_state()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE'
    OR ROW(NEW.encounter_id,NEW.participant_a_actor_id,
           NEW.participant_b_actor_id,NEW.started_round,NEW.created_at)
       IS DISTINCT FROM
       ROW(OLD.encounter_id,OLD.participant_a_actor_id,
           OLD.participant_b_actor_id,OLD.started_round,OLD.created_at)
    OR OLD.grapple_status='ended'
    OR (
      OLD.grapple_status='active'
      AND NOT (
        NEW.grapple_status='pending_option'
        AND NEW.check_sequence=OLD.check_sequence+1
        AND NEW.pending_check_command_id IS NOT NULL
        AND NEW.pending_winner_actor_id IS NOT NULL
      )
    )
    OR (
      OLD.grapple_status='pending_option'
      AND NOT (
        NEW.grapple_status IN ('active','ended')
        AND NEW.check_sequence=OLD.check_sequence
        AND NEW.pending_check_command_id IS NULL
        AND NEW.pending_winner_actor_id IS NULL
      )
    ) THEN
   RAISE EXCEPTION 'Invalid or immutable grapple-state transition';
 END IF;
 RETURN NEW;
END;
$$;
CREATE TRIGGER enc_personal_grapple_state_guard
BEFORE UPDATE OR DELETE ON enc_personal_grapple
FOR EACH ROW EXECUTE FUNCTION enc_guard_personal_grapple_state();

CREATE FUNCTION cmd_validate_personal_grapple_option()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE checked cmd_personal_grapple_check_receipt%ROWTYPE;
DECLARE prone_id bigint;
DECLARE draw cmd_random_draw%ROWTYPE;
BEGIN
 SELECT * INTO STRICT checked FROM cmd_personal_grapple_check_receipt
  WHERE command_id=NEW.check_command_id;
 SELECT rule_id INTO STRICT prone_id FROM rule_personal_stance
  WHERE stance_code='prone';
 IF NEW.grapple_id<>checked.grapple_id
    OR NEW.encounter_id<>checked.encounter_id
    OR NEW.round_number<>checked.round_number
    OR NEW.winner_actor_id<>checked.winner_actor_id
    OR NEW.loser_actor_id NOT IN (
        checked.challenger_actor_id,checked.opponent_actor_id)
    OR NEW.loser_actor_id=NEW.winner_actor_id
    OR NEW.effect<>checked.effect
    OR (NEW.option_code='knock_prone'
        AND NEW.stance_after_rule_id<>prone_id)
    OR (NEW.option_code='disarm' AND (
        (NEW.effect>=6 AND NEW.item_outcome<>'taken')
        OR (NEW.effect<6 AND NEW.item_outcome<>'floor')))
 THEN
   RAISE EXCEPTION 'Grapple option does not match opposed check';
 END IF;
 IF NEW.option_code='throw' THEN
   SELECT * INTO STRICT draw FROM cmd_random_draw
    WHERE command_id=NEW.command_id
      AND draw_group='grapple_throw_damage' AND draw_order=1;
   IF draw.die_sides<>6 OR draw.result<>NEW.raw_damage THEN
     RAISE EXCEPTION 'Grapple throw damage draw does not match receipt';
   END IF;
 END IF;
 IF NEW.damage_instance_id IS NOT NULL AND NOT EXISTS (
   SELECT 1 FROM health_damage_instance damage
    WHERE damage.damage_instance_id=NEW.damage_instance_id
      AND damage.grapple_option_command_id=NEW.command_id
      AND damage.target_actor_id=NEW.loser_actor_id
      AND damage.penetrating_damage=NEW.raw_damage
 ) THEN
   RAISE EXCEPTION 'Grapple damage instance does not match receipt';
 END IF;
 RETURN NEW;
END;
$$;
CREATE TRIGGER cmd_personal_grapple_option_receipt_validate
BEFORE INSERT ON cmd_personal_grapple_option_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_validate_personal_grapple_option();

COMMENT ON TABLE enc_personal_grapple IS
    'CE-COMBAT-010 campaign-safe current grapple state.';
