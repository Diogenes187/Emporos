ALTER TABLE cmd_attack_receipt
    DROP CONSTRAINT cmd_attack_receipt_check;

ALTER TABLE cmd_attack_receipt
    ADD CONSTRAINT cmd_attack_receipt_damage_components_check CHECK (
        (
            hit
            AND raw_damage = rolled_damage + effect_damage
                + kill_aim_damage_bonus
        )
        OR (
            NOT hit
            AND rolled_damage = 0
            AND effect_damage = 0
            AND kill_aim_damage_bonus = 0
            AND raw_damage = 0
            AND penetrating_damage = 0
        )
    );
