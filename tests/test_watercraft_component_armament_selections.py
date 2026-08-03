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
class WatercraftComponentArmamentSelectionTests(unittest.TestCase):
    def test_watercraft_component_ledgers_are_relational(self) -> None:
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
                   WHERE class.class_code IN (
                       'destroyer-watercraft','motor-boat',
                       'steamship','submersible'
                   )
                   GROUP BY class.class_code
                   ORDER BY class.class_code"""
            ).fetchall()
            self.assertEqual(
                totals,
                [
                    (
                        "destroyer-watercraft",
                        6,
                        Decimal("1724.11"),
                        14614500,
                    ),
                    (
                        "motor-boat",
                        4,
                        Decimal("313.02"),
                        2521000,
                    ),
                    ("steamship", 4, Decimal("625"), 4039500),
                    (
                        "submersible",
                        8,
                        Decimal("538.05"),
                        4399000,
                    ),
                ],
            )

    def test_formula_and_tech_adjudications_are_explicit(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            selections = connection.execute(
                """SELECT class.class_code,component.component_code,
                          selection.quantity,selection.rating,
                          selection.allocated_spaces,
                          selection.published_cost_minor,
                          selection.calculation_status,
                          selection.tech_level_status
                   FROM vehicle_class_component selection
                   JOIN vehicle_class class
                     USING (vehicle_class_rule_id)
                   JOIN vehicle_component_definition component
                     USING (component_rule_id)
                   WHERE component.component_code IN (
                       'additional.galley-full',
                       'life-support.extended'
                   )
                     AND class.class_code IN (
                         'destroyer-watercraft','motor-boat',
                         'steamship','submersible'
                     )
                   ORDER BY class.class_code,
                            component.component_code"""
            ).fetchall()
            self.assertEqual(
                selections,
                [
                    (
                        "steamship",
                        "additional.galley-full",
                        1,
                        Decimal("15"),
                        Decimal("24"),
                        9500,
                        "formula",
                        "matches",
                    ),
                    (
                        "submersible",
                        "additional.galley-full",
                        1,
                        Decimal("15"),
                        Decimal("24"),
                        9500,
                        "formula",
                        "matches",
                    ),
                    (
                        "submersible",
                        "life-support.extended",
                        3,
                        None,
                        Decimal("9"),
                        157500,
                        "matches",
                        "adjudicated",
                    ),
                ],
            )

    def test_options_autopilots_and_fuel_are_typed(self) -> None:
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
                        FROM vehicle_class_autopilot),
                     (SELECT count(*)
                        FROM vehicle_class_computer_option),
                     (SELECT count(*)
                        FROM vehicle_class_fuel_tank)"""
            ).fetchone()
            self.assertEqual(counts, (11, 3, 10, 3, 19))

            autopilots = connection.execute(
                """SELECT class.class_code,rule.rule_code,
                          autopilot.skill_level,
                          autopilot.published_cost_minor
                   FROM vehicle_class_autopilot autopilot
                   JOIN vehicle_class class
                     USING (vehicle_class_rule_id)
                   JOIN rule_rule rule
                     ON rule.rule_id=autopilot.skill_rule_id
                   WHERE class.class_code IN (
                       'destroyer-watercraft','submersible'
                   )
                   ORDER BY class.class_code"""
            ).fetchall()
            self.assertEqual(
                autopilots,
                [
                    (
                        "destroyer-watercraft",
                        "skill.ocean-ships",
                        2,
                        12000,
                    ),
                    ("submersible", "skill.submarine", 0, 2000),
                ],
            )

    def test_component_formula_is_database_enforced(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            with connection.transaction(force_rollback=True):
                with self.assertRaises(CheckViolation):
                    connection.execute(
                        """UPDATE vehicle_class_component selection
                           SET allocated_spaces=23
                           FROM vehicle_class class,
                                vehicle_component_definition component
                           WHERE class.vehicle_class_rule_id=
                                 selection.vehicle_class_rule_id
                             AND component.component_rule_id=
                                 selection.component_rule_id
                             AND class.class_code='steamship'
                             AND component.component_code=
                                 'additional.galley-full'"""
                    )

    def test_destroyer_weapon_points_remain_reconciled(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            summary = connection.execute(
                """SELECT published_available_weapon_points,
                          calculated_available_weapon_points,
                          published_used_weapon_points,
                          calculated_used_weapon_points,
                          used_reconciliation_status
                   FROM vehicle_class_weapon_point_summary summary
                   JOIN vehicle_class class
                     USING (vehicle_class_rule_id)
                   WHERE class.class_code='destroyer-watercraft'"""
            ).fetchone()
            self.assertEqual(
                summary,
                (160, 160, 23, 22, "source-conflict"),
            )

            mounts = connection.execute(
                """SELECT mount_sequence,quantity,weapon_points_each,
                          weapon_mount_rule_id IS NOT NULL,
                          turret_rule_id IS NOT NULL,
                          ordnance_bay_rule_id IS NOT NULL
                   FROM vehicle_class_armament_mount mount
                   JOIN vehicle_class class
                     USING (vehicle_class_rule_id)
                   WHERE class.class_code='destroyer-watercraft'
                   ORDER BY mount_sequence"""
            ).fetchall()
            self.assertEqual(
                mounts,
                [
                    (1, 4, 1, False, True, False),
                    (2, 1, 4, False, True, False),
                    (3, 8, 1, False, True, False),
                    (4, 4, 1, True, False, False),
                    (5, 2, 1, False, False, True),
                ],
            )

    def test_destroyer_ammunition_and_ordnance_are_typed(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            ammunition = connection.execute(
                """SELECT weapon_family_code,round_count,
                          allocated_spaces,published_cost_minor
                   FROM vehicle_class_weapon_ammunition_load
                   ORDER BY weapon_family_code"""
            ).fetchall()
            self.assertEqual(
                ammunition,
                [
                    ("autocannon", 1800, Decimal("72"), 288000),
                    ("mass-driver", 300, Decimal("150"), 1350000),
                    (
                        "rocket-artillery",
                        900,
                        Decimal("300"),
                        1500000,
                    ),
                ],
            )

            loads = connection.execute(
                """SELECT
                     (SELECT missile_count
                        FROM vehicle_class_missile_load),
                     (SELECT ordnance_count
                        FROM vehicle_class_ordnance_load),
                     (SELECT loaded_per_mount
                        FROM vehicle_class_armament_missile),
                     (SELECT loaded_per_bay
                        FROM vehicle_class_armament_ordnance)"""
            ).fetchone()
            self.assertEqual(loads, (900, 240, 1, 3))

    def test_new_source_findings_have_paired_evidence(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            evidence = connection.execute(
                """SELECT issue.issue_code,
                          count(DISTINCT locator.source_locator_id),
                          count(DISTINCT comparison.comparison_work_id)
                   FROM src_issue issue
                   JOIN src_issue_locator locator
                     USING (source_issue_id)
                   LEFT JOIN src_issue_comparison_check comparison
                     USING (source_issue_id)
                   WHERE issue.issue_code IN (
                       'vehicle.class.submersible-life-support-tech-level',
                       'vehicle.class.destroyer-used-weapon-points',
                       'vehicle.class.destroyer-heavy-weapon-labels'
                   )
                   GROUP BY issue.issue_code
                   ORDER BY issue.issue_code"""
            ).fetchall()
            self.assertEqual(
                evidence,
                [
                    (
                        "vehicle.class.destroyer-heavy-weapon-labels",
                        2,
                        1,
                    ),
                    (
                        "vehicle.class.destroyer-used-weapon-points",
                        2,
                        1,
                    ),
                    (
                        "vehicle.class.submersible-life-support-tech-level",
                        2,
                        1,
                    ),
                ],
            )


if __name__ == "__main__":
    unittest.main()
