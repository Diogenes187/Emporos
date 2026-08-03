CREATE TABLE rule_personal_burst_size (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    rounds_consumed smallint NOT NULL UNIQUE CHECK (
        rounds_consumed IN (3,4,10,20,100)
    ),
    attack_modifier integer NOT NULL CHECK (attack_modifier > 0),
    extra_damage_dice smallint NOT NULL CHECK (extra_damage_dice >= 0),
    extra_damage_flat smallint NOT NULL CHECK (extra_damage_flat >= 0),
    CHECK (
        (extra_damage_dice > 0 AND extra_damage_flat = 0)
        OR (extra_damage_dice = 0 AND extra_damage_flat > 0)
    )
);

CREATE TABLE rule_personal_burst_option (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    option_code text NOT NULL UNIQUE CHECK (
        option_code IN ('spray','grouped')
    ),
    applies_attack_modifier boolean NOT NULL,
    applies_extra_damage boolean NOT NULL,
    CHECK (applies_attack_modifier <> applies_extra_damage)
);

CREATE TABLE inv_weapon_burst_capability (
    weapon_rule_id bigint NOT NULL
        REFERENCES inv_weapon_definition(item_rule_id),
    burst_size_rule_id bigint NOT NULL
        REFERENCES rule_personal_burst_size(rule_id),
    PRIMARY KEY (weapon_rule_id,burst_size_rule_id)
);

ALTER TABLE enc_personal_attack
    ADD COLUMN burst_size_rule_id bigint
        REFERENCES rule_personal_burst_size(rule_id),
    ADD COLUMN burst_option_rule_id bigint
        REFERENCES rule_personal_burst_option(rule_id),
    ADD COLUMN burst_attack_modifier integer NOT NULL DEFAULT 0,
    ADD COLUMN burst_extra_damage_dice smallint NOT NULL DEFAULT 0 CHECK (
        burst_extra_damage_dice >= 0
    ),
    ADD COLUMN burst_extra_damage_flat smallint NOT NULL DEFAULT 0 CHECK (
        burst_extra_damage_flat >= 0
    ),
    ADD CONSTRAINT enc_personal_attack_burst_pair_check CHECK (
        (burst_size_rule_id IS NULL AND burst_option_rule_id IS NULL
         AND burst_attack_modifier=0 AND burst_extra_damage_dice=0
         AND burst_extra_damage_flat=0)
        OR
        (burst_size_rule_id IS NOT NULL AND burst_option_rule_id IS NOT NULL)
    );

ALTER TABLE cmd_attack_receipt
    ADD COLUMN burst_size_rule_id bigint
        REFERENCES rule_personal_burst_size(rule_id),
    ADD COLUMN burst_option_rule_id bigint
        REFERENCES rule_personal_burst_option(rule_id),
    ADD COLUMN burst_attack_modifier integer NOT NULL DEFAULT 0,
    ADD COLUMN burst_extra_damage_dice smallint NOT NULL DEFAULT 0 CHECK (
        burst_extra_damage_dice >= 0
    ),
    ADD COLUMN burst_extra_damage_flat smallint NOT NULL DEFAULT 0 CHECK (
        burst_extra_damage_flat >= 0
    ),
    ADD CONSTRAINT cmd_attack_receipt_burst_pair_check CHECK (
        (burst_size_rule_id IS NULL AND burst_option_rule_id IS NULL
         AND burst_attack_modifier=0 AND burst_extra_damage_dice=0
         AND burst_extra_damage_flat=0)
        OR
        (burst_size_rule_id IS NOT NULL AND burst_option_rule_id IS NOT NULL)
    ),
    DROP CONSTRAINT cmd_attack_receipt_damage_components_check,
    ADD CONSTRAINT cmd_attack_receipt_damage_components_check CHECK (
        (
            hit AND raw_damage=rolled_damage+effect_damage
                +kill_aim_damage_bonus+weapon_flat_damage_bonus
                +burst_extra_damage_flat
        )
        OR
        (
            NOT hit AND rolled_damage=0 AND effect_damage=0
            AND kill_aim_damage_bonus=0 AND weapon_flat_damage_bonus=0
            AND burst_extra_damage_flat=0
            AND raw_damage=0 AND penetrating_damage=0
        )
    );

CREATE FUNCTION enc_validate_personal_burst_attack()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    burst record;
    option_row record;
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
    IF NEW.ammunition_consumed<>burst.rounds_consumed THEN
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

CREATE TRIGGER enc_personal_attack_validate_burst
BEFORE INSERT OR UPDATE OF
    weapon_rule_id,ammunition_consumed,burst_size_rule_id,
    burst_option_rule_id,burst_attack_modifier,
    burst_extra_damage_dice,burst_extra_damage_flat
ON enc_personal_attack
FOR EACH ROW EXECUTE FUNCTION enc_validate_personal_burst_attack();

COMMENT ON TABLE rule_personal_burst_size IS
    'Published burst sizes and their mutually exclusive accuracy or damage benefit.';
COMMENT ON TABLE inv_weapon_burst_capability IS
    'Relational weapon-to-burst-size eligibility parsed from published rate of fire.';
