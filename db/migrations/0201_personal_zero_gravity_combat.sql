CREATE TABLE rule_personal_zero_gravity_combat (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    zero_g_skill_rule_id bigint NOT NULL REFERENCES rule_skill(rule_id),
    missing_zero_g_uses_untrained boolean NOT NULL CHECK (
        missing_zero_g_uses_untrained
    ),
    skill_cap_uses_lower boolean NOT NULL CHECK (skill_cap_uses_lower),
    recoil_attack_modifier smallint NOT NULL CHECK (
        recoil_attack_modifier=-2
    )
);

ALTER TABLE enc_personal_battlefield_condition
    ADD COLUMN gravity_code text NOT NULL DEFAULT 'normal-gravity' CHECK (
        gravity_code IN ('normal-gravity','zero-gravity')
    );
ALTER TABLE cmd_personal_battlefield_condition_receipt
    ADD COLUMN gravity_before text NOT NULL DEFAULT 'normal-gravity' CHECK (
        gravity_before IN ('normal-gravity','zero-gravity')
    ),
    ADD COLUMN gravity_after text NOT NULL DEFAULT 'normal-gravity' CHECK (
        gravity_after IN ('normal-gravity','zero-gravity')
    );

ALTER TABLE enc_personal_attack
    ADD COLUMN zero_gravity boolean NOT NULL DEFAULT false,
    ADD COLUMN zero_gravity_weapon_skill_level integer,
    ADD COLUMN zero_gravity_trained boolean,
    ADD COLUMN zero_gravity_skill_level integer,
    ADD COLUMN zero_gravity_effective_skill_level integer,
    ADD COLUMN zero_gravity_weapon_has_recoil boolean,
    ADD COLUMN zero_gravity_recoil_modifier smallint NOT NULL DEFAULT 0,
    ADD CONSTRAINT enc_personal_attack_zero_gravity_check CHECK (
        (
            NOT zero_gravity
            AND zero_gravity_weapon_skill_level IS NULL
            AND zero_gravity_trained IS NULL
            AND zero_gravity_skill_level IS NULL
            AND zero_gravity_effective_skill_level IS NULL
            AND zero_gravity_weapon_has_recoil IS NULL
            AND zero_gravity_recoil_modifier=0
        )
        OR (
            zero_gravity
            AND zero_gravity_weapon_skill_level IS NOT NULL
            AND zero_gravity_trained IS NOT NULL
            AND (
                (zero_gravity_trained
                 AND zero_gravity_skill_level>=0
                 AND zero_gravity_effective_skill_level=
                     LEAST(zero_gravity_weapon_skill_level,
                           zero_gravity_skill_level))
                OR
                (NOT zero_gravity_trained
                 AND zero_gravity_skill_level IS NULL
                 AND zero_gravity_effective_skill_level=-3)
            )
            AND zero_gravity_weapon_has_recoil IS NOT NULL
            AND zero_gravity_recoil_modifier=CASE
                WHEN zero_gravity_weapon_has_recoil THEN -2 ELSE 0 END
        )
    );

CREATE TABLE cmd_personal_zero_gravity_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_attack_receipt(command_id),
    personal_attack_id bigint NOT NULL UNIQUE
        REFERENCES enc_personal_attack(personal_attack_id),
    weapon_skill_level integer NOT NULL,
    zero_g_trained boolean NOT NULL,
    zero_g_skill_level integer,
    effective_skill_level integer NOT NULL,
    weapon_has_recoil boolean NOT NULL,
    recoil_modifier smallint NOT NULL,
    CHECK ((zero_g_trained AND zero_g_skill_level>=0)
           OR (NOT zero_g_trained AND zero_g_skill_level IS NULL)),
    CHECK (recoil_modifier=CASE WHEN weapon_has_recoil THEN -2 ELSE 0 END)
);

CREATE FUNCTION cmd_reject_zero_gravity_receipt_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Zero-gravity receipts are immutable'; END;
$$;
CREATE TRIGGER cmd_personal_zero_gravity_receipt_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_zero_gravity_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_zero_gravity_receipt_mutation();

COMMENT ON TABLE rule_personal_zero_gravity_combat IS
    'Fighting in Zero Gravity mechanics and CE-COMBAT-008 interpretation.';
