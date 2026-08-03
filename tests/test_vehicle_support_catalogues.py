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
class VehicleSupportCatalogueTests(unittest.TestCase):
    def test_control_and_remote_operation_catalogues(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            controls = connection.execute(
                """SELECT component.component_code,
                          component.minimum_tech_level,
                          control.interface_rank,control.price_basis,
                          control.chassis_price_adjustment_percent,
                          control.agility_dm,control.initiative_dm,
                          control.high_speed_dm,
                          control.high_speed_threshold_kph
                   FROM rule_vehicle_control_system control
                   JOIN vehicle_component_definition component
                     ON component.component_rule_id=
                        control.component_rule_id
                   ORDER BY control.interface_rank"""
            ).fetchall()
            self.assertEqual(
                controls,
                [
                    (
                        "control.primitive", 1, 1,
                        "chassis_percent_adjustment", -20,
                        -1, 0, -2, 50,
                    ),
                    (
                        "control.basic", 4, 2, "included", None,
                        0, 0, None, None,
                    ),
                    (
                        "control.advanced", 8, 3, "fixed", None,
                        1, 0, None, None,
                    ),
                    (
                        "control.exo-skeleton", 10, 4, "fixed", None,
                        1, 1, None, None,
                    ),
                    (
                        "control.neural-linked", 12, 5, "fixed", None,
                        2, 2, None, None,
                    ),
                ],
            )

            remote = connection.execute(
                """SELECT controller.interface_code,
                          controller.control_dm,
                          controller.range_code,
                          brain.cpu_code,brain.computer_model,
                          brain.maximum_skill_level,
                          brain.minimum_control_rank
                   FROM rule_vehicle_drone_controller controller
                   FULL JOIN rule_vehicle_robot_brain brain
                     ON controller.component_rule_id=
                        brain.component_rule_id
                   ORDER BY controller.interface_code NULLS LAST,
                            brain.cpu_code"""
            ).fetchall()
            self.assertEqual(len(remote), 8)
            self.assertIn(
                ("neural-linked", 1, "regional", None, None, None, None),
                remote,
            )
            self.assertIn(
                (None, None, None, "synaptic", 3, 3, 3),
                remote,
            )

            autopilot = connection.execute(
                """SELECT category.vehicle_category,
                          category.minimum_tech_level,
                          formula.base_skill_level,
                          formula.tech_levels_per_skill_level,
                          formula.maximum_skill_level,
                          formula.base_price_minor,
                          formula.price_per_skill_level_minor
                   FROM rule_vehicle_autopilot_introduction category
                   JOIN rule_vehicle_autopilot_formula formula
                     USING (formula_code)
                   ORDER BY category.vehicle_category"""
            ).fetchall()
            self.assertEqual(
                autopilot,
                [
                    ("aircraft", 5, 0, 2, 3, 2000, 5000),
                    ("ground_vehicle", 9, 0, 2, 3, 2000, 5000),
                    ("sea_vessel", 5, 0, 2, 3, 2000, 5000),
                ],
            )

    def test_communications_and_sensor_ranges_are_typed(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            communications = connection.execute(
                """SELECT communication.communication_class,
                          range.range_code,range.maximum_range_km
                   FROM rule_vehicle_communication_system communication
                   JOIN rule_vehicle_electronics_range range
                     USING (range_code)
                   ORDER BY communication.communication_class"""
            ).fetchall()
            self.assertEqual(
                communications,
                [
                    (1, "distant", 5),
                    (2, "very-distant", 50),
                    (3, "regional", 500),
                    (4, "continental", 5000),
                ],
            )

            alternatives = connection.execute(
                """SELECT communicator_type_code,space_multiplier,
                          price_multiplier,
                          requires_clear_line_of_sight,
                          penetrates_smoke_aerosols,
                          cannot_be_jammed_or_blocked,
                          requires_stationary_vehicle
                   FROM rule_vehicle_communicator_type
                   ORDER BY minimum_tech_level"""
            ).fetchall()
            self.assertEqual(
                alternatives,
                [
                    ("laser", 2, 3, True, False, False, False),
                    ("maser", 4, 6, True, True, False, False),
                    ("meson", 10, 50, False, True, True, True),
                ],
            )

            standard = connection.execute(
                """SELECT package.published_range_text,
                          range.maximum_range_km,
                          package.communications_dm
                   FROM rule_vehicle_sensor_package package
                   JOIN rule_vehicle_electronics_range range
                     USING (range_code)
                   WHERE package.sensor_code='standard'"""
            ).fetchone()
            self.assertEqual(
                standard,
                ("Very Long (500 m)", Decimal("0.5"), -4),
            )

            capability_counts = connection.execute(
                """SELECT package.sensor_code,count(*)
                   FROM rule_vehicle_sensor_package package
                   JOIN rule_vehicle_sensor_package_capability capability
                     USING (component_rule_id)
                   GROUP BY package.sensor_code
                   ORDER BY package.sensor_code"""
            ).fetchall()
            self.assertEqual(
                capability_counts,
                [
                    ("advanced", 4),
                    ("basic-civilian", 2),
                    ("basic-military", 3),
                    ("standard", 2),
                    ("very-advanced", 5),
                ],
            )

    def test_computers_and_provenance_are_complete(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            computers = connection.execute(
                """SELECT computer.model_number,
                          computer.computer_rating,
                          computer.program_capacity,
                          component.minimum_tech_level,
                          component.unit_spaces,
                          component.unit_cost_minor
                   FROM rule_vehicle_computer computer
                   JOIN vehicle_component_definition component
                     ON component.component_rule_id=
                        computer.component_rule_id
                   ORDER BY computer.model_number"""
            ).fetchall()
            self.assertEqual(
                computers,
                [
                    (0, 0, 1, 7, Decimal("0.02"), 100),
                    (1, 1, 1, 8, Decimal("0.01"), 500),
                    (2, 2, 2, 10, Decimal("0"), 1000),
                    (3, 3, 3, 12, Decimal("0"), 2000),
                    (4, 4, 4, 13, Decimal("0"), 3000),
                    (5, 5, 5, 14, Decimal("0"), 10000),
                ],
            )

            counts = connection.execute(
                """SELECT
                     (SELECT count(*)
                        FROM vehicle_component_definition),
                     (SELECT count(*)
                        FROM src_record_provenance provenance
                        JOIN rule_rule rule USING (rule_id)
                       WHERE rule.rule_code LIKE
                             'vehicle.component.%'),
                     (SELECT count(*)
                        FROM src_open_issue_report
                       WHERE domain_code='vehicle.catalogue')"""
            ).fetchone()
            self.assertEqual(counts, (77, 156, 0))

            with connection.transaction(force_rollback=True):
                with self.assertRaises(CheckViolation):
                    connection.execute(
                        """UPDATE rule_vehicle_computer
                           SET computer_rating=5
                           WHERE model_number=0"""
                    )


if __name__ == "__main__":
    unittest.main()
