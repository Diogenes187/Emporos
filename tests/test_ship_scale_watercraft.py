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
class ShipScaleWatercraftTests(unittest.TestCase):
    def test_watercraft_remain_vehicle_classes(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            profiles = connection.execute(
                """SELECT class.class_code,class.chassis_code,
                          class.minimum_tech_level,class.armor_rating,
                          class.hull_points,class.structure_points,
                          class.allocated_spaces,class.cargo_spaces,
                          class.construction_cost_minor,
                          class.construction_hours,
                          hull.ship_hull_code,
                          hull.published_base_spaces,
                          hull.published_base_cost_minor,
                          hull.space_combat_hull_points
                   FROM vehicle_class class
                   JOIN vehicle_class_ship_scale_hull hull
                     USING (vehicle_class_rule_id)
                   ORDER BY class.class_code"""
            ).fetchall()
            self.assertEqual(
                profiles,
                [
                    (
                        "destroyer-watercraft",
                        None,
                        9,
                        6,
                        160,
                        160,
                        Decimal("8752.62"),
                        Decimal("847.38"),
                        51521940,
                        15456,
                        "8",
                        Decimal("9600"),
                        20000000,
                        16,
                    ),
                    (
                        "motor-boat",
                        None,
                        5,
                        2,
                        12,
                        12,
                        Decimal("447.15"),
                        Decimal("272.85"),
                        2698450,
                        5376,
                        "sB",
                        Decimal("720"),
                        400000,
                        1,
                    ),
                    (
                        "steamship",
                        None,
                        4,
                        2,
                        40,
                        40,
                        Decimal("1883.4"),
                        Decimal("516.6"),
                        5730030,
                        7392,
                        "2",
                        Decimal("2400"),
                        2000000,
                        4,
                    ),
                    (
                        "submersible",
                        None,
                        7,
                        2,
                        20,
                        20,
                        Decimal("659.73"),
                        Decimal("540.27"),
                        31062370,
                        6048,
                        "1",
                        Decimal("1200"),
                        3000000,
                        2,
                    ),
                ],
            )

    def test_ship_scale_drives_retain_vehicle_propulsion(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            drives = connection.execute(
                """SELECT class.class_code,plant.craft_scale,
                          plant.drive_code,plant.power_plant_code,
                          plant.published_spaces,
                          plant.published_cost_minor,
                          propulsion.propulsion_code,
                          propulsion.performance,
                          propulsion.reported_top_speed,
                          propulsion.reported_cruise_speed,
                          propulsion.reported_agility_dm
                   FROM vehicle_class class
                   JOIN vehicle_class_ship_scale_power_plant plant
                     USING (vehicle_class_rule_id)
                   JOIN vehicle_class_ship_scale_propulsion propulsion
                     USING (vehicle_class_rule_id)
                   ORDER BY class.class_code"""
            ).fetchall()
            self.assertEqual(
                drives,
                [
                    (
                        "destroyer-watercraft",
                        "starship",
                        "K",
                        "early-fusion",
                        Decimal("338.4"),
                        480000,
                        "screw-propeller",
                        3,
                        Decimal("60"),
                        Decimal("45"),
                        -3,
                    ),
                    (
                        "motor-boat",
                        "small_craft",
                        "sC",
                        "internal-combustion",
                        Decimal("116.64"),
                        1200,
                        "screw-propeller",
                        5,
                        Decimal("100"),
                        Decimal("75"),
                        -2,
                    ),
                    (
                        "steamship",
                        "starship",
                        "B",
                        "external-combustion",
                        Decimal("1134"),
                        19200,
                        "screw-propeller",
                        2,
                        Decimal("40"),
                        Decimal("30"),
                        -5,
                    ),
                    (
                        "submersible",
                        "starship",
                        "C",
                        "fission",
                        Decimal("86.4"),
                        96000,
                        "screw-propeller",
                        2,
                        Decimal("40"),
                        Decimal("30"),
                        -5,
                    ),
                ],
            )

    def test_ship_scale_hull_capacity_is_enforced(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            with connection.transaction(force_rollback=True):
                with self.assertRaises(CheckViolation):
                    connection.execute(
                        """UPDATE vehicle_class
                           SET cargo_spaces=cargo_spaces+1
                           WHERE class_code='motor-boat'"""
                    )

    def test_ship_scale_hull_formula_is_enforced(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            with connection.transaction(force_rollback=True):
                with self.assertRaises(CheckViolation):
                    connection.execute(
                        """UPDATE vehicle_class_ship_scale_hull hull
                           SET published_base_spaces=721
                           FROM vehicle_class class
                           WHERE class.vehicle_class_rule_id=
                                 hull.vehicle_class_rule_id
                             AND class.class_code='motor-boat'"""
                    )

    def test_ship_scale_selection_is_deferred_but_required(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            with connection.transaction(force_rollback=True):
                connection.execute(
                    """DELETE FROM vehicle_class_ship_scale_power_plant plant
                       USING vehicle_class class
                       WHERE class.vehicle_class_rule_id=
                             plant.vehicle_class_rule_id
                         AND class.class_code='steamship'"""
                )
                with self.assertRaises(CheckViolation):
                    connection.execute("SET CONSTRAINTS ALL IMMEDIATE")

    def test_profiles_and_destroyer_issue_have_paired_evidence(
        self,
    ) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            provenance = connection.execute(
                """SELECT count(*),
                          count(*) FILTER (
                              WHERE provenance_class='fills_source_gap'
                                AND is_primary_citation
                          ),
                          count(*) FILTER (
                              WHERE provenance_class='corroborating'
                                AND NOT is_primary_citation
                          )
                   FROM src_record_provenance provenance
                   JOIN rule_rule rule
                     ON rule.rule_id=provenance.rule_id
                   WHERE rule.rule_code IN (
                       'vehicle.class.destroyer-watercraft',
                       'vehicle.class.motor-boat',
                       'vehicle.class.steamship',
                       'vehicle.class.submersible'
                   )"""
            ).fetchone()
            self.assertEqual(provenance, (8, 4, 4))

            issue = connection.execute(
                """SELECT report.review_priority,
                          report.engine_disposition,
                          count(DISTINCT locator.source_locator_id),
                          count(DISTINCT comparison.comparison_work_id)
                   FROM src_issue report
                   JOIN src_issue issue
                     USING (issue_code)
                   JOIN src_issue_locator locator
                     ON locator.source_issue_id=issue.source_issue_id
                   LEFT JOIN src_issue_comparison_check comparison
                     ON comparison.source_issue_id=issue.source_issue_id
                   WHERE report.issue_code=
                         'vehicle.class.destroyer-design-table-copy'
                   GROUP BY report.review_priority,
                            report.engine_disposition"""
            ).fetchone()
            self.assertEqual(issue, ("high", "preserve_rule", 2, 1))


if __name__ == "__main__":
    unittest.main()
