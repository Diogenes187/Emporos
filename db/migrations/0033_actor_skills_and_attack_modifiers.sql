CREATE TABLE actor_skill (
    actor_id            bigint NOT NULL REFERENCES actor_actor(actor_id),
    skill_rule_id       bigint NOT NULL REFERENCES rule_skill(rule_id),
    skill_level         smallint NOT NULL CHECK (skill_level >= 0),
    PRIMARY KEY (actor_id, skill_rule_id)
);

ALTER TABLE enc_personal_attack
    ADD COLUMN characteristic_rule_id bigint
        REFERENCES rule_characteristic(rule_id);

UPDATE enc_personal_attack attack
SET characteristic_rule_id=rule.rule_id
FROM rule_rule rule
WHERE rule.rule_code='characteristic.dexterity'
  AND attack.characteristic_rule_id IS NULL;

ALTER TABLE enc_personal_attack
    ALTER COLUMN characteristic_rule_id SET NOT NULL;

COMMENT ON TABLE actor_skill IS
    'Player-editable canonical actor skill levels; absence means untrained.';
COMMENT ON COLUMN enc_personal_attack.characteristic_rule_id IS
    'Characteristic selected when the attack is declared, before reactions.';
