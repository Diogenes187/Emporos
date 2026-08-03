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
class StandardVehicleComponentSelectionTests(unittest.TestCase):
    def test_every_standard_vehicle_has_a_component_ledger(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            totals = connection.execute(
                """SELECT class.class_code,count(*),
                          sum(selection.allocated_spaces),
                          sum(selection.published_cost_minor)
                   FROM vehicle_class_component selection
                   JOIN vehicle_class class
                     USING (vehicle_class_rule_id)
                   WHERE class.class_code NOT IN (
                       'destroyer-watercraft','motor-boat',
                       'steamship','submersible'
                   )
                   GROUP BY class.class_code
                   ORDER BY class.class_code"""
            ).fetchall()
            self.assertEqual(
                totals,
                [
                    ("afv-tracked", 9, Decimal("56.10"), 49500),
                    ("air-raft", 6, Decimal("14.06"), 25500),
                    ("atv-tracked", 9, Decimal("50.10"), 39500),
                    ("biplane", 3, Decimal("5"), 2000),
                    ("g-carrier", 7, Decimal("37.10"), 64500),
                    ("grav-bike", 4, Decimal("3.10"), 7000),
                    ("grav-floater", 5, Decimal("7.06"), 18500),
                    ("grav-tank", 7, Decimal("31.11"), 45000),
                    ("ground-car", 3, Decimal("9"), 4000),
                    ("helicopter", 4, Decimal("13.05"), 8000),
                    ("hovercraft", 5, Decimal("29.05"), 14500),
                    ("speeder", 7, Decimal("15.11"), 37200),
                    ("stagecoach", 3, Decimal("12.5"), 5290),
                    (
                        "tunnel-boring-machine",
                        6,
                        Decimal("11.03"),
                        8500,
                    ),
                    ("twin-engine-jet", 4, Decimal("13.05"), 8000),
                    ("van", 2, Decimal("5"), 2000),
                ],
            )

    def test_published_component_overrides_are_explicit(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            overrides = connection.execute(
                """SELECT class.class_code,component.component_code,
                          selection.allocated_spaces,
                          selection.published_cost_minor,
                          selection.calculation_status
                   FROM vehicle_class_component selection
                   JOIN vehicle_class class
                     USING (vehicle_class_rule_id)
                   JOIN vehicle_component_definition component
                     USING (component_rule_id)
                   WHERE selection.calculation_status<>'matches'
                     AND class.class_code NOT IN (
                         'destroyer-watercraft','motor-boat',
                         'steamship','submersible'
                     )
                   ORDER BY class.class_code,
                            component.component_code"""
            ).fetchall()
            self.assertEqual(
                overrides,
                [
                    (
                        "afv-tracked",
                        "additional.galley-full",
                        Decimal("21"),
                        6000,
                        "formula",
                    ),
                    (
                        "afv-tracked",
                        "life-support.basic",
                        Decimal("3"),
                        0,
                        "adjudicated",
                    ),
                    (
                        "atv-tracked",
                        "additional.galley-full",
                        Decimal("21"),
                        6000,
                        "formula",
                    ),
                    (
                        "atv-tracked",
                        "life-support.basic",
                        Decimal("3"),
                        0,
                        "adjudicated",
                    ),
                    (
                        "g-carrier",
                        "life-support.basic",
                        Decimal("3"),
                        10500,
                        "adjudicated",
                    ),
                    (
                        "grav-tank",
                        "life-support.basic",
                        Decimal("3"),
                        10500,
                        "adjudicated",
                    ),
                    (
                        "speeder",
                        "life-support.basic",
                        Decimal("3"),
                        10500,
                        "adjudicated",
                    ),
                    (
                        "stagecoach",
                        "control.primitive",
                        Decimal("0.5"),
                        -710,
                        "formula",
                    ),
                    (
                        "tunnel-boring-machine",
                        "computer.model-1",
                        Decimal("0.01"),
                        500,
                        "adjudicated",
                    ),
                    (
                        "tunnel-boring-machine",
                        "life-support.basic",
                        Decimal("3"),
                        0,
                        "adjudicated",
                    ),
                    (
                        "tunnel-boring-machine",
                        "sensor.standard",
                        Decimal("3"),
                        5000,
                        "adjudicated",
                    ),
                ],
            )

    def test_autopilot_formula_conflicts_are_typed(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            autopilots = connection.execute(
                """SELECT class.class_code,autopilot.skill_level,
                          autopilot.published_cost_minor,
                          autopilot.calculation_status
                   FROM vehicle_class_autopilot autopilot
                   JOIN vehicle_class class
                     USING (vehicle_class_rule_id)
                   WHERE class.class_code NOT IN (
                       'destroyer-watercraft','submersible'
                   )
                   ORDER BY class.class_code"""
            ).fetchall()
            self.assertEqual(
                autopilots,
                [
                    ("afv-tracked", 1, 7000, "adjudicated"),
                    ("air-raft", 0, 2000, "matches"),
                    ("atv-tracked", 1, 7000, "adjudicated"),
                    ("g-carrier", 3, 17000, "adjudicated"),
                    ("grav-bike", 1, 7000, "matches"),
                    ("grav-floater", 1, 7000, "matches"),
                    ("grav-tank", 0, 2000, "adjudicated"),
                    ("speeder", 0, 2000, "matches"),
                ],
            )

    def test_options_fuel_and_laser_communications_are_typed(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            counts = connection.execute(
                """SELECT
                     (SELECT count(*)
                        FROM vehicle_class_configuration_option),
                     (SELECT count(*)
                        FROM vehicle_class_drive_option),
                     (SELECT count(*)
                        FROM vehicle_class_computer_option),
                     (SELECT count(*)
                        FROM vehicle_class_fuel_tank),
                     (SELECT count(*)
                        FROM vehicle_class_alternative_communication)"""
            ).fetchone()
            self.assertEqual(counts, (11, 3, 3, 19, 2))

            laser_rows = connection.execute(
                """SELECT class.class_code,
                          alternative.communicator_type_code,
                          alternative.allocated_spaces,
                          alternative.published_cost_minor
                   FROM vehicle_class_alternative_communication
                        alternative
                   JOIN vehicle_class class
                     USING (vehicle_class_rule_id)
                   ORDER BY class.class_code"""
            ).fetchall()
            self.assertEqual(
                laser_rows,
                [
                    ("afv-tracked", "laser", Decimal("0.2"), 12000),
                    ("atv-tracked", "laser", Decimal("0.2"), 12000),
                ],
            )

    def test_selection_calculations_are_database_enforced(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            with connection.transaction(force_rollback=True):
                with self.assertRaises(CheckViolation):
                    connection.execute(
                        """UPDATE vehicle_class_component selection
                           SET published_cost_minor=-700
                           FROM vehicle_class class,
                                vehicle_component_definition component
                           WHERE class.vehicle_class_rule_id=
                                 selection.vehicle_class_rule_id
                             AND component.component_rule_id=
                                 selection.component_rule_id
                             AND class.class_code='stagecoach'
                             AND component.component_code=
                                 'control.primitive'"""
                    )

            with connection.transaction(force_rollback=True):
                with self.assertRaises(CheckViolation):
                    connection.execute(
                        """UPDATE vehicle_class_alternative_communication
                           SET published_cost_minor=4000"""
                    )

    def test_selection_findings_have_paired_evidence(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            evidence = connection.execute(
                """SELECT count(DISTINCT issue.source_issue_id),
                          count(DISTINCT comparison.source_issue_id)
                   FROM src_issue issue
                   JOIN src_issue_locator locator
                     USING (source_issue_id)
                   LEFT JOIN src_issue_comparison_check comparison
                     USING (source_issue_id)
                   WHERE issue.issue_code IN (
                       'vehicle.class.basic-life-support-profile-price',
                       'vehicle.class.g-carrier-autopilot',
                       'vehicle.class.tracked-autopilot-price',
                       'vehicle.class.grav-tank-autopilot-label',
                       'vehicle.class.tracked-insidious-protection-price',
                       'vehicle.class.tunnel-boring-electronics-omission'
                   )"""
            ).fetchone()
            self.assertEqual(evidence, (6, 6))


if __name__ == "__main__":
    unittest.main()
