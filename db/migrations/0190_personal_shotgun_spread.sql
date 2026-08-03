CREATE TABLE rule_personal_shotgun_spread (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    attack_modifier integer NOT NULL CHECK (attack_modifier=1),
    damage_dice smallint NOT NULL CHECK (damage_dice=2),
    minimum_range_rule_id bigint NOT NULL REFERENCES combat_range_band(rule_id),
    maximum_range_rule_id bigint NOT NULL REFERENCES combat_range_band(rule_id),
    affects_personal_range_bystanders boolean NOT NULL CHECK (
        affects_personal_range_bystanders
    ),
    shared_attack_roll boolean NOT NULL CHECK (shared_attack_roll),
    shared_damage_roll boolean NOT NULL CHECK (shared_damage_roll),
    armor_resolved_individually boolean NOT NULL CHECK (
        armor_resolved_individually
    )
);

CREATE TABLE inv_weapon_shotgun_spread_capability (
    weapon_rule_id bigint NOT NULL
        REFERENCES inv_weapon_definition(item_rule_id),
    ammunition_rule_id bigint NOT NULL
        REFERENCES inv_ammunition_definition(ammunition_rule_id),
    PRIMARY KEY (weapon_rule_id,ammunition_rule_id)
);

ALTER TABLE enc_personal_attack
    ADD COLUMN shotgun_spread boolean NOT NULL DEFAULT false,
    ADD COLUMN shotgun_spread_attack_modifier integer NOT NULL DEFAULT 0,
    ADD COLUMN shotgun_spread_damage_dice smallint,
    ADD CONSTRAINT enc_personal_attack_shotgun_spread_check CHECK (
        (NOT shotgun_spread AND shotgun_spread_attack_modifier=0
         AND shotgun_spread_damage_dice IS NULL)
        OR (shotgun_spread AND shotgun_spread_attack_modifier=1
            AND shotgun_spread_damage_dice=2
            AND NOT suppression_fire AND NOT panic_fire
            AND burst_size_rule_id IS NULL)
    );

CREATE TABLE enc_personal_shotgun_spread_target (
    personal_attack_id bigint NOT NULL
        REFERENCES enc_personal_attack(personal_attack_id),
    target_actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    target_order smallint NOT NULL CHECK (target_order>0),
    is_primary boolean NOT NULL,
    personal_range_to_primary_asserted boolean NOT NULL,
    PRIMARY KEY (personal_attack_id,target_actor_id),
    UNIQUE (personal_attack_id,target_order),
    CHECK (is_primary OR personal_range_to_primary_asserted)
);

CREATE FUNCTION enc_validate_shotgun_spread_target()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE attack enc_personal_attack%ROWTYPE;
BEGIN
    SELECT * INTO STRICT attack FROM enc_personal_attack
    WHERE personal_attack_id=NEW.personal_attack_id;
    IF NOT attack.shotgun_spread THEN
        RAISE EXCEPTION 'spread target requires a shotgun-spread attack';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM enc_personal_combatant
        WHERE encounter_id=attack.encounter_id AND actor_id=NEW.target_actor_id
    ) THEN RAISE EXCEPTION 'spread target is not an encounter combatant';
    END IF;
    IF NEW.is_primary<>(NEW.target_actor_id=attack.target_actor_id) THEN
        RAISE EXCEPTION 'spread primary target does not match attack';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER enc_personal_shotgun_spread_target_validate
BEFORE INSERT OR UPDATE ON enc_personal_shotgun_spread_target
FOR EACH ROW EXECUTE FUNCTION enc_validate_shotgun_spread_target();

ALTER TABLE cmd_attack_receipt
    ADD COLUMN shotgun_spread boolean NOT NULL DEFAULT false,
    ADD COLUMN shotgun_spread_attack_modifier integer NOT NULL DEFAULT 0,
    ADD COLUMN shotgun_spread_damage_dice smallint,
    ADD CONSTRAINT cmd_attack_receipt_shotgun_spread_check CHECK (
        (NOT shotgun_spread AND shotgun_spread_attack_modifier=0
         AND shotgun_spread_damage_dice IS NULL)
        OR (shotgun_spread AND shotgun_spread_attack_modifier=1
            AND shotgun_spread_damage_dice=2)
    );

CREATE TABLE cmd_personal_shotgun_spread_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    personal_attack_id bigint NOT NULL UNIQUE
        REFERENCES enc_personal_attack(personal_attack_id),
    shared_attack_roll boolean NOT NULL CHECK (shared_attack_roll),
    shared_damage_roll boolean NOT NULL CHECK (shared_damage_roll),
    affected_target_count smallint NOT NULL CHECK (affected_target_count>0)
);

CREATE TABLE cmd_personal_shotgun_spread_target_receipt (
    command_id bigint NOT NULL
        REFERENCES cmd_personal_shotgun_spread_receipt(command_id),
    target_actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    target_order smallint NOT NULL CHECK (target_order>0),
    is_primary boolean NOT NULL,
    armor_rule_id bigint NOT NULL REFERENCES inv_armor_definition(item_rule_id),
    armor_rating integer NOT NULL CHECK (armor_rating>=0),
    raw_damage integer NOT NULL CHECK (raw_damage>=0),
    penetrating_damage integer NOT NULL CHECK (penetrating_damage>=0),
    damage_instance_id bigint REFERENCES health_damage_instance(
        damage_instance_id
    ),
    PRIMARY KEY (command_id,target_actor_id),
    UNIQUE (command_id,target_order)
);

ALTER TABLE health_damage_instance
    DROP CONSTRAINT health_damage_instance_attack_command_id_key,
    ADD CONSTRAINT health_damage_instance_attack_target_unique
        UNIQUE (attack_command_id,target_actor_id);

CREATE FUNCTION enc_validate_shotgun_spread_attack()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE rules rule_personal_shotgun_spread%ROWTYPE;
BEGIN
    IF NOT NEW.shotgun_spread THEN RETURN NEW; END IF;
    SELECT * INTO STRICT rules FROM rule_personal_shotgun_spread;
    IF NEW.range_band_rule_id NOT IN (
        rules.minimum_range_rule_id,rules.maximum_range_rule_id
    ) THEN RAISE EXCEPTION 'shotgun spread requires Medium or Long range';
    END IF;
    IF NEW.shotgun_spread_attack_modifier<>rules.attack_modifier
       OR NEW.shotgun_spread_damage_dice<>rules.damage_dice THEN
        RAISE EXCEPTION 'shotgun spread modifiers changed';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER enc_personal_attack_validate_shotgun_spread
BEFORE INSERT OR UPDATE OF shotgun_spread,range_band_rule_id,
 shotgun_spread_attack_modifier,shotgun_spread_damage_dice
ON enc_personal_attack FOR EACH ROW
EXECUTE FUNCTION enc_validate_shotgun_spread_attack();

CREATE FUNCTION cmd_reject_shotgun_spread_receipt_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Shotgun-spread receipts are immutable'; END;
$$;

CREATE TRIGGER cmd_personal_shotgun_spread_receipt_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_shotgun_spread_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_shotgun_spread_receipt_mutation();
CREATE TRIGGER cmd_personal_shotgun_spread_target_receipt_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_shotgun_spread_target_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_shotgun_spread_receipt_mutation();
