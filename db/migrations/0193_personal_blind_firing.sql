CREATE TABLE rule_personal_blind_fire (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    effective_skill_level smallint NOT NULL CHECK (effective_skill_level=0),
    attack_dice_rolled smallint NOT NULL CHECK (attack_dice_rolled=3),
    highest_attack_die_removed boolean NOT NULL CHECK (
        highest_attack_die_removed
    ),
    random_target_after_success boolean NOT NULL CHECK (
        random_target_after_success
    ),
    permits_friendly_targets boolean NOT NULL CHECK (
        permits_friendly_targets
    )
);

ALTER TABLE enc_personal_attack
    ADD COLUMN blind_fire boolean NOT NULL DEFAULT false;

CREATE TABLE enc_personal_blind_fire_target (
    personal_attack_id bigint NOT NULL
        REFERENCES enc_personal_attack(personal_attack_id),
    target_actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    target_order smallint NOT NULL CHECK (target_order>0),
    PRIMARY KEY (personal_attack_id,target_actor_id),
    UNIQUE (personal_attack_id,target_order)
);

CREATE FUNCTION enc_validate_personal_blind_fire_target()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE attack enc_personal_attack%ROWTYPE;
BEGIN
    SELECT * INTO STRICT attack FROM enc_personal_attack
    WHERE personal_attack_id=NEW.personal_attack_id;
    IF NOT attack.blind_fire THEN
        RAISE EXCEPTION 'Blind-fire roster requires a blind-fire attack';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM enc_personal_combatant
        WHERE encounter_id=attack.encounter_id
          AND actor_id=NEW.target_actor_id
    ) THEN
        RAISE EXCEPTION 'Blind-fire target must be an encounter combatant';
    END IF;
    IF NEW.target_actor_id=attack.attacker_actor_id THEN
        RAISE EXCEPTION 'Blind firer cannot be in their own firing line';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER enc_personal_blind_fire_target_validate
BEFORE INSERT OR UPDATE ON enc_personal_blind_fire_target
FOR EACH ROW EXECUTE FUNCTION enc_validate_personal_blind_fire_target();

CREATE TABLE cmd_personal_blind_fire_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_attack_receipt(command_id),
    personal_attack_id bigint NOT NULL UNIQUE
        REFERENCES enc_personal_attack(personal_attack_id),
    discarded_attack_die smallint NOT NULL CHECK (
        discarded_attack_die BETWEEN 1 AND 6
    ),
    eligible_target_count smallint NOT NULL CHECK (
        eligible_target_count>0
    ),
    selection_draw smallint CHECK (selection_draw>0),
    selected_target_actor_id bigint REFERENCES actor_actor(actor_id),
    CHECK (
        (selection_draw IS NULL)=(selected_target_actor_id IS NULL)
    ),
    CHECK (
        selection_draw IS NULL
        OR selection_draw<=eligible_target_count
    )
);

CREATE FUNCTION cmd_reject_blind_fire_receipt_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Blind-fire receipts are immutable'; END;
$$;
CREATE TRIGGER cmd_personal_blind_fire_receipt_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_blind_fire_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_blind_fire_receipt_mutation();

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
        'blind_target'
    )
);
ALTER TABLE cmd_random_draw DROP CONSTRAINT cmd_random_draw_die_sides_check;
ALTER TABLE cmd_random_draw ADD CONSTRAINT cmd_random_draw_die_sides_check CHECK (
    (draw_group='blind_target' AND die_sides>=1)
    OR (draw_group<>'blind_target' AND die_sides>1)
);

COMMENT ON TABLE enc_personal_blind_fire_target IS
    'CE-COMBAT-005 referee-declared firing-line eligibility roster.';
COMMENT ON TABLE cmd_personal_blind_fire_receipt IS
    'Immutable discarded die and success-only random target selection.';
