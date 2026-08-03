import os
import unittest

import psycopg

DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class PersonalSupportDrugTests(unittest.TestCase):
    def connect(self):
        return psycopg.connect(DSN)

    def test_fast_and_medicinal_drug_mechanics_are_relational(self):
        with self.connect() as connection:
            fast = connection.execute(
                """SELECT metabolic_rate_divisor,subjective_days,
                          corresponding_actual_months,prolongs_life_support,
                          cryoberth_substitute
                   FROM rule_personal_fast_drug"""
            ).fetchone()
            medicinal = connection.execute(
                """SELECT rule.rule_code,difficulty_rule.name,
                          difficulty.modifier,
                          drug.successful_use_counteracts_most_poison_disease,
                          drug.resistance_dm_is_positive,
                          drug.resistance_dm_is_unquantified,
                          drug.wrong_drug_poison_damage_dice,
                          drug.wrong_drug_poison_damage_die_sides
                   FROM rule_personal_medicinal_drug drug
                   JOIN rule_rule rule
                     ON rule.rule_id=drug.required_skill_rule_id
                   JOIN rule_difficulty difficulty
                     ON difficulty.rule_id=drug.wrong_drug_difficulty_rule_id
                   JOIN rule_rule difficulty_rule
                     ON difficulty_rule.rule_id=difficulty.rule_id"""
            ).fetchone()
        self.assertEqual(fast, (60, 1, 2, True, True))
        self.assertEqual(
            medicinal,
            ("skill.medicine", "Difficult", -2, True, True, True, 1, 6),
        )

    def test_slow_panacea_and_anagathic_mechanics_are_exact(self):
        with self.connect() as connection:
            slow = connection.execute(
                """SELECT requires_medical_facility,requires_life_support,
                          requires_cryo_technology,
                          approximate_metabolic_multiplier,
                          metabolic_multiplier_is_approximate,
                          healing_months,elapsed_days
                   FROM rule_personal_medicinal_slow_drug"""
            ).fetchone()
            panacea = connection.execute(
                """SELECT applicable_to_any_wound_or_illness,
                          guaranteed_not_to_worsen,
                          granted_medic_skill_level,treatment_scope
                   FROM rule_personal_panacea"""
            ).fetchone()
            anagathic = connection.execute(
                """SELECT doses_per_interval,interval_unit,
                          maintains_slowed_aging,
                          missed_dose_immediate_aging_roll
                   FROM rule_personal_anagathic_dosing"""
            ).fetchone()
        self.assertEqual(slow, (True, True, True, 30, True, 1, 1))
        self.assertEqual(panacea, (True, True, 0, "infection-or-disease"))
        self.assertEqual(anagathic, (1, "calendar-month", True, True))

    def test_database_rejects_recasting_approximate_rate_as_exact(self):
        with self.connect() as connection:
            with self.assertRaises(psycopg.errors.CheckViolation):
                connection.execute(
                    """UPDATE rule_personal_medicinal_slow_drug
                       SET metabolic_multiplier_is_approximate=false"""
                )


if __name__ == "__main__":
    unittest.main()
