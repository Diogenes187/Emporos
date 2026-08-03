from __future__ import annotations

import os
import unittest

import psycopg
from psycopg.errors import CheckViolation


@unittest.skipUnless(
    os.environ.get("BASE_CEPHEUS_DATABASE_URL"),
    "BASE_CEPHEUS_DATABASE_URL is not configured",
)
class LowPrioritySourceAdjudicationTests(unittest.TestCase):
    def test_drug_runtime_uses_completed_rounds(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            rows = connection.execute(
                """SELECT drug.drug_code,effect.activation_seconds,
                          effect.activation_rounds,
                          effect.activation_runtime_basis,
                          effect.effective_activation_rounds
                     FROM rule_personal_combat_drug_effect effect
                     JOIN inv_personal_drug_definition drug
                       ON drug.item_rule_id=effect.drug_rule_id
                    ORDER BY drug.drug_code"""
            ).fetchall()
        self.assertEqual(rows, [
            ("combat", 20, 4, "completed-rounds", 4),
            ("metabolic-accelerator", 45, 8, "completed-rounds", 8),
        ])

    def test_vehicle_corrections_are_effective_and_auditable(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            grav_tank = connection.execute(
                """SELECT autopilot.skill_level,
                          autopilot.published_cost_minor,
                          autopilot.calculation_status
                     FROM vehicle_class_autopilot autopilot
                     JOIN vehicle_class class USING(vehicle_class_rule_id)
                    WHERE class.class_code='grav-tank'"""
            ).fetchone()
            helicopter = connection.execute(
                """SELECT class.construction_cost_minor,
                          receipt.receipt_version,
                          total.stated_discounted_cost_credits,
                          total.published_cost_variance,
                          receipt.receipt_status
                     FROM vehicle_class class
                     JOIN vehicle_class_construction_receipt receipt
                       USING(vehicle_class_rule_id)
                     JOIN vehicle_class_construction_total total
                       USING(construction_receipt_id)
                    WHERE class.class_code='helicopter'
                    ORDER BY receipt.receipt_version DESC LIMIT 1"""
            ).fetchone()
        self.assertEqual(grav_tank, (0, 2000, "adjudicated"))
        self.assertEqual(helicopter, (154850, 2, 154850, 0, "adjudicated"))

    def test_ship_effective_costs_adopt_finalized_receipts(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            rows = connection.execute(
                """SELECT class.class_code,effective.effective_cost_minor,
                          total.calculated_cost_minor,receipt.finalized,
                          effective.decision_register_entry
                     FROM ship_class_effective_cost_adjudication effective
                     JOIN ship_class class USING(ship_class_rule_id)
                     JOIN ship_class_construction_receipt receipt
                       USING(construction_receipt_id,ship_class_rule_id)
                     JOIN ship_class_construction_receipt_total total
                       USING(construction_receipt_id,ship_class_rule_id)
                    ORDER BY class.class_code"""
            ).fetchall()
        self.assertEqual(len(rows), 18)
        self.assertTrue(all(row[1] == row[2] for row in rows))
        self.assertTrue(all(row[3] for row in rows))
        self.assertEqual({row[4] for row in rows}, {"CE-SHIP-008"})
        self.assertIn(("cutter", 18364500, 18364500, True, "CE-SHIP-008"), rows)
        self.assertIn(("dreadnought", 2890955000, 2890955000, True, "CE-SHIP-008"), rows)

    def test_adjudicated_values_reject_silent_changes(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            statements = (
                "UPDATE rule_personal_combat_drug_effect "
                "SET effective_activation_rounds=activation_rounds+1",
                "UPDATE vehicle_class_autopilot SET skill_level=1 "
                "WHERE vehicle_class_rule_id=(SELECT vehicle_class_rule_id "
                "FROM vehicle_class WHERE class_code='grav-tank')",
                "UPDATE vehicle_class SET construction_cost_minor=154810 "
                "WHERE class_code='helicopter'",
                "UPDATE ship_class_effective_cost_adjudication "
                "SET effective_cost_minor=effective_cost_minor+1",
            )
            for statement in statements:
                with self.assertRaises(CheckViolation):
                    with connection.transaction():
                        connection.execute(statement)
                connection.rollback()

    def test_all_review_questions_are_closed(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            open_count = connection.execute(
                "SELECT count(*) FROM src_open_issue_report"
            ).fetchone()[0]
            decisions = connection.execute(
                """SELECT DISTINCT decision_register_entry
                     FROM rule_interpretation
                    WHERE decision_register_entry IN (
                        'CE-DRUG-001','CE-VDS-029','CE-VDS-030','CE-SHIP-008')
                    ORDER BY decision_register_entry"""
            ).fetchall()
        self.assertEqual(open_count, 0)
        self.assertEqual(decisions, [
            ("CE-DRUG-001",), ("CE-SHIP-008",),
            ("CE-VDS-029",), ("CE-VDS-030",),
        ])


if __name__ == "__main__":
    unittest.main()
