import os
import unittest
import psycopg

DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class PersonalDeviceCapabilityTests(unittest.TestCase):
    def test_capability_ranges_and_modifier_are_typed(self):
        with psycopg.connect(DSN) as connection:
            rows = connection.execute(
                """SELECT device.device_code,capability.capability_code,
                          capability.range_metres,
                          capability.range_is_approximate,
                          capability.task_modifier
                   FROM rule_personal_device_capability capability
                   JOIN inv_personal_device_definition device
                     ON device.item_rule_id=capability.device_rule_id
                   WHERE capability.range_metres IS NOT NULL
                      OR capability.task_modifier IS NOT NULL
                   ORDER BY device.device_code,capability.capability_code"""
            ).fetchall()
        self.assertEqual(rows, [
            ("electromagnetic-probe", "equipment-diagnostics",
             None, None, 1),
            ("holographic-projector", "three-dimensional-projection",
             3, True, None),
            ("metal-detector", "metal-detection", 3, False, None),
            ("neural-activity-sensor", "neural-activity-detection",
             500, False, None),
            ("neural-activity-sensor", "rough-intelligence-estimate",
             500, False, None),
            ("radiation-counter", "radioactivity-detection-and-intensity",
             30, False, None),
        ])

    def test_interpretation_skills_use_canonical_rules(self):
        with psycopg.connect(DSN) as connection:
            rows = connection.execute(
                """SELECT device.device_code,skill.rule_code
                   FROM rule_personal_device_capability_skill link
                   JOIN inv_personal_device_definition device
                     ON device.item_rule_id=link.device_rule_id
                   JOIN rule_rule skill ON skill.rule_id=link.skill_rule_id
                   ORDER BY device.device_code,skill.rule_code"""
            ).fetchall()
        self.assertEqual(len(rows), 6)
        self.assertIn(("bioscanner", "skill.life-sciences"), rows)
        self.assertIn(
            ("neural-activity-sensor", "skill.social-sciences"), rows)

    def test_hologram_upgrades_preserve_cost_and_realism(self):
        with psycopg.connect(DSN) as connection:
            rows = connection.execute(
                """SELECT upgrade_tech_level,cost_multiplier,realism_code,
                          intelligence_check_required
                   FROM rule_personal_holographic_projector_upgrade
                   ORDER BY upgrade_tech_level""").fetchall()
        self.assertEqual(rows, [
            (12, 2, "check-to-disbelieve", True),
            (13, 10, "true-to-life", False),
        ])


if __name__ == "__main__":
    unittest.main()
