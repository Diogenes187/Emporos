import os
import unittest
import psycopg

DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class PersonalRobotDroneChassisTests(unittest.TestCase):
    def test_all_seven_chassis_preserve_core_profiles(self):
        with psycopg.connect(DSN) as connection:
            rows = connection.execute(
                """SELECT chassis_code,kind_code,item.minimum_tech_level,
                          item.cost_credits,strength,dexterity,hull,structure,
                          intelligence,education,social_standing,armor
                   FROM inv_personal_robot_drone_chassis chassis
                   JOIN inv_item_definition item
                     ON item.rule_id=chassis.item_rule_id
                   ORDER BY chassis_code""").fetchall()
        self.assertEqual(len(rows), 7)
        self.assertIn(
            ("cargo-robot", "robot", 11, 75000, 30, 9, 2, 2,
             3, 5, 0, 8), rows)
        self.assertIn(
            ("probe-drone", "drone", 11, 15000, 3, 7, 3, 3,
             None, None, None, 5), rows)
        self.assertIn(
            ("servitor", "robot", 13, 120000, 7, 9, 2, 2,
             9, 12, 7, None), rows)

    def test_probe_drone_reuses_ship_carried_item_identity(self):
        with psycopg.connect(DSN) as connection:
            row = connection.execute(
                """SELECT chassis.item_rule_id,count(carried.*)
                   FROM inv_personal_robot_drone_chassis chassis
                   JOIN ship_class_carried_item carried
                     ON carried.item_rule_id=chassis.item_rule_id
                   WHERE chassis.chassis_code='probe-drone'
                   GROUP BY chassis.item_rule_id""").fetchone()
        self.assertEqual(row[1], 2)

    def test_variable_price_and_cargo_variant_boundaries_are_typed(self):
        with psycopg.connect(DSN) as connection:
            rows = connection.execute(
                """SELECT chassis_code,price_excludes_selected_weapon,
                          cargo_drone_variant_minimum_tech_level,
                          cargo_drone_pre_intellect_utility_extremely_limited
                   FROM inv_personal_robot_drone_chassis
                   WHERE price_excludes_selected_weapon
                      OR cargo_drone_variant_minimum_tech_level IS NOT NULL
                   ORDER BY chassis_code""").fetchall()
        self.assertEqual(rows, [
            ("cargo-robot", False, 9, True),
            ("combat-drone", True, None, False),
        ])


if __name__ == "__main__":
    unittest.main()
