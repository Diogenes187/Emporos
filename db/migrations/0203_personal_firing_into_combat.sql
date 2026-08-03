CREATE TABLE rule_personal_firing_into_combat (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    attack_modifier smallint NOT NULL CHECK (attack_modifier=-2),
    scatter_die_sides smallint NOT NULL CHECK (scatter_die_sides=6),
    scatter_hit_minimum smallint NOT NULL CHECK (scatter_hit_minimum=4),
    nearest_only boolean NOT NULL CHECK (nearest_only),
    permits_friendly_targets boolean NOT NULL CHECK (
        permits_friendly_targets
    ),
    redirected_uses_original_effect boolean NOT NULL CHECK (
        redirected_uses_original_effect
    ),
    redirected_excludes_kill_aim boolean NOT NULL CHECK (
        redirected_excludes_kill_aim
    )
);

ALTER TABLE enc_personal_attack
    ADD COLUMN firing_into_combat boolean NOT NULL DEFAULT false,
    ADD COLUMN firing_into_combat_attack_modifier smallint NOT NULL DEFAULT 0,
    ADD CONSTRAINT enc_personal_attack_firing_into_combat_check CHECK (
        (firing_into_combat AND firing_into_combat_attack_modifier=-2)
        OR (NOT firing_into_combat
            AND firing_into_combat_attack_modifier=0)
    );

CREATE TABLE enc_personal_firing_into_combat_target (
    personal_attack_id bigint NOT NULL
        REFERENCES enc_personal_attack(personal_attack_id),
    target_actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    proximity_tier smallint NOT NULL CHECK (proximity_tier>0),
    target_order smallint NOT NULL CHECK (target_order>0),
    PRIMARY KEY (personal_attack_id,target_actor_id),
    UNIQUE (personal_attack_id,target_order)
);

CREATE FUNCTION enc_validate_firing_into_combat_target()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE attack enc_personal_attack%ROWTYPE;
BEGIN
 SELECT * INTO STRICT attack FROM enc_personal_attack
  WHERE personal_attack_id=NEW.personal_attack_id;
 IF NOT attack.firing_into_combat
    OR NEW.target_actor_id IN (
        attack.attacker_actor_id,attack.target_actor_id)
    OR NOT EXISTS (
        SELECT 1 FROM enc_personal_combatant
         WHERE encounter_id=attack.encounter_id
           AND actor_id=NEW.target_actor_id) THEN
   RAISE EXCEPTION 'Invalid Firing into Combat proximity target';
 END IF;
 RETURN NEW;
END;
$$;
CREATE TRIGGER enc_personal_firing_into_combat_target_validate
BEFORE INSERT OR UPDATE ON enc_personal_firing_into_combat_target
FOR EACH ROW EXECUTE FUNCTION enc_validate_firing_into_combat_target();

CREATE TABLE cmd_personal_firing_into_combat_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_attack_receipt(command_id),
    personal_attack_id bigint NOT NULL UNIQUE
        REFERENCES enc_personal_attack(personal_attack_id),
    original_target_actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    original_attack_hit boolean NOT NULL,
    scatter_roll smallint,
    redirected boolean NOT NULL,
    nearest_tier smallint,
    nearest_tie_count smallint,
    tie_selection_draw smallint,
    selected_target_actor_id bigint REFERENCES actor_actor(actor_id),
    original_effect integer NOT NULL,
    kill_aim_damage_excluded integer NOT NULL CHECK (
        kill_aim_damage_excluded>=0
    ),
    CHECK (
        (original_attack_hit AND scatter_roll IS NULL AND NOT redirected
         AND nearest_tier IS NULL AND nearest_tie_count IS NULL
         AND tie_selection_draw IS NULL
         AND selected_target_actor_id IS NULL)
        OR
        (NOT original_attack_hit AND scatter_roll BETWEEN 1 AND 3
         AND NOT redirected AND nearest_tier IS NULL
         AND nearest_tie_count IS NULL AND tie_selection_draw IS NULL
         AND selected_target_actor_id IS NULL)
        OR
        (NOT original_attack_hit AND scatter_roll BETWEEN 4 AND 6
         AND redirected AND nearest_tier>0 AND nearest_tie_count>0
         AND selected_target_actor_id IS NOT NULL
         AND ((nearest_tie_count=1 AND tie_selection_draw IS NULL)
              OR (nearest_tie_count>1
                  AND tie_selection_draw BETWEEN 1 AND nearest_tie_count)))
    )
);

CREATE FUNCTION cmd_reject_firing_into_combat_receipt_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Firing into Combat receipts are immutable'; END;
$$;
CREATE TRIGGER cmd_personal_firing_into_combat_receipt_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_firing_into_combat_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_firing_into_combat_receipt_mutation();

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
        'combat_scatter','combat_nearest_tie'
    )
);

COMMENT ON TABLE enc_personal_firing_into_combat_target IS
    'CE-COMBAT-009 frozen Personal-range proximity tiers.';
