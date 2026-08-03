CREATE TABLE rule_personal_reaction_option (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    reaction_kind text NOT NULL UNIQUE CHECK (reaction_kind IN ('dodge','parry')),
    attack_modifier smallint,
    cover_attack_modifier smallint,
    melee_attack_only boolean NOT NULL,
    weapon_bound boolean NOT NULL,
    uses_weapon_supported_melee_skill boolean NOT NULL,
    CHECK ((reaction_kind='dodge' AND attack_modifier=-1
            AND cover_attack_modifier=-2 AND NOT melee_attack_only
            AND NOT weapon_bound AND NOT uses_weapon_supported_melee_skill)
        OR (reaction_kind='parry' AND attack_modifier IS NULL
            AND cover_attack_modifier IS NULL AND melee_attack_only
            AND weapon_bound AND uses_weapon_supported_melee_skill))
);

ALTER TABLE cmd_personal_reaction_receipt
  ADD COLUMN parrying_weapon_rule_id bigint REFERENCES inv_weapon_definition(item_rule_id),
  ADD COLUMN parrying_weapon_item_instance_id bigint REFERENCES inv_item_instance(item_instance_id),
  ADD COLUMN parry_skill_rule_id bigint REFERENCES rule_skill(rule_id),
  ADD COLUMN parry_skill_modifier smallint,
  ADD CONSTRAINT cmd_personal_reaction_parry_snapshot CHECK (
    (reaction_kind='parry' AND parrying_weapon_rule_id IS NOT NULL
     AND parry_skill_rule_id IS NOT NULL AND parry_skill_modifier>=0)
    OR (reaction_kind<>'parry' AND parrying_weapon_rule_id IS NULL
        AND parrying_weapon_item_instance_id IS NULL
        AND parry_skill_rule_id IS NULL AND parry_skill_modifier IS NULL));

CREATE FUNCTION cmd_reject_personal_reaction_receipt_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Personal reaction receipts are immutable'; END; $$;
CREATE TRIGGER cmd_personal_reaction_receipt_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_reaction_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_personal_reaction_receipt_mutation();

COMMENT ON TABLE rule_personal_reaction_option IS
  'CE-COMBAT-025 paired-source Dodge and weapon-bound Parry mechanics.';
