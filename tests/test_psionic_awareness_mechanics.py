import os
import unittest

import psycopg
from psycopg.errors import CheckViolation, UniqueViolation


DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class PsionicAwarenessMechanicsTests(unittest.TestCase):
    def test_awareness_mechanics_are_exact_and_relational(self):
        with psycopg.connect(DSN) as connection:
            suspended = connection.execute(
                """SELECT duration_days,food_required,water_required,
                          air_requirement,
                          early_waking_requires_external_stimulus,
                          cold_sleep_death_risk,self_only
                   FROM rule_psi_suspended_animation"""
            ).fetchone()
            enhancements = connection.execute(
                """SELECT rule.rule_code,cost.psionic_cost_per_point,
                          cost.points_capped_by_awareness_level,
                          cost.racial_maximum_applies,
                          cost.peak_duration_minutes,cost.decline_points,
                          cost.decline_interval_minutes,
                          cost.returns_to_wounded_value,
                          cost.permits_healing,cost.self_only
                   FROM rule_psi_characteristic_enhancement cost
                   JOIN rule_rule rule
                     ON rule.rule_id=cost.characteristic_rule_id
                   ORDER BY rule.rule_code"""
            ).fetchall()
            regeneration = connection.execute(
                """SELECT regeneration.psionic_cost_per_point,
                          regeneration.maximum_per_use,
                          regeneration.reusable_after_all_spent_psi_recovered,
                          regeneration.permits_new_limbs_or_organs,
                          regeneration.permits_old_wound_healing,
                          regeneration.permits_aging_reversal,
                          regeneration.self_only,
                          array_agg(rule.rule_code ORDER BY rule.rule_code)
                   FROM rule_psi_regeneration regeneration
                   JOIN rule_psi_regeneration_characteristic permitted
                     USING (power_rule_id)
                   JOIN rule_rule rule
                     ON rule.rule_id=permitted.characteristic_rule_id
                   GROUP BY regeneration.power_rule_id"""
            ).fetchone()

        self.assertEqual(
            suspended,
            (7, False, False, "minimal", True, False, True),
        )
        self.assertEqual(
            enhancements,
            [
                ("characteristic.endurance", 1, True, True, 10, 1, 1,
                 True, False, True),
                ("characteristic.strength", 1, True, True, 10, 1, 1,
                 True, False, True),
            ],
        )
        self.assertEqual(
            regeneration,
            (1, None, True, True, True, False, True, [
                "characteristic.dexterity",
                "characteristic.endurance",
                "characteristic.strength",
            ]),
        )

    def test_database_rejects_noncanonical_awareness_mechanics(self):
        with psycopg.connect(DSN) as connection:
            power = connection.execute(
                """SELECT power_rule_id FROM psi_power
                   WHERE power_code='suspended-animation'"""
            ).fetchone()[0]
            with self.assertRaises(UniqueViolation):
                with connection.transaction():
                    connection.execute(
                        """INSERT INTO rule_psi_suspended_animation
                           VALUES (%s,7,false,false,'minimal',
                                   true,false,true)""",
                        (power,),
                    )
            with self.assertRaises(CheckViolation):
                with connection.transaction():
                    connection.execute(
                        """UPDATE rule_psi_suspended_animation
                           SET duration_days=8"""
                    )


if __name__ == "__main__":
    unittest.main()
