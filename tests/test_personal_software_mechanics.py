import os
import unittest

import psycopg

DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class PersonalSoftwareMechanicsTests(unittest.TestCase):
    def connect(self):
        return psycopg.connect(DSN)

    def test_security_uses_canonical_difficulties(self):
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT mapping.rating,rule.name,difficulty.modifier
                   FROM rule_personal_security_difficulty mapping
                   JOIN rule_difficulty difficulty
                     ON difficulty.rule_id=mapping.difficulty_rule_id
                   JOIN rule_rule rule ON rule.rule_id=difficulty.rule_id
                   ORDER BY mapping.rating"""
            ).fetchall()
        self.assertEqual(rows, [
            (0, "Average", 0),
            (1, "Difficult", -2),
            (2, "Very Difficult", -4),
            (3, "Formidable", -6),
        ])

    def test_expert_is_limited_to_intelligence_and_education(self):
        with self.connect() as connection:
            mechanic = connection.execute(
                """SELECT expert.granted_skill_level_offset,
                          expert.existing_higher_skill_dm,
                          interface.software_code
                   FROM rule_personal_expert_mechanic expert
                   JOIN rule_personal_software_family interface
                     ON interface.rule_id=expert.required_interface_rule_id"""
            ).fetchone()
            characteristics = connection.execute(
                """SELECT rule.rule_code
                   FROM rule_personal_expert_allowed_characteristic allowed
                   JOIN rule_rule rule
                     ON rule.rule_id=allowed.characteristic_rule_id
                   ORDER BY rule.rule_code"""
            ).fetchall()
        self.assertEqual(mechanic, (-1, 1, "intelligent-interface"))
        self.assertEqual(characteristics, [
            ("characteristic.education",),
            ("characteristic.intelligence",),
        ])

    def test_agent_and_intellect_relationships_are_typed(self):
        with self.connect() as connection:
            row = connection.execute(
                """SELECT skill.rule_code,agent.computer_skill_equals_rating,
                          agent.carries_out_assigned_tasks,
                          expert.software_code,intellect.software_code,
                          intellect_rule.simultaneous_skills_equal_rating
                   FROM rule_personal_agent_mechanic agent
                   JOIN rule_rule skill
                     ON skill.rule_id=agent.computer_skill_rule_id
                   JOIN rule_personal_software_family expert
                     ON expert.rule_id=agent.expert_component_rule_id
                   JOIN rule_personal_software_family intellect
                     ON intellect.rule_id=agent.intellect_component_rule_id
                   JOIN rule_personal_intellect_mechanic intellect_rule
                     ON intellect_rule.software_rule_id=intellect.rule_id"""
            ).fetchone()
        self.assertEqual(
            row, ("skill.computer", True, True, "expert", "intellect", True))

    def test_translator_intrusion_and_interface_are_exact(self):
        with self.connect() as connection:
            row = connection.execute(
                """SELECT translator.language_skills_only,
                          translator.minimum_realtime_rating,
                          translator.rating_zero_near_realtime,
                          intrusion.hacking_dm_equals_rating,
                          intrusion.often_illegal,
                          difficulty.modifier
                   FROM rule_personal_translator_mechanic translator
                   CROSS JOIN rule_personal_intrusion_mechanic intrusion
                   CROSS JOIN rule_personal_interface_mechanic interface
                   JOIN rule_difficulty difficulty ON difficulty.rule_id=
                     interface.missing_interface_difficulty_rule_id"""
            ).fetchone()
        self.assertEqual(row, (True, 1, True, True, True, -6))

    def test_intelligent_interface_capability_progression(self):
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT rating,autonomy_class,self_initiating,
                          self_learning,creative_thought
                   FROM rule_personal_intelligent_interface_capability
                   ORDER BY rating"""
            ).fetchall()
        self.assertEqual(rows, [
            (1, "low-autonomous", False, False, False),
            (2, "high-autonomous", True, True, False),
            (3, "true-ai", True, True, True),
        ])


if __name__ == "__main__":
    unittest.main()
