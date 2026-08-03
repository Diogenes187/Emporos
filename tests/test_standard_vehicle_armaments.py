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
class StandardVehicleArmamentTests(unittest.TestCase):
    def test_weapon_point_summaries_preserve_published_conflict(
        self,
    ) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            rows = connection.execute(
                """SELECT class.class_code,
                          summary.published_available_weapon_points,
                          summary.calculated_available_weapon_points,
                          summary.published_used_weapon_points,
                          summary.calculated_used_weapon_points,
                          summary.used_reconciliation_status,
                          summary.reconciliation_status,
                          summary.effective_available_weapon_points,
                          summary.effective_unused_weapon_points,
                          summary.adjudication_basis
                   FROM vehicle_class_weapon_point_summary summary
                   JOIN vehicle_class class
                     USING (vehicle_class_rule_id)
                   ORDER BY class.class_code"""
            ).fetchall()
            self.assertEqual(
                rows,
                [
                    (
                        "afv-tracked", 1, 2, 1, 1, "matches",
                        "source-conflict",
                        2, 1, "governing-rule",
                    ),
                    (
                        "destroyer-watercraft", 160, 160, 23, 22,
                        "source-conflict", "matches",
                        160, 138, "published-profile",
                    ),
                    (
                        "g-carrier", 1, 1, 1, 1, "matches", "matches",
                        1, 0, "published-profile",
                    ),
                    (
                        "grav-tank", 1, 1, 1, 1, "matches", "matches",
                        1, 0, "published-profile",
                    ),
                ],
            )

    def test_published_mounts_and_weapons_are_linked(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            rows = connection.execute(
                """SELECT class.class_code,mount.quantity,
                          weapon_mount.mount_code,turret.turret_code,
                          mount.weapon_points_each,
                          mount.published_mount_spaces_each,
                          mount.published_mount_cost_each_minor,
                          weapon.weapon_code,
                          selection.published_weapon_spaces_each,
                          selection.published_weapon_cost_each_minor,
                          selection.reconciliation_status
                   FROM vehicle_class_armament_mount mount
                   JOIN vehicle_class class
                     USING (vehicle_class_rule_id)
                   LEFT JOIN rule_vehicle_weapon_mount weapon_mount
                     ON weapon_mount.mount_rule_id=
                        mount.weapon_mount_rule_id
                   LEFT JOIN rule_vehicle_turret turret
                     ON turret.turret_rule_id=mount.turret_rule_id
                   JOIN vehicle_class_armament_weapon selection
                     USING (class_armament_mount_id)
                   JOIN rule_vehicle_weapon_definition weapon
                     USING (weapon_rule_id)
                   ORDER BY class.class_code,mount.mount_sequence"""
            ).fetchall()
            self.assertEqual(
                rows,
                [
                    (
                        "afv-tracked", 1, None, "small", 1,
                        Decimal("0.5"), 4000,
                        "beam-laser-tl-11", 3, 120000, "matches",
                    ),
                    (
                        "destroyer-watercraft", 4, None, "small", 1,
                        Decimal("0.5"), 4000,
                        "autocannon-tl-8", 24, 300000, "matches",
                    ),
                    (
                        "destroyer-watercraft", 1, None, "small", 4,
                        Decimal("0.5"), 4000,
                        "mass-driver-tl-8", 180, 250000, "matches",
                    ),
                    (
                        "destroyer-watercraft", 8, None, "small", 1,
                        Decimal("0.5"), 4000,
                        "rocket-artillery-tl-7", 15, 10000, "matches",
                    ),
                    (
                        "destroyer-watercraft", 4, "fixed", None, 1,
                        0, 0, "missile-rack", 12, 48000, "matches",
                    ),
                    (
                        "g-carrier", 1, "ring-powered", None, 1,
                        0, 2150, "fusion-gun-tl-15", 3,
                        200000, "matches",
                    ),
                    (
                        "grav-tank", 1, None, "small", 1,
                        Decimal("0.5"), 4000,
                        "beam-laser-tl-9", 3, 100000, "matches",
                    ),
                ],
            )

    def test_g_carrier_gun_shield_is_rule_derived(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            shield = connection.execute(
                """SELECT class.class_code,mount_definition.mount_code,
                          selection.published_armor_rating,
                          shield.cost_per_armor_point_minor,
                          selection.published_cost_minor
                   FROM vehicle_class_armament_gun_shield selection
                   JOIN vehicle_class_armament_mount mount
                     USING (class_armament_mount_id)
                   JOIN vehicle_class class
                     USING (vehicle_class_rule_id)
                   JOIN rule_vehicle_weapon_mount mount_definition
                     ON mount_definition.mount_rule_id=
                        mount.weapon_mount_rule_id
                   JOIN rule_vehicle_gun_shield shield
                     USING (option_rule_id)"""
            ).fetchone()
            self.assertEqual(
                shield,
                ("g-carrier", "ring-powered", 7, 200, 1400),
            )

    def test_turret_price_basis_matches_common_designs(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            turret = connection.execute(
                """SELECT base_spaces,price_per_base_space_minor,
                          base_spaces*price_per_base_space_minor
                   FROM rule_vehicle_turret
                   WHERE turret_code='small'"""
            ).fetchone()
            self.assertEqual(
                turret,
                (Decimal("0.5"), 8000, Decimal("4000.0")),
            )

    def test_armament_constraints_reject_oversized_weapon(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            mass_driver_id = connection.execute(
                """SELECT weapon_rule_id
                   FROM rule_vehicle_weapon_definition
                   WHERE weapon_code='mass-driver-tl-8'"""
            ).fetchone()[0]
            with connection.transaction(force_rollback=True):
                with self.assertRaises(CheckViolation):
                    connection.execute(
                        """UPDATE vehicle_class_armament_weapon selection
                           SET weapon_rule_id=%s,
                               published_weapon_spaces_each=180,
                               published_weapon_cost_each_minor=250000
                           FROM vehicle_class_armament_mount mount
                           JOIN vehicle_class class
                             USING (vehicle_class_rule_id)
                           WHERE mount.class_armament_mount_id=
                                 selection.class_armament_mount_id
                             AND class.class_code='g-carrier'""",
                        (mass_driver_id,),
                    )

    def test_afv_source_issue_and_legacy_check_are_recorded(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            row = connection.execute(
                """SELECT issue.review_priority,issue.published_value,
                          issue.calculated_value,
                          issue.engine_disposition,
                          count(comparison.*)
                   FROM src_issue issue
                   JOIN src_issue_comparison_check comparison
                     USING (source_issue_id)
                   WHERE issue.issue_code=
                         'vehicle.class.afv-weapon-points'
                   GROUP BY issue.source_issue_id"""
            ).fetchone()
            self.assertEqual(
                row,
                (
                    "high", "One weapon point", "Two weapon points",
                    "preserve_rule", 1,
                ),
            )


if __name__ == "__main__":
    unittest.main()
