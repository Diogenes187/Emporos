import os
import unittest
import psycopg

DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class PersonalRobotDroneLoadoutTests(unittest.TestCase):
    def test_relational_loadout_counts(self):
        with psycopg.connect(DSN) as connection:
            counts = connection.execute(
                """SELECT
                    (SELECT count(*) FROM inv_personal_robot_drone_system),
                    (SELECT count(*) FROM inv_personal_robot_drone_program),
                    (SELECT count(*) FROM inv_personal_robot_drone_weapon)"""
            ).fetchone()
        self.assertEqual(counts, (17, 13, 5))

    def test_program_alternatives_and_unresolved_liaison_are_preserved(self):
        with psycopg.connect(DSN) as connection:
            rows = connection.execute(
                """SELECT chassis.chassis_code,program.printed_specialization,
                          skill.rule_code,program.rating,
                          program.program_status,
                          program.alternative_to_program_order
                   FROM inv_personal_robot_drone_program program
                   JOIN inv_personal_robot_drone_chassis chassis
                     ON chassis.item_rule_id=program.chassis_rule_id
                   LEFT JOIN rule_rule skill
                     ON skill.rule_id=program.expert_skill_rule_id
                   WHERE program.program_status<>'installed'
                   ORDER BY chassis.chassis_code,program.program_order"""
            ).fetchall()
        self.assertEqual(rows, [
            ("repair-robot", "Engineering", "skill.engineering",
             2, "alternative", 2),
            ("servitor", "Liaison", None, 2, "available-on-demand", None),
            ("servitor", None, None, 1, "available-on-demand", None),
            ("servitor", "Carousing", "skill.carousing",
             None, "reprogram-option", None),
            ("servitor", "Gambling", "skill.gambling",
             None, "reprogram-option", None),
        ])

    def test_weapons_and_probe_mobility_are_exact(self):
        with psycopg.connect(DSN) as connection:
            weapons = connection.execute(
                """SELECT chassis.chassis_code,weapon.weapon_name,
                          skill.rule_code,weapon.damage_dice_count,
                          weapon.open_weapon_selection
                   FROM inv_personal_robot_drone_weapon weapon
                   JOIN inv_personal_robot_drone_chassis chassis
                     ON chassis.item_rule_id=weapon.chassis_rule_id
                   LEFT JOIN rule_rule skill
                     ON skill.rule_id=weapon.skill_rule_id
                   ORDER BY chassis.chassis_code"""
            ).fetchall()
            mobility = connection.execute(
                """SELECT operating_range_kilometres,speed_kph
                   FROM rule_personal_robot_drone_mobility"""
            ).fetchone()
        self.assertIn(
            ("autodoc", "Surgical Tools", "skill.slashing-weapons", 1, False),
            weapons)
        self.assertIn(("combat-drone", "Any gun", None, None, True), weapons)
        self.assertEqual(mobility, (500, 300))

    def test_combat_drone_operation_uses_canonical_comms(self):
        with psycopg.connect(DSN) as connection:
            row = connection.execute(
                """SELECT skill.rule_code,
                          operation.attacks_use_selected_weapon_skill,
                          operation.intellect_plus_combat_expert_makes_autonomous,
                          operation.autonomous_form_illegal_on_many_worlds
                   FROM rule_personal_combat_drone_operation operation
                   JOIN rule_rule skill
                     ON skill.rule_id=operation.piloting_skill_rule_id"""
            ).fetchone()
        self.assertEqual(row, ("skill.comms", True, True, True))


if __name__ == "__main__":
    unittest.main()
