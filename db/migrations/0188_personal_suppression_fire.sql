CREATE TABLE rule_personal_suppression_fire (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    attack_modifier integer NOT NULL CHECK (attack_modifier < 0),
    ammunition_multiplier smallint NOT NULL CHECK (ammunition_multiplier > 1),
    check_modifier integer NOT NULL CHECK (check_modifier < 0),
    duration_rounds smallint NOT NULL CHECK (duration_rounds >= 1),
    initiative_penalty_uses_effect boolean NOT NULL,
    highest_effect_only boolean NOT NULL,
    requires_intervening_action boolean NOT NULL
);

CREATE TABLE rule_personal_suppression_immunity (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    immunity_code text NOT NULL UNIQUE
);

ALTER TABLE enc_personal_attack
    ADD COLUMN suppression_fire boolean NOT NULL DEFAULT false,
    ADD COLUMN suppression_attack_modifier integer NOT NULL DEFAULT 0,
    ADD CONSTRAINT enc_personal_attack_suppression_modifier_check CHECK (
        (suppression_fire AND suppression_attack_modifier < 0)
        OR (NOT suppression_fire AND suppression_attack_modifier = 0)
    );

ALTER TABLE enc_personal_combatant
    ADD COLUMN suppression_check_modifier integer NOT NULL DEFAULT 0,
    ADD COLUMN suppression_expires_after_round integer,
    ADD COLUMN suppression_action_required boolean NOT NULL DEFAULT false,
    ADD CONSTRAINT enc_personal_combatant_suppression_check CHECK (
        (suppression_check_modifier=0
         AND suppression_expires_after_round IS NULL
         AND NOT suppression_action_required)
        OR
        (suppression_check_modifier<0
         AND suppression_expires_after_round IS NOT NULL)
    );

ALTER TABLE cmd_attack_receipt
    ADD COLUMN suppression_fire boolean NOT NULL DEFAULT false,
    ADD COLUMN suppression_attack_modifier integer NOT NULL DEFAULT 0,
    ADD CONSTRAINT cmd_attack_receipt_suppression_modifier_check CHECK (
        (suppression_fire AND suppression_attack_modifier < 0)
        OR (NOT suppression_fire AND suppression_attack_modifier = 0)
    );

CREATE OR REPLACE FUNCTION enc_validate_personal_burst_attack()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    burst record;
    option_row record;
    expected_ammunition integer;
BEGIN
    IF NEW.burst_size_rule_id IS NULL THEN
        RETURN NEW;
    END IF;
    SELECT * INTO burst FROM rule_personal_burst_size
    WHERE rule_id=NEW.burst_size_rule_id;
    SELECT * INTO option_row FROM rule_personal_burst_option
    WHERE rule_id=NEW.burst_option_rule_id;
    IF NOT EXISTS (
        SELECT 1 FROM inv_weapon_burst_capability
        WHERE weapon_rule_id=NEW.weapon_rule_id
          AND burst_size_rule_id=NEW.burst_size_rule_id
    ) THEN
        RAISE EXCEPTION 'weapon does not support selected burst size';
    END IF;
    expected_ammunition := burst.rounds_consumed;
    IF NEW.suppression_fire THEN
        expected_ammunition := expected_ammunition * (
            SELECT ammunition_multiplier
            FROM rule_personal_suppression_fire
        );
    END IF;
    IF NEW.ammunition_consumed<>expected_ammunition THEN
        RAISE EXCEPTION 'burst ammunition does not match burst size';
    END IF;
    IF NEW.burst_attack_modifier <> (
           CASE WHEN option_row.applies_attack_modifier
                THEN burst.attack_modifier ELSE 0 END
       )
       OR NEW.burst_extra_damage_dice <> (
           CASE WHEN option_row.applies_extra_damage
                THEN burst.extra_damage_dice ELSE 0 END
       )
       OR NEW.burst_extra_damage_flat <> (
           CASE WHEN option_row.applies_extra_damage
                THEN burst.extra_damage_flat ELSE 0 END
       ) THEN
        RAISE EXCEPTION 'burst modifiers do not match selected option';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TABLE enc_personal_suppression_immunity (
    encounter_id bigint NOT NULL,
    actor_id bigint NOT NULL,
    immunity_rule_id bigint NOT NULL
        REFERENCES rule_personal_suppression_immunity(rule_id),
    PRIMARY KEY (encounter_id,actor_id,immunity_rule_id),
    FOREIGN KEY (encounter_id,actor_id)
        REFERENCES enc_personal_combatant(encounter_id,actor_id)
);

