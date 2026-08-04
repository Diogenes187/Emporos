CREATE TABLE rule_personal_laser_weapon(
 weapon_rule_id bigint PRIMARY KEY REFERENCES inv_weapon_definition(item_rule_id)
);
INSERT INTO rule_personal_laser_weapon
SELECT rule_id FROM rule_rule
WHERE rule_code IN('equipment.weapon.laser-carbine','equipment.weapon.laser-pistol','equipment.weapon.laser-rifle');

CREATE TABLE cmd_attack_armor_layer_receipt(
 command_id bigint NOT NULL REFERENCES cmd_attack_receipt(command_id),
 item_instance_id bigint NOT NULL REFERENCES inv_item_instance(item_instance_id),
 layer_order integer NOT NULL CHECK(layer_order BETWEEN 1 AND 2),
 armor_rule_id bigint NOT NULL REFERENCES inv_armor_definition(item_rule_id),
 applicable_armor_rating integer NOT NULL CHECK(applicable_armor_rating>=0),
 damage_before integer NOT NULL CHECK(damage_before>=0),
 damage_after integer NOT NULL CHECK(damage_after>=0),
 laser_attack boolean NOT NULL,
 PRIMARY KEY(command_id,layer_order),
 UNIQUE(command_id,item_instance_id),
 CHECK(damage_after=greatest(damage_before-applicable_armor_rating,0))
);

COMMENT ON TABLE cmd_attack_armor_layer_receipt IS
 'Immutable outside-in personal armor resolution for an attack.';
