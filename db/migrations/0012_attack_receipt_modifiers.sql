CREATE TABLE cmd_attack_modifier (
    command_id          bigint NOT NULL REFERENCES cmd_attack_receipt(command_id),
    modifier_order      smallint NOT NULL CHECK (modifier_order > 0),
    modifier_value      integer NOT NULL,
    PRIMARY KEY (command_id, modifier_order)
);

COMMENT ON TABLE cmd_attack_modifier IS
    'Ordered non-skill, non-characteristic, non-Difficulty attack modifiers.';