CREATE TABLE cmd_personal_suppression_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    personal_attack_id bigint NOT NULL UNIQUE
        REFERENCES enc_personal_attack(personal_attack_id),
    target_actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    immune boolean NOT NULL,
    applied boolean NOT NULL,
    effect integer NOT NULL,
    initiative_before integer NOT NULL,
    initiative_after integer NOT NULL,
    check_modifier_before integer NOT NULL,
    check_modifier_after integer NOT NULL,
    expires_after_round integer,
    CONSTRAINT suppression_receipt_result_check CHECK (
        (applied AND NOT immune AND effect >= 0
         AND initiative_after=initiative_before-effect
         AND check_modifier_after < 0
         AND expires_after_round IS NOT NULL)
        OR
        (NOT applied AND initiative_after=initiative_before
         AND check_modifier_after=check_modifier_before)
    )
);

CREATE FUNCTION cmd_reject_suppression_receipt_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Suppression-fire receipts are immutable';
END;
$$;

CREATE TRIGGER cmd_personal_suppression_receipt_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_suppression_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_suppression_receipt_mutation();

CREATE FUNCTION enc_clear_suppression_gate_after_action()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.suppression_action_required AND (
        NEW.significant_actions_remaining < OLD.significant_actions_remaining
        OR NEW.minor_actions_remaining < OLD.minor_actions_remaining
    ) THEN
        NEW.suppression_action_required := false;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER enc_personal_combatant_clear_suppression_gate
BEFORE UPDATE OF significant_actions_remaining,minor_actions_remaining
ON enc_personal_combatant
FOR EACH ROW EXECUTE FUNCTION enc_clear_suppression_gate_after_action();

CREATE FUNCTION enc_validate_suppression_attack()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    rules rule_personal_suppression_fire%ROWTYPE;
BEGIN
    IF NOT NEW.suppression_fire THEN RETURN NEW; END IF;
    SELECT * INTO STRICT rules FROM rule_personal_suppression_fire;
    IF NEW.attack_profile_code IN ('close-quarters','natural-weapon','thrown') THEN
        RAISE EXCEPTION 'suppression fire requires a shooting attack';
    END IF;
    IF NEW.burst_option_rule_id IS NOT NULL AND EXISTS (
        SELECT 1 FROM rule_personal_burst_option
        WHERE rule_id=NEW.burst_option_rule_id AND option_code<>'spray'
    ) THEN
        RAISE EXCEPTION 'suppression fire cannot use grouped burst damage';
    END IF;
    IF NEW.ammunition_consumed < rules.ammunition_multiplier THEN
        RAISE EXCEPTION 'suppression fire must consume double ammunition';
    END IF;
    IF NEW.suppression_attack_modifier<>rules.attack_modifier THEN
        RAISE EXCEPTION 'suppression modifier does not match published rule';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER enc_personal_attack_validate_suppression
BEFORE INSERT OR UPDATE OF suppression_fire,attack_profile_code,
    ammunition_consumed ON enc_personal_attack
FOR EACH ROW EXECUTE FUNCTION enc_validate_suppression_attack();

COMMENT ON TABLE rule_personal_suppression_fire IS
    'Normalized paired-source suppression-fire procedure.';
COMMENT ON TABLE cmd_personal_suppression_receipt IS
    'Immutable outcome facts for a resolved suppression attack.';
