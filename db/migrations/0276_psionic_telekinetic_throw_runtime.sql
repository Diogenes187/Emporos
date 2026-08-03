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
        'telekinetic_damage'
    )
);

CREATE TABLE cmd_psi_telekinetic_throw_receipt (
    activation_command_id bigint PRIMARY KEY REFERENCES
        cmd_psi_telekinetic_manipulation_receipt(activation_command_id),
    target_actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    psion_to_target_metres numeric NOT NULL CHECK (
        psion_to_target_metres>=0
    ),
    object_origin_to_target_metres numeric NOT NULL CHECK (
        object_origin_to_target_metres>=0
    ),
    selected_distance_metres numeric NOT NULL CHECK (
        selected_distance_metres=
        greatest(psion_to_target_metres,object_origin_to_target_metres)
    ),
    range_band_rule_id bigint NOT NULL REFERENCES combat_range_band(rule_id),
    skill_modifier smallint NOT NULL,
    characteristic_modifier smallint NOT NULL,
    difficulty_modifier smallint NOT NULL,
    circumstance_modifier_total smallint NOT NULL,
    attack_total smallint NOT NULL,
    target_number smallint NOT NULL,
    attack_effect smallint NOT NULL,
    hit boolean NOT NULL,
    damage_dice_count smallint,
    damage_die_sides smallint,
    rolled_damage smallint NOT NULL CHECK (rolled_damage>=0),
    effect_damage smallint NOT NULL CHECK (effect_damage>=0),
    raw_damage smallint NOT NULL CHECK (raw_damage>=0),
    thrown_creature_damage smallint,
    CHECK (hit=(attack_total>=target_number)),
    CHECK (attack_effect=attack_total-target_number),
    CHECK (
        (hit AND effect_damage=greatest(attack_effect,0)
         AND raw_damage=rolled_damage+effect_damage)
        OR
        (NOT hit AND rolled_damage=0 AND effect_damage=0 AND raw_damage=0)
    ),
    CHECK (
        thrown_creature_damage IS NULL
        OR thrown_creature_damage=raw_damage
    )
);

