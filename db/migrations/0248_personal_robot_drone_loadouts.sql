CREATE TABLE inv_personal_robot_drone_system (
    chassis_rule_id bigint NOT NULL REFERENCES
        inv_personal_robot_drone_chassis(item_rule_id),
    system_code text NOT NULL,
    minimum_tech_level integer,
    quantity integer NOT NULL DEFAULT 1 CHECK (quantity>0),
    selection_scope text,
    PRIMARY KEY (chassis_rule_id,system_code),
    CHECK (minimum_tech_level IS NULL OR minimum_tech_level>=0)
);

CREATE TABLE inv_personal_robot_drone_program (
    chassis_rule_id bigint NOT NULL REFERENCES
        inv_personal_robot_drone_chassis(item_rule_id),
    program_order integer NOT NULL CHECK (program_order>0),
    software_rule_id bigint REFERENCES rule_personal_software_family(rule_id),
    printed_program_name text NOT NULL CHECK (btrim(printed_program_name)<>''),
    rating integer CHECK (rating>=0),
    expert_skill_rule_id bigint REFERENCES rule_skill(rule_id),
    printed_specialization text,
    program_status text NOT NULL CHECK (
        program_status IN (
            'installed','alternative','available-on-demand',
            'reprogram-option')),
    alternative_to_program_order integer,
    PRIMARY KEY (chassis_rule_id,program_order),
    CHECK (
        (program_status='alternative'
         AND alternative_to_program_order IS NOT NULL AND rating IS NOT NULL)
        OR
        (program_status IN ('installed','available-on-demand')
         AND alternative_to_program_order IS NULL AND rating IS NOT NULL)
        OR
        (program_status='reprogram-option'
         AND alternative_to_program_order IS NULL AND rating IS NULL))
);

CREATE TABLE inv_personal_robot_drone_weapon (
    chassis_rule_id bigint NOT NULL REFERENCES
        inv_personal_robot_drone_chassis(item_rule_id),
    weapon_order integer NOT NULL CHECK (weapon_order>0),
    weapon_name text NOT NULL CHECK (btrim(weapon_name)<>''),
    printed_skill_name text NOT NULL CHECK (btrim(printed_skill_name)<>''),
    skill_rule_id bigint REFERENCES rule_skill(rule_id),
    damage_dice_count integer CHECK (damage_dice_count>0),
    damage_die_sides integer CHECK (damage_die_sides>1),
    open_weapon_selection boolean NOT NULL,
    PRIMARY KEY (chassis_rule_id,weapon_order),
    CHECK (
        (open_weapon_selection AND damage_dice_count IS NULL
         AND damage_die_sides IS NULL)
        OR
        (NOT open_weapon_selection AND damage_dice_count IS NOT NULL
         AND damage_die_sides IS NOT NULL))
);

CREATE TABLE rule_personal_robot_drone_mobility (
    chassis_rule_id bigint PRIMARY KEY REFERENCES
        inv_personal_robot_drone_chassis(item_rule_id),
    operating_range_kilometres integer NOT NULL CHECK (
        operating_range_kilometres=500),
    speed_kph integer NOT NULL CHECK (speed_kph=300)
);

CREATE TABLE rule_personal_combat_drone_operation (
    chassis_rule_id bigint PRIMARY KEY REFERENCES
        inv_personal_robot_drone_chassis(item_rule_id),
    piloting_skill_rule_id bigint NOT NULL REFERENCES rule_skill(rule_id),
    attacks_use_selected_weapon_skill boolean NOT NULL CHECK (
        attacks_use_selected_weapon_skill),
    intellect_plus_combat_expert_makes_autonomous boolean NOT NULL CHECK (
        intellect_plus_combat_expert_makes_autonomous),
    autonomous_form_illegal_on_many_worlds boolean NOT NULL CHECK (
        autonomous_form_illegal_on_many_worlds)
);

COMMENT ON TABLE inv_personal_robot_drone_program IS
    'CE-EQUIP-017 preserves unresolved and open program specializations.';
