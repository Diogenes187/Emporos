CREATE TABLE rule_personal_robot_drone_framework (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    drone_control_skill_rule_id bigint NOT NULL REFERENCES rule_skill(rule_id),
    operates_in_combat_like_character boolean NOT NULL CHECK (
        operates_in_combat_like_character),
    takes_damage_like_vehicle boolean NOT NULL CHECK (
        takes_damage_like_vehicle),
    uses_hull_and_structure_instead_of_endurance boolean NOT NULL CHECK (
        uses_hull_and_structure_instead_of_endurance),
    endurance_dm integer NOT NULL CHECK (endurance_dm=0)
);

CREATE TABLE rule_personal_robot_drone_kind (
    framework_rule_id bigint NOT NULL REFERENCES
        rule_personal_robot_drone_framework(rule_id),
    kind_code text NOT NULL CHECK (kind_code IN ('robot','drone')),
    intellect_program_required boolean NOT NULL,
    remotely_controlled boolean NOT NULL,
    has_intelligence_and_education boolean NOT NULL,
    social_standing_mode text NOT NULL CHECK (
        social_standing_mode IN (
            'usually-zero-with-exceptions','operator-score-for-social-use')),
    PRIMARY KEY (framework_rule_id,kind_code),
    CHECK (
        (kind_code='robot' AND intellect_program_required
         AND NOT remotely_controlled AND has_intelligence_and_education
         AND social_standing_mode='usually-zero-with-exceptions')
        OR
        (kind_code='drone' AND NOT intellect_program_required
         AND remotely_controlled AND NOT has_intelligence_and_education
         AND social_standing_mode='operator-score-for-social-use'))
);

COMMENT ON TABLE rule_personal_robot_drone_framework IS
    'CE-EQUIP-015 paired-source robot and drone shared rules.';
