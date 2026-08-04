INSERT INTO cmd_command_type VALUES
    ('reroll_characteristics','Reroll initial characteristics');

INSERT INTO cmd_domain_event_type VALUES
    ('characteristics_rerolled','Initial characteristics rerolled');

CREATE TABLE cmd_characteristic_reroll_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    actor_version_before bigint NOT NULL CHECK (actor_version_before>0),
    actor_version_after bigint NOT NULL CHECK (
        actor_version_after=actor_version_before+1
    )
);

CREATE TABLE cmd_characteristic_reroll_score (
    command_id bigint NOT NULL REFERENCES
        cmd_characteristic_reroll_receipt(command_id),
    characteristic_rule_id bigint NOT NULL REFERENCES
        rule_characteristic(rule_id),
    display_order smallint NOT NULL CHECK (display_order>0),
    prior_score smallint NOT NULL CHECK (prior_score>=0),
    dice_total smallint NOT NULL CHECK (dice_total>0),
    resulting_score smallint NOT NULL CHECK (resulting_score>=0),
    PRIMARY KEY (command_id,characteristic_rule_id),
    UNIQUE (command_id,display_order)
);

COMMENT ON TABLE cmd_characteristic_reroll_receipt IS
    'Audited pre-career rerolls of all initial characteristics.';
