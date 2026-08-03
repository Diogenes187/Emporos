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
class CommonAircraftHovercraftTests(unittest.TestCase):
    def test_published_profiles_are_relational(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            profiles = connection.execute(
                """SELECT class_code,chassis_code,minimum_tech_level,
                          configuration,armor_rating,hull_points,
                          structure_points,allocated_spaces,cargo_spaces,
                          construction_cost_minor,construction_hours
                   FROM vehicle_class
                   WHERE class_code IN (
                       'biplane','helicopter',
                       'twin-engine-jet','hovercraft'
                   )
                   ORDER BY class_code"""
            ).fetchall()
            self.assertEqual(
                profiles,
                [
                    (
                        "biplane",
                        "5",
                        5,
                        "open",
                        2,
                        0,
                        1,
                        Decimal("11.01"),
                        Decimal("0.99"),
                        20670,
                        9,
                    ),
                    (
                        "helicopter",
                        "8",
                        7,
                        "closed",
                        3,
                        0,
                        1,
                        Decimal("36.14"),
                        Decimal("11.86"),
                    154850,
                        36,
                    ),
                    (
                        "hovercraft",
                        "C",
                        7,
                        "closed",
                        3,
                        1,
                        2,
                        Decimal("43.73"),
                        Decimal("52.27"),
                        144660,
                        36,
                    ),
                    (
                        "twin-engine-jet",
                        "9",
                        7,
                        "closed",
                        3,
                        1,
                        1,
                        Decimal("42.78"),
                        Decimal("17.22"),
                        736110,
                        45,
                    ),
                ],
            )

    def test_power_plants_propulsion_and_agility_are_typed(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            drives = connection.execute(
                """SELECT class.class_code,plant.drive_code,
                          plant.power_plant_code,
                          propulsion.propulsion_code,
                          propulsion.speed_variant,
                          propulsion.performance,
                          propulsion.reported_top_speed,
                          propulsion.reported_cruise_speed,
                          propulsion.reported_agility_dm
                   FROM vehicle_class class
                   JOIN vehicle_class_power_plant plant
                     USING (vehicle_class_rule_id)
                   JOIN vehicle_class_propulsion propulsion
                     USING (vehicle_class_rule_id)
                   WHERE class.class_code IN (
                       'biplane','helicopter',
                       'twin-engine-jet','hovercraft'
                   )
                   ORDER BY class.class_code"""
            ).fetchall()
            self.assertEqual(
                drives,
                [
                    (
                        "biplane",
                        "D",
                        "internal-combustion",
                        "rotor",
                        "horizontal",
                        2,
                        Decimal("200"),
                        Decimal("150"),
                        -1,
                    ),
                    (
                        "helicopter",
                        "M",
                        "gas-turbine",
                        "rotor",
                        "vertical",
                        5,
                        Decimal("250"),
                        Decimal("187.5"),
                        -2,
                    ),
                    (
                        "hovercraft",
                        "L",
                        "gas-turbine",
                        "air-cushion",
                        "standard",
                        2,
                        Decimal("100"),
                        Decimal("75"),
                        1,
                    ),
                    (
                        "twin-engine-jet",
                        "N",
                        "gas-turbine",
                        "jet",
                        "standard",
                        5,
                        Decimal("750"),
                        Decimal("562.5"),
                        -1,
                    ),
                ],
            )

    def test_every_standard_vehicle_has_published_agility(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            coverage = connection.execute(
                """SELECT count(*),
                          count(
                              coalesce(
                                  propulsion.reported_agility_dm,
                                  ship_propulsion.reported_agility_dm
                              )
                          )
                   FROM vehicle_class class
                   LEFT JOIN vehicle_class_propulsion propulsion
                     USING (vehicle_class_rule_id)
                   LEFT JOIN vehicle_class_ship_scale_propulsion
                             ship_propulsion
                     USING (vehicle_class_rule_id)
                   WHERE class.standard_design"""
            ).fetchone()
            self.assertEqual(coverage, (20, 20))

    def test_biplane_uses_governing_one_ton_chassis(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            adjudication = connection.execute(
                """SELECT class.chassis_code,chassis.displacement_tons,
                          chassis.spaces,issue.engine_disposition
                   FROM vehicle_class class
                   JOIN rule_vehicle_chassis chassis USING (chassis_code)
                   JOIN src_issue issue
                     ON issue.issue_code=
                        'vehicle.class.biplane-chassis-code'
                   WHERE class.class_code='biplane'"""
            ).fetchone()
            self.assertEqual(
                adjudication,
                ("5", Decimal("1"), 12, "preserve_rule"),
            )

    def test_profile_capacity_is_database_enforced(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            with connection.transaction(force_rollback=True):
                with self.assertRaises(CheckViolation):
                    connection.execute(
                        """UPDATE vehicle_class
                           SET cargo_spaces=1.01
                           WHERE class_code='biplane'"""
                    )

    def test_profiles_have_paired_provenance(self) -> None:
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
                       'vehicle.class.biplane',
                       'vehicle.class.helicopter',
                       'vehicle.class.twin-engine-jet',
                       'vehicle.class.hovercraft'
                   )"""
            ).fetchone()
            self.assertEqual(provenance, (8, 4, 4))

            issue_evidence = connection.execute(
                """SELECT count(*),
                          count(DISTINCT locator.evidence_role),
                          count(comparison.source_issue_id)
                   FROM src_issue issue
                   JOIN src_issue_locator locator
                     USING (source_issue_id)
                   LEFT JOIN src_issue_comparison_check comparison
                     USING (source_issue_id)
                   WHERE issue.issue_code=
                         'vehicle.class.biplane-chassis-code'"""
            ).fetchone()
            self.assertEqual(issue_evidence, (2, 2, 2))

    def test_air_raft_profile_cost_matches_publication(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            cost = connection.execute(
                """SELECT construction_cost_minor
                   FROM vehicle_class
                   WHERE class_code='air-raft'"""
            ).fetchone()
            self.assertEqual(cost, (94160,))


if __name__ == "__main__":
    unittest.main()
