import os
import unittest

import psycopg

DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class PersonalCombatDrugTests(unittest.TestCase):
    def connect(self):
        return psycopg.connect(DSN)

    def test_dual_timings_are_preserved_with_round_runtime_authority(self):
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT drug.drug_code,effect.activation_seconds,
                          effect.activation_rounds,
                          effect.printed_timings_not_equivalent_at_six_seconds,
                          effect.activation_runtime_basis,
                          effect.effective_activation_rounds,
                          effect.approximate_duration_seconds,
                          effect.duration_is_approximate
                   FROM rule_personal_combat_drug_effect effect
                   JOIN inv_personal_drug_definition drug
                     ON drug.item_rule_id=effect.drug_rule_id
                   ORDER BY drug.drug_code"""
            ).fetchall()
        self.assertEqual(rows, [
            ("combat", 20, 4, True, "completed-rounds", 4, 600, True),
            ("metabolic-accelerator", 45, 8, True,
             "completed-rounds", 8, 600, True),
        ])

    def test_combat_and_slow_drug_effects_are_exact(self):
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT drug.drug_code,effect.initiative_modifier,
                          effect.free_dodges_per_round,
                          effect.free_dodges_change_initiative,
                          effect.damage_reduction,effect.aftermath_code,
                          effect.aftermath_damage_dice_count,
                          effect.aftermath_damage_die_sides
                   FROM rule_personal_combat_drug_effect effect
                   JOIN inv_personal_drug_definition drug
                     ON drug.item_rule_id=effect.drug_rule_id
                   ORDER BY drug.drug_code"""
            ).fetchall()
        self.assertEqual(rows, [
            ("combat", 4, 1, False, 2, "fatigued", 0, None),
            ("metabolic-accelerator", 8, 2, False, 0,
             "damage-and-exhausted", 2, 6),
        ])

    def test_antiradiation_and_stim_rules_are_typed(self):
        with self.connect() as connection:
            anti = connection.execute(
                """SELECT post_exposure_window_seconds,absorbed_rads_per_dose,
                          safe_doses_per_day,
                          excess_dose_endurance_damage_dice,
                          excess_dose_endurance_damage_die_sides,
                          excess_damage_is_per_dose,
                          endurance_damage_is_permanent
                   FROM rule_personal_antiradiation_drug"""
            ).fetchone()
            stim = connection.execute(
                """SELECT removes_fatigue,
                          damage_equals_use_sequence_since_sleep,
                          sleep_resets_use_sequence
                   FROM rule_personal_stim_drug"""
            ).fetchone()
        self.assertEqual(anti, (600, 100, 1, 1, 6, True, True))
        self.assertEqual(stim, (True, True, True))

    def test_both_timing_conflicts_are_registered_with_paired_evidence(self):
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT issue.subject_code,issue.issue_status,
                          issue.engine_disposition,count(locator.*)
                   FROM src_issue issue
                   JOIN src_issue_locator locator USING (source_issue_id)
                   WHERE issue.domain_code='equipment.drug'
                   GROUP BY issue.source_issue_id,issue.subject_code,
                            issue.issue_status,issue.engine_disposition
                   ORDER BY issue.subject_code"""
            ).fetchall()
        self.assertEqual(rows, [
            ("combat", "resolved", "preserve_rule", 2),
            ("metabolic-accelerator", "resolved", "preserve_rule", 2),
        ])


if __name__ == "__main__":
    unittest.main()
