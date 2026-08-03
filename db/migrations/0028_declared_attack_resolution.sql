ALTER TABLE cmd_attack_receipt
    ADD COLUMN personal_attack_id bigint UNIQUE
        REFERENCES enc_personal_attack(personal_attack_id);

COMMENT ON COLUMN cmd_attack_receipt.personal_attack_id IS
    'When present, binds this mechanical roll to the declared attack and its reactions.';
