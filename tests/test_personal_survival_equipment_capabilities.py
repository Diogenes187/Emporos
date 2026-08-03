import os
import unittest

import psycopg

DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class PersonalSurvivalEquipmentCapabilityTests(unittest.TestCase):
    def test_cold_air_and_duration_mechanics_are_exact(self):
        with psycopg.connect(DSN) as connection:
            cold = connection.execute(
                """SELECT capability.cold_threshold_celsius,
                          capability.endurance_check_modifier,
                          capability.mass_reduction_grams_per_tech_interval,
                          capability.tech_level_interval
                   FROM rule_personal_survival_equipment_capability capability
                   JOIN inv_personal_survival_equipment_definition item
                     ON item.item_rule_id=
                        capability.survival_equipment_rule_id
                   WHERE item.survival_equipment_code=
                         'cold-weather-clothing'"""
            ).fetchone()
            durations = connection.execute(
                """SELECT item.survival_equipment_code,
                          capability.operating_duration_seconds,
                          capability.refill_cost_credits,
                          capability.units_per_full_set
                   FROM rule_personal_survival_equipment_capability capability
                   JOIN inv_personal_survival_equipment_definition item
                     ON item.item_rule_id=
                        capability.survival_equipment_rule_id
                   WHERE capability.operating_duration_seconds IS NOT NULL
                   ORDER BY item.survival_equipment_code"""
            ).fetchall()
        self.assertEqual(cold, (-20, 2, 1000, 5))
        self.assertEqual(durations, [
            ("oxygen-tanks", 21600, 20, 2),
            ("portable-generator", 2592000, None, None),
            ("underwater-air-tanks", 21600, 20, 2),
        ])

    def test_atmospheres_use_canonical_world_codes(self):
        with psycopg.connect(DSN) as connection:
            rows = connection.execute(
                """SELECT item.survival_equipment_code,
                          array_agg(link.atmosphere_code
                                    ORDER BY link.atmosphere_code)
                   FROM rule_personal_survival_equipment_atmosphere link
                   JOIN inv_personal_survival_equipment_definition item
                     ON item.item_rule_id=link.survival_equipment_rule_id
                   GROUP BY item.survival_equipment_code
                   ORDER BY item.survival_equipment_code"""
            ).fetchall()
        self.assertIn(("artificial-gill", [4, 5, 6, 7, 8, 9]), rows)
        self.assertIn(("combination-mask", [2, 3, 4, 7, 9]), rows)
        self.assertIn(("filter-mask", [4, 7, 9]), rows)
        self.assertIn(("respirator", [3]), rows)

    def test_skill_links_and_rescue_bubble_are_typed(self):
        with psycopg.connect(DSN) as connection:
            skills = connection.execute(
                """SELECT item.survival_equipment_code,rule.rule_code,
                          link.task_modifier,
                          link.check_required_for_accurate_use
                   FROM rule_personal_survival_equipment_skill link
                   JOIN inv_personal_survival_equipment_definition item
                     ON item.item_rule_id=link.survival_equipment_rule_id
                   JOIN rule_rule rule ON rule.rule_id=link.skill_rule_id
                   ORDER BY item.survival_equipment_code"""
            ).fetchall()
            bubble = connection.execute(
                """SELECT capability.life_support_person_hours,
                          capability.diameter_metres,
                          capability.pressurized,
                          capability.self_repairing_emergency_airlock,
                          capability.movement_recharges_batteries,
                          capability.distress_beacon
                   FROM rule_personal_survival_equipment_capability capability
                   JOIN inv_personal_survival_equipment_definition item
                     ON item.item_rule_id=
                        capability.survival_equipment_rule_id
                   WHERE item.survival_equipment_code='rescue-bubble'"""
            ).fetchone()
        self.assertEqual(skills, [
            ("swimming-equipment", "skill.athletics", 1, False),
            ("thruster-pack", "skill.zero-g", None, True),
        ])
        self.assertEqual(bubble, (2, 2, True, True, True, True))


if __name__ == "__main__":
    unittest.main()
