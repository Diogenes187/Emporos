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
class VehicleSourceAdjudicationTests(unittest.TestCase):
    def test_mechanical_source_adjudications_are_effective(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            components = connection.execute(
                """SELECT component_code,minimum_tech_level,unit_spaces,
                          unit_cost_minor,calculation_status
                     FROM vehicle_component_definition
                    WHERE component_code IN (
                        'control.primitive','additional.wet-bar')
                    ORDER BY component_code"""
            ).fetchall()
            sensor = connection.execute(
                """SELECT range_code,published_range_text
                     FROM rule_vehicle_sensor_package
                    WHERE sensor_code='standard'"""
            ).fetchone()
            missile = connection.execute(
                """SELECT radiation_hit_count,radiation_rule_status
                     FROM rule_vehicle_missile
                    WHERE missile_code='nuclear-nas-guided'"""
            ).fetchone()
            torpedo = connection.execute(
                """SELECT range_profile_code,published_range_token,
                          range_status,radiation_unit_status
                     FROM rule_vehicle_ordnance_definition
                    WHERE ordnance_code='torpedo-nuclear-heavy'"""
            ).fetchone()
        self.assertEqual(
            components,
            [
                ("additional.wet-bar", 2, 1.5, 2000, "adjudicated"),
                ("control.primitive", 1, 0.5, 0, "adjudicated"),
            ],
        )
        self.assertEqual(sensor, ("very-long", "Very Long (500 m)"))
        self.assertEqual(missile, (1, "adjudicated"))
        self.assertEqual(
            torpedo,
            (
                "very-distant", "ranged (very distant)",
                "adjudicated", "adjudicated-rads",
            ),
        )

    def test_adjudicated_receipts_preserve_published_versions(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            totals = connection.execute(
                """SELECT class.class_code,total.receipt_version,
                          total.receipt_status,total.stated_subtotal_credits,
                          total.discountable_cost_credits,
                          total.reconciliation_status
                     FROM vehicle_class_construction_receipt_total total
                     JOIN vehicle_class class USING(vehicle_class_rule_id)
                    WHERE class.class_code IN (
                        'afv-tracked','atv-tracked','destroyer-watercraft',
                        'g-carrier','grav-tank')
                      AND total.receipt_version=2
                    ORDER BY class.class_code"""
            ).fetchall()
            insidious = connection.execute(
                """SELECT class.class_code,line.published_cost_credits,
                          line.line_status
                     FROM vehicle_class_construction_line line
                     JOIN vehicle_class class USING(vehicle_class_rule_id)
                     JOIN vehicle_class_construction_receipt receipt
                       USING(construction_receipt_id,vehicle_class_rule_id)
                    WHERE class.class_code IN ('afv-tracked','atv-tracked')
                      AND receipt.receipt_version=2
                      AND line.reference_code=
                          'insidious-environmental-protection'
                    ORDER BY class.class_code"""
            ).fetchall()
        self.assertEqual(
            totals,
            [
                ("afv-tracked", 2, "adjudicated", Decimal("6264760.48"),
                 Decimal("6264760.48"), "published_cost_conflict"),
                ("atv-tracked", 2, "adjudicated", Decimal("6116560.48"),
                 Decimal("6116560.48"), "published_cost_conflict"),
                ("destroyer-watercraft", 2, "source_gap", None,
                 Decimal("58224590"), "source_gap"),
                ("g-carrier", 2, "adjudicated", Decimal("1518682.24"),
                 Decimal("1518682.24"), "published_cost_conflict"),
                ("grav-tank", 2, "adjudicated", Decimal("1732659.48"),
                 Decimal("1732659.48"), "published_cost_conflict"),
            ],
        )
        self.assertEqual(
            insidious,
            [
                ("afv-tracked", 6000000, "adjudicated"),
                ("atv-tracked", 6000000, "adjudicated"),
            ],
        )

    def test_weapon_points_and_issue_resolutions_are_auditable(self) -> None:
        issue_codes = (
            "vehicle.class.afv-weapon-points",
            "vehicle.class.destroyer-design-table-copy",
            "vehicle.class.destroyer-used-weapon-points",
            "vehicle.class.g-carrier-design-subtotal",
            "vehicle.class.grav-tank-subtotal-omits-weapon",
            "vehicle.class.tracked-insidious-protection-price",
            "vehicle.components.wet-bar-table",
            "vehicle.configuration.open-frame-copy-error",
            "vehicle.controls.primitive-tech-level",
            "vehicle.missile.nas-radiation-hit",
            "vehicle.ordnance.heavy-nuclear-torpedo-row",
            "vehicle.sensors.standard-range-distance",
            "ship.destroyer.construction.cost",
            "ship.destroyer.construction.tonnage-adjudicated-drives",
        )
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            weapon_points = connection.execute(
                """SELECT class.class_code,
                          summary.effective_available_weapon_points,
                          summary.calculated_used_weapon_points,
                          summary.effective_unused_weapon_points
                     FROM vehicle_class_weapon_point_summary summary
                     JOIN vehicle_class class USING(vehicle_class_rule_id)
                    WHERE class.class_code IN (
                        'afv-tracked','destroyer-watercraft')
                    ORDER BY class.class_code"""
            ).fetchall()
            statuses = dict(
                connection.execute(
                    "SELECT issue_code,issue_status FROM src_issue "
                    "WHERE issue_code=ANY(%s)",
                    (list(issue_codes),),
                ).fetchall()
            )
            decisions = connection.execute(
                """SELECT decision_register_entry
                     FROM rule_interpretation
                    WHERE decision_register_entry LIKE 'CE-VDS-%'
                    ORDER BY decision_register_entry"""
            ).fetchall()
        self.assertEqual(
            weapon_points,
            [
                ("afv-tracked", 2, 1, 1),
                ("destroyer-watercraft", 160, 22, 138),
            ],
        )
        self.assertEqual(statuses, {code: "resolved" for code in issue_codes})
        self.assertEqual(
            decisions,
            [(f"CE-VDS-{number:03d}",) for number in range(1, 31)],
        )

    def test_medium_priority_vehicle_decisions_are_effective(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            classes = connection.execute(
                """SELECT class_code,chassis_code,minimum_tech_level,
                          allocated_spaces,cargo_spaces,
                          construction_cost_minor
                     FROM vehicle_class
                    WHERE class_code IN (
                        'air-raft','biplane','submersible','steamship'
                    ) ORDER BY class_code"""
            ).fetchall()
            autopilots = connection.execute(
                """SELECT class.class_code,autopilot.skill_level,
                          autopilot.published_cost_minor,
                          autopilot.calculation_status
                     FROM vehicle_class_autopilot autopilot
                     JOIN vehicle_class class USING(vehicle_class_rule_id)
                    WHERE class.class_code IN (
                        'afv-tracked','atv-tracked','g-carrier'
                    ) ORDER BY class.class_code"""
            ).fetchall()
            guidance = connection.execute(
                """SELECT claim.guidance_code,claim.claim_role,
                          claim.mechanically_effective
                     FROM rule_vehicle_anti_missile_guidance_claim claim
                     JOIN rule_vehicle_anti_missile_system system
                       USING(system_rule_id)
                    WHERE system.system_code='decoys'
                    ORDER BY claim.guidance_code"""
            ).fetchall()
            rof = connection.execute(
                """SELECT rate_of_fire_multiplier,
                          rate_of_fire_rounding_method,calculation_status
                     FROM rule_vehicle_armament_option
                    WHERE option_code='heavy-turret-weapon'"""
            ).fetchone()
            rounding = connection.execute(
                """SELECT rounding_method,half_tie_method,
                          calculation_status
                     FROM rule_vehicle_space_rounding_policy
                    WHERE policy_code='submersible-ballast'"""
            ).fetchone()
        self.assertEqual(
            classes,
            [
                ("air-raft", "8", 9, Decimal("18.32"),
                 Decimal("29.68"), 94160),
                ("biplane", "5", 5, Decimal("11.01"),
                 Decimal("0.99"), 20670),
                ("steamship", None, 4, Decimal("1883.4"),
                 Decimal("516.6"), 5730030),
                ("submersible", None, 7, Decimal("659.73"),
                 Decimal("540.27"), 31062370),
            ],
        )
        self.assertEqual(
            autopilots,
            [
                ("afv-tracked", 1, 7000, "adjudicated"),
                ("atv-tracked", 1, 7000, "adjudicated"),
                ("g-carrier", 3, 17000, "adjudicated"),
            ],
        )
        self.assertEqual(
            guidance,
            [
                ("radar-guided", "parenthetical-label", False),
                ("smart-ai-guided", "primary-label", True),
                ("smart-computer-guided", "primary-label", True),
            ],
        )
        self.assertEqual(rof, (Decimal("0.5"), "exact-rational", "adjudicated"))
        self.assertEqual(rounding, ("nearest", "up", "adjudicated"))

    def test_adjudicated_mechanics_reject_silent_changes(self) -> None:
        statements = (
            "UPDATE vehicle_component_definition SET unit_spaces=1 "
            "WHERE component_code='additional.wet-bar'",
            "UPDATE vehicle_component_definition SET minimum_tech_level=2 "
            "WHERE component_code='control.primitive'",
            "UPDATE rule_vehicle_sensor_package "
            "SET published_range_text='Very Long (500 km)' "
            "WHERE sensor_code='standard'",
            "UPDATE rule_vehicle_missile SET radiation_hit_count=0 "
            "WHERE missile_code='nuclear-nas-guided'",
            "UPDATE rule_vehicle_ordnance_definition "
            "SET range_profile_code='very-long' "
            "WHERE ordnance_code='torpedo-nuclear-heavy'",
            "UPDATE vehicle_class_weapon_point_summary "
            "SET calculated_used_weapon_points=23 "
            "WHERE vehicle_class_rule_id=(SELECT vehicle_class_rule_id "
            "FROM vehicle_class WHERE class_code='destroyer-watercraft')",
        )
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            for statement in statements:
                with self.assertRaises(CheckViolation):
                    with connection.transaction():
                        connection.execute(statement)
                connection.rollback()


if __name__ == "__main__":
    unittest.main()
