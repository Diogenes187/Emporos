from __future__ import annotations

import os
import unittest
from decimal import Decimal

import psycopg
from psycopg.errors import CheckViolation


@unittest.skipUnless(
    os.environ.get("BASE_CEPHEUS_DATABASE_URL"),
    "BASE_CEPHEUS_DATABASE_URL is not configured",
)
class VehicleConstructionReceiptTests(unittest.TestCase):
    def test_standard_profiles_have_finalized_published_receipts(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            counts = connection.execute(
                """SELECT
                     (SELECT count(*)
                        FROM vehicle_class_construction_receipt
                       WHERE finalized),
                     (SELECT count(*)
                        FROM vehicle_class_construction_line),
                     (SELECT count(*)
                        FROM vehicle_class_construction_variance)"""
            ).fetchone()
            self.assertEqual(counts, (36, 537, 10))

    def test_ship_scale_watercraft_receipts_preserve_source_results(
        self,
    ) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            totals = connection.execute(
                """SELECT class.class_code,total.receipt_status,
                          total.capacity_spaces,
                          total.allocated_spaces,
                          total.remainder_spaces,
                          total.space_variance,
                          total.stated_subtotal_variance,
                          total.published_cost_variance,
                          total.reconciliation_status
                   FROM vehicle_class_construction_total total
                   JOIN vehicle_class class
                     USING (vehicle_class_rule_id)
                   WHERE class.class_code IN (
                       'destroyer-watercraft','motor-boat',
                       'steamship','submersible'
                   )
                   ORDER BY class.class_code"""
            ).fetchall()
            self.assertEqual(
                totals,
                [
                    (
                        "destroyer-watercraft",
                        "source_gap",
                        Decimal("9600"),
                        Decimal("8548.21"),
                        Decimal("847.38"),
                        Decimal("204.41"),
                        None,
                        None,
                        "source_gap",
                    ),
                    (
                        "motor-boat",
                        "published",
                        Decimal("720"),
                        Decimal("447.15"),
                        Decimal("272.85"),
                        Decimal("0.00"),
                        Decimal("0.000"),
                        Decimal("10"),
                        "published_cost_conflict",
                    ),
                    (
                        "steamship",
                        "adjudicated",
                        Decimal("2400"),
                        Decimal("1883.4"),
                        Decimal("516.6"),
                        Decimal("0.0"),
                        Decimal("0"),
                        Decimal("0"),
                        "published_reconciled",
                    ),
                    (
                        "submersible",
                        "adjudicated",
                        Decimal("1200"),
                        Decimal("659.73"),
                        Decimal("540.27"),
                        Decimal("0.00"),
                        Decimal("0"),
                        Decimal("0"),
                        "published_reconciled",
                    ),
                ],
            )

            destroyer_lines = connection.execute(
                """SELECT count(*),
                          count(*) FILTER (
                              WHERE line_status='reconstructed'
                          ),
                          count(*) FILTER (
                              WHERE line_kind IN (
                                  'ammunition','missile','ordnance'
                              )
                          )
                   FROM vehicle_class_construction_line line
                   JOIN vehicle_class class
                     USING (vehicle_class_rule_id)
                   WHERE class.class_code='destroyer-watercraft'"""
            ).fetchone()
            self.assertEqual(destroyer_lines, (58, 30, 10))

    def test_receipts_distinguish_capacity_allocation_and_cargo(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            reconciled = connection.execute(
                """SELECT class.class_code,total.capacity_spaces,
                          total.allocated_spaces,
                          total.remainder_spaces,
                          total.space_variance,
                          total.reconciliation_status
                   FROM vehicle_class_construction_total total
                   JOIN vehicle_class class
                     USING (vehicle_class_rule_id)
                   WHERE class.class_code IN (
                       'ground-car','stagecoach','van'
                   )
                   ORDER BY class.class_code"""
            ).fetchall()
            self.assertEqual(
                reconciled,
                [
                    (
                        "ground-car",
                        Decimal("12"),
                        Decimal("11.962"),
                        Decimal("0.038"),
                        Decimal("0.000"),
                        "published_cost_conflict",
                    ),
                    (
                        "stagecoach",
                        Decimal("24"),
                        Decimal("13.5"),
                        Decimal("10.5"),
                        Decimal("0.0"),
                        "published_reconciled",
                    ),
                    (
                        "van",
                        Decimal("24"),
                        Decimal("14.172"),
                        Decimal("9.828"),
                        Decimal("0.000"),
                        "published_cost_conflict",
                    ),
                ],
            )

    def test_material_variances_are_linked_to_source_issues(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            variances = connection.execute(
                """SELECT class_code,variance_dimension,
                          variance_amount,issue_code
                   FROM vehicle_class_construction_material_variance
                   ORDER BY class_code,variance_dimension"""
            ).fetchall()
            self.assertEqual(
                variances,
                [
                    (
                        "afv-tracked",
                        "stated_subtotal",
                        Decimal("5000"),
                        "vehicle.class.tracked-autopilot-price",
                    ),
                    (
                        "air-raft",
                        "published_cost",
                        Decimal("190"),
                        "vehicle.class.air-raft-construction-arithmetic",
                    ),
                    (
                        "air-raft",
                        "space",
                        Decimal("5.11"),
                        "vehicle.class.air-raft-construction-arithmetic",
                    ),
                    (
                        "atv-tracked",
                        "stated_subtotal",
                        Decimal("5000"),
                        "vehicle.class.tracked-autopilot-price",
                    ),
                    (
                        "destroyer-watercraft",
                        "space",
                        Decimal("204.41"),
                        "vehicle.class.destroyer-design-table-copy",
                    ),
                    (
                        "g-carrier",
                        "stated_subtotal",
                        Decimal("1968600"),
                        "vehicle.class.g-carrier-design-subtotal",
                    ),
                    (
                        "grav-tank",
                        "stated_subtotal",
                        Decimal("-100000"),
                        "vehicle.class.grav-tank-subtotal-omits-weapon",
                    ),
                    (
                        "helicopter",
                        "published_cost",
                        Decimal("-40"),
                        "vehicle.class.helicopter-final-price",
                    ),
                    (
                        "speeder",
                        "stated_subtotal",
                        Decimal("2000"),
                        "vehicle.class.speeder-unitemized-subtotal",
                    ),
                    (
                        "steamship",
                        "space",
                        Decimal("-108"),
                        "vehicle.class.steamship-cargo-space",
                    ),
                ],
            )

    def test_fractional_published_fuel_costs_are_preserved(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            fuel = connection.execute(
                """SELECT class.class_code,tank.capacity_kilolitres,
                          tank.published_cost_credits
                   FROM vehicle_class_fuel_tank tank
                   JOIN vehicle_class class
                     USING (vehicle_class_rule_id)
                   WHERE class.class_code IN (
                       'grav-bike','ground-car','motor-boat'
                   )
                   ORDER BY class.class_code"""
            ).fetchall()
            self.assertEqual(
                fuel,
                [
                    (
                        "grav-bike",
                        Decimal("0.32"),
                        Decimal("12.9024"),
                    ),
                    (
                        "ground-car",
                        Decimal("0.012"),
                        Decimal("9.5865"),
                    ),
                    (
                        "motor-boat",
                        Decimal("1.29"),
                        Decimal("1067.143"),
                    ),
                ],
            )

    def test_finalized_receipts_and_lines_are_immutable(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            with connection.transaction(force_rollback=True):
                with self.assertRaises(CheckViolation):
                    connection.execute(
                        """UPDATE vehicle_class_construction_line
                           SET published_cost_credits=
                               published_cost_credits+1
                           WHERE construction_line_id=(
                               SELECT min(construction_line_id)
                               FROM vehicle_class_construction_line
                           )"""
                    )

            with connection.transaction(force_rollback=True):
                with self.assertRaises(CheckViolation):
                    connection.execute(
                        """UPDATE vehicle_class_construction_receipt
                           SET stated_subtotal_credits=
                               stated_subtotal_credits+1
                           WHERE construction_receipt_id=(
                               SELECT min(construction_receipt_id)
                               FROM vehicle_class_construction_receipt
                           )"""
                    )


if __name__ == "__main__":
    unittest.main()
