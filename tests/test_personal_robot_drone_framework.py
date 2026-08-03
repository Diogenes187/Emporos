import os
import unittest
import psycopg

DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class PersonalRobotDroneFrameworkTests(unittest.TestCase):
    def test_shared_framework_uses_canonical_comms(self):
        with psycopg.connect(DSN) as connection:
            row = connection.execute(
                """SELECT skill.rule_code,
                          framework.operates_in_combat_like_character,
                          framework.takes_damage_like_vehicle,
                          framework.uses_hull_and_structure_instead_of_endurance,
                          framework.endurance_dm
                   FROM rule_personal_robot_drone_framework framework
                   JOIN rule_rule skill
                     ON skill.rule_id=framework.drone_control_skill_rule_id"""
            ).fetchone()
        self.assertEqual(row, ("skill.comms", True, True, True, 0))

    def test_robot_and_drone_distinctions_are_relational(self):
        with psycopg.connect(DSN) as connection:
            rows = connection.execute(
                """SELECT kind_code,intellect_program_required,
                          remotely_controlled,
                          has_intelligence_and_education,
                          social_standing_mode
                   FROM rule_personal_robot_drone_kind
                   ORDER BY kind_code""").fetchall()
        self.assertEqual(rows, [
            ("drone", False, True, False, "operator-score-for-social-use"),
            ("robot", True, False, True, "usually-zero-with-exceptions"),
        ])


if __name__ == "__main__":
    unittest.main()
