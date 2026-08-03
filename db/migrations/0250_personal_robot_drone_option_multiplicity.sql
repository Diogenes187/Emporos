ALTER TABLE cmd_personal_robot_drone_option_receipt
    DROP CONSTRAINT
        cmd_personal_robot_drone_opti_robot_item_instance_id_option_key;

COMMENT ON TABLE cmd_personal_robot_drone_option_receipt IS
    'CE-EQUIP-018 immutable installations; multiple integral options allowed.';