CREATE FUNCTION cmd_validate_psi_telekinetic_throw()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE manipulation cmd_psi_telekinetic_manipulation_receipt%ROWTYPE;
DECLARE activation cmd_psionic_activation_receipt%ROWTYPE;
DECLARE profile rule_psi_telekinesis_mass_profile%ROWTYPE;
DECLARE expected_skill integer;
DECLARE expected_characteristic integer;
DECLARE expected_difficulty integer;
DECLARE expected_target integer;
DECLARE attack_draw_total integer;
DECLARE attack_draw_count integer;
DECLARE invalid_attack_draw_count integer;
DECLARE damage_draw_total integer;
DECLARE damage_draw_count integer;
DECLARE invalid_damage_draw_count integer;
DECLARE target_campaign_id bigint;
BEGIN
 SELECT * INTO STRICT manipulation
   FROM cmd_psi_telekinetic_manipulation_receipt
  WHERE activation_command_id=NEW.activation_command_id;
 SELECT * INTO STRICT activation FROM cmd_psionic_activation_receipt
  WHERE command_id=NEW.activation_command_id;
 SELECT * INTO STRICT profile FROM rule_psi_telekinesis_mass_profile
  WHERE power_rule_id=activation.power_rule_id;
 SELECT skill.skill_level INTO STRICT expected_skill
   FROM rule_psi_telekinesis_system system
   JOIN actor_skill skill
     ON skill.actor_id=manipulation.actor_id
    AND skill.skill_rule_id=system.throwing_skill_rule_id;
 SELECT band.modifier INTO STRICT expected_characteristic
   FROM actor_characteristic characteristic
   JOIN rule_rule rule ON rule.rule_id=characteristic.characteristic_rule_id
    AND rule.rule_code='characteristic.dexterity'
   JOIN rule_characteristic_modifier_band band
     ON (band.characteristic_rule_id IS NULL
         OR band.characteristic_rule_id=characteristic.characteristic_rule_id)
    AND band.score_range @> characteristic.current_value::integer
  WHERE characteristic.actor_id=manipulation.actor_id
  ORDER BY band.characteristic_rule_id NULLS LAST LIMIT 1;
 SELECT difficulty.modifier INTO STRICT expected_difficulty
   FROM combat_attack_profile_difficulty profile_difficulty
   JOIN rule_difficulty difficulty
     ON difficulty.rule_id=profile_difficulty.difficulty_rule_id
  WHERE profile_difficulty.attack_profile_code='thrown'
    AND profile_difficulty.range_band_rule_id=NEW.range_band_rule_id
    AND profile_difficulty.permitted;
 SELECT target_number INTO STRICT expected_target FROM rule_check_system;
 SELECT COALESCE(sum(result),0),count(*),
        count(*) FILTER (WHERE die_sides<>6)
   INTO attack_draw_total,attack_draw_count,invalid_attack_draw_count
   FROM cmd_random_draw WHERE command_id=NEW.activation_command_id
    AND draw_group='telekinetic_attack';
 SELECT COALESCE(sum(result),0),count(*),
        count(*) FILTER (
          WHERE die_sides IS DISTINCT FROM profile.throwing_damage_die_sides
        )
   INTO damage_draw_total,damage_draw_count,invalid_damage_draw_count
   FROM cmd_random_draw WHERE command_id=NEW.activation_command_id
    AND draw_group='telekinetic_damage';
 SELECT campaign_id INTO STRICT target_campaign_id
   FROM actor_actor WHERE actor_id=NEW.target_actor_id;
 IF NOT activation.succeeded
    OR NOT profile.can_inflict_throwing_damage
    OR target_campaign_id<>manipulation.campaign_id
    OR attack_draw_count<>2
    OR invalid_attack_draw_count<>0
    OR NEW.skill_modifier<>expected_skill
    OR NEW.characteristic_modifier<>expected_characteristic
    OR NEW.difficulty_modifier<>expected_difficulty
    OR NEW.target_number<>expected_target
    OR NEW.attack_total<>attack_draw_total+expected_skill+
       expected_characteristic+expected_difficulty+
       NEW.circumstance_modifier_total
    OR NEW.damage_dice_count IS DISTINCT FROM
       profile.throwing_damage_dice_count
    OR NEW.damage_die_sides IS DISTINCT FROM
       profile.throwing_damage_die_sides
    OR (NEW.hit AND NEW.rolled_damage<>
       damage_draw_total+COALESCE(profile.throwing_damage_flat,0))
    OR (NEW.hit AND damage_draw_count<>
       COALESCE(profile.throwing_damage_dice_count,0))
    OR invalid_damage_draw_count<>0
    OR (NOT NEW.hit AND damage_draw_count<>0)
    OR (manipulation.target_kind='creature'
        AND NEW.thrown_creature_damage IS DISTINCT FROM NEW.raw_damage)
    OR (manipulation.target_kind='item'
        AND NEW.thrown_creature_damage IS NOT NULL)
    OR manipulation.target_actor_id=NEW.target_actor_id THEN
   RAISE EXCEPTION 'Telekinetic throw receipt is invalid';
 END IF;
 RETURN NEW;
END; $$;

CREATE TRIGGER cmd_psi_telekinetic_throw_valid
BEFORE INSERT ON cmd_psi_telekinetic_throw_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_validate_psi_telekinetic_throw();

CREATE TRIGGER cmd_psi_telekinetic_throw_immutable
BEFORE UPDATE OR DELETE ON cmd_psi_telekinetic_throw_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_psi_telekinetic_manipulation_mutation();

COMMENT ON TABLE cmd_psi_telekinetic_throw_receipt IS
    'CE-PSI-007 immutable Ranged (thrown), greater-distance, Effect-added impact audit.';
