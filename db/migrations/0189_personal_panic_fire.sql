CREATE TABLE rule_personal_panic_fire (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    attack_modifier integer NOT NULL CHECK (attack_modifier < 0),
    consumes_all_remaining boolean NOT NULL CHECK (consumes_all_remaining),
    damage_only_burst_fire boolean NOT NULL CHECK (damage_only_burst_fire),
    tier_selection_code text NOT NULL CHECK (
        tier_selection_code='greatest-not-exceeding'
    )
);

CREATE TABLE inv_weapon_panic_fire_capability (
    weapon_rule_id bigint PRIMARY KEY
        REFERENCES inv_weapon_definition(item_rule_id),
    eligibility_basis text NOT NULL CHECK (
        eligibility_basis IN ('slug-pistol','slug-rifle')
    )
);

ALTER TABLE enc_personal_attack
    ADD COLUMN panic_fire boolean NOT NULL DEFAULT false,
    ADD COLUMN panic_attack_modifier integer NOT NULL DEFAULT 0,
    ADD COLUMN panic_damage_burst_size_rule_id bigint
        REFERENCES rule_personal_burst_size(rule_id),
    ADD COLUMN panic_extra_damage_dice smallint NOT NULL DEFAULT 0 CHECK (
        panic_extra_damage_dice >= 0
    ),
    ADD COLUMN panic_extra_damage_flat smallint NOT NULL DEFAULT 0 CHECK (
        panic_extra_damage_flat >= 0
    ),
    ADD CONSTRAINT enc_personal_attack_panic_check CHECK (
        (NOT panic_fire AND panic_attack_modifier=0
         AND panic_damage_burst_size_rule_id IS NULL
         AND panic_extra_damage_dice=0 AND panic_extra_damage_flat=0)
        OR
        (panic_fire AND panic_attack_modifier<0
         AND NOT suppression_fire AND burst_size_rule_id IS NULL)
    );

ALTER TABLE cmd_attack_receipt
    ADD COLUMN panic_fire boolean NOT NULL DEFAULT false,
    ADD COLUMN panic_attack_modifier integer NOT NULL DEFAULT 0,
    ADD COLUMN panic_damage_burst_size_rule_id bigint
        REFERENCES rule_personal_burst_size(rule_id),
    ADD COLUMN panic_extra_damage_dice smallint NOT NULL DEFAULT 0 CHECK (
        panic_extra_damage_dice >= 0
    ),
    ADD COLUMN panic_extra_damage_flat smallint NOT NULL DEFAULT 0 CHECK (
        panic_extra_damage_flat >= 0
    ),
    ADD CONSTRAINT cmd_attack_receipt_panic_check CHECK (
        (NOT panic_fire AND panic_attack_modifier=0
         AND panic_damage_burst_size_rule_id IS NULL
         AND panic_extra_damage_dice=0 AND panic_extra_damage_flat=0)
        OR (panic_fire AND panic_attack_modifier<0)
    ),
    DROP CONSTRAINT cmd_attack_receipt_damage_components_check,
    ADD CONSTRAINT cmd_attack_receipt_damage_components_check CHECK (
        (
            hit AND raw_damage=rolled_damage+effect_damage
                +kill_aim_damage_bonus+weapon_flat_damage_bonus
                +burst_extra_damage_flat+panic_extra_damage_flat
        )
        OR
        (
            NOT hit AND rolled_damage=0 AND effect_damage=0
            AND kill_aim_damage_bonus=0 AND weapon_flat_damage_bonus=0
            AND burst_extra_damage_flat=0 AND panic_extra_damage_flat=0
            AND raw_damage=0 AND penetrating_damage=0
        )
    );

CREATE TABLE cmd_personal_panic_fire_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    personal_attack_id bigint NOT NULL UNIQUE
        REFERENCES enc_personal_attack(personal_attack_id),
    ammunition_consumed integer NOT NULL CHECK (ammunition_consumed > 0),
    damage_burst_size_rule_id bigint
        REFERENCES rule_personal_burst_size(rule_id),
    extra_damage_dice smallint NOT NULL CHECK (extra_damage_dice >= 0),
    extra_damage_flat smallint NOT NULL CHECK (extra_damage_flat >= 0)
);

CREATE FUNCTION enc_validate_panic_attack()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    rules rule_personal_panic_fire%ROWTYPE;
    tier rule_personal_burst_size%ROWTYPE;
BEGIN
    IF NOT NEW.panic_fire THEN RETURN NEW; END IF;
    SELECT * INTO STRICT rules FROM rule_personal_panic_fire;
    IF NOT EXISTS (
        SELECT 1 FROM inv_weapon_panic_fire_capability
        WHERE weapon_rule_id=NEW.weapon_rule_id
    ) THEN
        RAISE EXCEPTION 'weapon is not a small-arms slug thrower';
    END IF;
    IF NEW.panic_attack_modifier<>rules.attack_modifier THEN
        RAISE EXCEPTION 'panic-fire attack modifier changed';
    END IF;
    IF NEW.panic_damage_burst_size_rule_id IS NULL THEN
        IF NEW.ammunition_consumed>=3
           OR NEW.panic_extra_damage_dice<>0
           OR NEW.panic_extra_damage_flat<>0 THEN
            RAISE EXCEPTION 'panic-fire damage tier is missing';
        END IF;
    ELSE
        SELECT * INTO STRICT tier FROM rule_personal_burst_size
        WHERE rule_id=NEW.panic_damage_burst_size_rule_id;
        IF tier.rounds_consumed>NEW.ammunition_consumed
           OR EXISTS (
               SELECT 1 FROM rule_personal_burst_size larger
               WHERE larger.rounds_consumed<=NEW.ammunition_consumed
                 AND larger.rounds_consumed>tier.rounds_consumed
           )
           OR NEW.panic_extra_damage_dice<>tier.extra_damage_dice
           OR NEW.panic_extra_damage_flat<>tier.extra_damage_flat THEN
            RAISE EXCEPTION 'panic-fire damage tier is not the greatest eligible tier';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER enc_personal_attack_validate_panic
BEFORE INSERT OR UPDATE OF panic_fire,weapon_rule_id,ammunition_consumed,
    panic_attack_modifier,panic_damage_burst_size_rule_id,
    panic_extra_damage_dice,panic_extra_damage_flat
ON enc_personal_attack
FOR EACH ROW EXECUTE FUNCTION enc_validate_panic_attack();

CREATE FUNCTION cmd_reject_panic_receipt_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Panic-fire receipts are immutable';
END;
$$;

CREATE TRIGGER cmd_personal_panic_fire_receipt_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_panic_fire_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_panic_receipt_mutation();

COMMENT ON TABLE rule_personal_panic_fire IS
    'Paired-source panic fire plus the agreed intermediate-round tier ruling.';
COMMENT ON TABLE cmd_personal_panic_fire_receipt IS
    'Immutable panic-fire ammunition and selected damage-tier facts.';
