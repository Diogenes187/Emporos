CREATE TABLE rule_personal_device_capability (
    device_rule_id bigint NOT NULL REFERENCES
        inv_personal_device_definition(item_rule_id),
    capability_code text NOT NULL CHECK (btrim(capability_code)<>''),
    range_metres integer CHECK (range_metres>0),
    range_is_approximate boolean,
    task_modifier integer,
    PRIMARY KEY (device_rule_id,capability_code),
    CHECK ((range_metres IS NULL)=(range_is_approximate IS NULL))
);

CREATE TABLE rule_personal_device_capability_skill (
    device_rule_id bigint NOT NULL,
    capability_code text NOT NULL,
    skill_rule_id bigint NOT NULL REFERENCES rule_skill(rule_id),
    PRIMARY KEY (device_rule_id,capability_code,skill_rule_id),
    FOREIGN KEY (device_rule_id,capability_code) REFERENCES
        rule_personal_device_capability(device_rule_id,capability_code)
);

CREATE TABLE rule_personal_holographic_projector_upgrade (
    device_rule_id bigint NOT NULL REFERENCES
        inv_personal_device_definition(item_rule_id),
    upgrade_tech_level integer NOT NULL CHECK (
        upgrade_tech_level IN (12,13)),
    cost_multiplier integer NOT NULL CHECK (cost_multiplier IN (2,10)),
    realism_code text NOT NULL CHECK (
        realism_code IN ('check-to-disbelieve','true-to-life')),
    intelligence_check_required boolean NOT NULL,
    PRIMARY KEY (device_rule_id,upgrade_tech_level),
    CHECK (
        (upgrade_tech_level=12 AND cost_multiplier=2
         AND realism_code='check-to-disbelieve'
         AND intelligence_check_required)
        OR
        (upgrade_tech_level=13 AND cost_multiplier=10
         AND realism_code='true-to-life'
         AND NOT intelligence_check_required))
);

COMMENT ON TABLE rule_personal_device_capability IS
    'CE-EQUIP-014 normalized Personal Device description capabilities.';
