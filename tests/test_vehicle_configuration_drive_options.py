from __future__ import annotations

import os
import unittest
from decimal import Decimal

import psycopg
from psycopg.errors import ForeignKeyViolation


@unittest.skipUnless(
    os.environ.get("BASE_CEPHEUS_DATABASE_URL"),
    "BASE_CEPHEUS_DATABASE_URL is not configured",
)
class VehicleConfigurationDriveOptionTests(unittest.TestCase):
    def test_configurations_define_price_cover_and_fire_access(
        self,
    ) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            configurations = connection.execute(
                """SELECT configuration.configuration_code,
                          configuration.chassis_price_multiplier,
                          configuration.sealed_or_airtight,
                          configuration.unrestricted_attack_direction,
                          cover.vehicle_use_code,cover.cover_code,
                          cover.shooters_per_arc,
                          cover.all_occupants_may_attack
                   FROM rule_vehicle_configuration configuration
                   JOIN rule_vehicle_configuration_cover cover
                     USING (configuration_rule_id)
                   ORDER BY configuration.configuration_code,
                            cover.vehicle_use_code"""
            ).fetchall()
            self.assertEqual(
                configurations,
                [
                    (
                        "closed", 1, False, False, "civilian",
                        "half-soft", 2, False,
                    ),
                    (
                        "closed", 1, False, False, "military",
                        "full-hard", 1, False,
                    ),
                    (
                        "open", Decimal("0.9"), False, True,
                        "civilian", "none", None, True,
                    ),
                    (
                        "open", Decimal("0.9"), False, True,
                        "military", "none", None, True,
                    ),
                ],
            )
            with connection.transaction(force_rollback=True):
                with self.assertRaises(ForeignKeyViolation):
                    connection.execute(
                        """DELETE FROM rule_vehicle_configuration
                           WHERE configuration_code='open'"""
                    )

    def test_configuration_options_preserve_exact_cost_bases(
        self,
    ) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            rows = connection.execute(
                """SELECT option_code,minimum_tech_level,
                          required_configuration_code,
                          space_basis,space_value,space_rounding,
                          price_basis,price_value,
                          base_speed_multiplier,construction_only,
                          requires_life_support,calculation_status
                   FROM rule_vehicle_configuration_option
                   ORDER BY option_code"""
            ).fetchall()
            self.assertEqual(len(rows), 11)
            self.assertIn(
                (
                    "corrosive-environmental-protection", 9,
                    "closed", "fixed", 6, "exact",
                    "per-chassis-space", 10000, None,
                    False, True, "published",
                ),
                rows,
            )
            self.assertIn(
                (
                    "open-frame", None, None, "none", 0, "exact",
                    "chassis-price-reduction-percent", 20, None,
                    False, False, "adjudicated",
                ),
                rows,
            )
            self.assertIn(
                (
                    "wave-piercing-hull", None, None,
                    "chassis-percent", 5, "ceiling",
                    "chassis-price-percent", 200,
                    Decimal("1.1"), False, False, "published",
                ),
                rows,
            )
            combinations = connection.execute(
                """SELECT option.option_code,
                          combined_chassis_price_reduction_percent,
                          replaces_individual_reductions,
                          combination.calculation_status
                   FROM rule_vehicle_configuration_price_combination
                        combination
                   JOIN rule_vehicle_configuration_option option
                     USING (option_rule_id)
                   ORDER BY option.option_code"""
            ).fetchall()
            self.assertEqual(
                combinations,
                [
                    ("open-cargo-bed", 25, True, "published"),
                    ("open-frame", 25, True, "adjudicated"),
                ],
            )

    def test_environmental_protection_is_hazard_relational(
        self,
    ) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            counts = connection.execute(
                """SELECT option.option_code,count(hazard.hazard_code)
                   FROM rule_vehicle_environmental_protection protection
                   JOIN rule_vehicle_configuration_option option
                     USING (option_rule_id)
                   JOIN rule_vehicle_environmental_protection_hazard hazard
                     USING (option_rule_id)
                   GROUP BY option.option_code
                   ORDER BY option.option_code"""
            ).fetchall()
            self.assertEqual(
                counts,
                [
                    ("corrosive-environmental-protection", 6),
                    ("hostile-environmental-protection", 5),
                    ("insidious-environmental-protection", 6),
                    ("vacuum-environmental-protection", 6),
                ],
            )
            insidious = connection.execute(
                """SELECT protected_duration_days,
                          hull_structure_damage_per_day_after_duration
                   FROM rule_vehicle_environmental_protection protection
                   JOIN rule_vehicle_configuration_option option
                     USING (option_rule_id)
                   WHERE option.option_code=
                         'insidious-environmental-protection'"""
            ).fetchone()
            self.assertEqual(insidious, (5, 1))
            inclusions = connection.execute(
                """SELECT included_option.option_code,
                          component.component_code,
                          inclusion.included_spaces,
                          inclusion.included_cost_minor
                   FROM rule_vehicle_configuration_option_inclusion
                        inclusion
                   LEFT JOIN rule_vehicle_configuration_option
                        included_option
                     ON included_option.option_rule_id=
                        inclusion.included_option_rule_id
                   LEFT JOIN vehicle_component_definition component
                     ON component.component_rule_id=
                        inclusion.included_component_rule_id
                   ORDER BY included_option.option_code NULLS LAST"""
            ).fetchall()
            self.assertEqual(
                inclusions,
                [
                    (
                        "hostile-environmental-protection",
                        None, 3, 0,
                    ),
                    (None, "life-support.basic", 3, 0),
                ],
            )

    def test_submersible_depth_rules_keep_rounding_gap_visible(
        self,
    ) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            depths = connection.execute(
                """SELECT minimum_tech_level,maximum_tech_level,
                          safe_dive_depth_metres,crush_depth_metres
                   FROM rule_vehicle_submersible_depth
                   ORDER BY minimum_tech_level"""
            ).fetchall()
            self.assertEqual(
                depths,
                [
                    (4, 5, 50, 150),
                    (6, 8, 200, 600),
                    (9, 11, 600, 1800),
                    (12, 14, 2000, 6000),
                    (15, 16, 4000, 12000),
                    (17, None, 8000, 24000),
                ],
            )
            formulas = connection.execute(
                """SELECT world.baseline_world_size,
                          world.depth_percent_per_size_difference,
                          world.larger_world_depth_direction,
                          upgrade.depth_multiplier_per_step,
                          upgrade.remaining_space_multiplier_per_step,
                          upgrade.chassis_price_increase_percent_per_step,
                          upgrade.space_rounding
                   FROM rule_vehicle_submersible_world_adjustment world
                   JOIN rule_vehicle_submersible_depth_upgrade upgrade
                     USING (option_rule_id)"""
            ).fetchone()
            self.assertEqual(
                formulas,
                (
                    8, 10, "decrease", 2, Decimal("0.5"),
                    100, "source-unspecified",
                ),
            )

    def test_drive_adjustments_and_secondary_drive_are_numeric(
        self,
    ) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            adjustments = connection.execute(
                """SELECT option.option_code,
                          adjustment.agility_dm_per_step,
                          adjustment.maximum_steps,
                          adjustment.fuel_consumption_multiplier,
                          adjustment.chassis_price_adjustment_percent_per_step
                   FROM rule_vehicle_drive_adjustment_option adjustment
                   JOIN rule_vehicle_drive_option option
                     USING (option_rule_id)
                   ORDER BY option.option_code"""
            ).fetchall()
            self.assertEqual(
                adjustments,
                [
                    ("decreased-agility", -1, 2, None, -25),
                    (
                        "decreased-fuel-efficiency", None, None,
                        Decimal("1.25"), -10,
                    ),
                    ("increased-agility", 1, 3, None, 50),
                    (
                        "increased-fuel-efficiency", None, None,
                        Decimal("0.9"), 20,
                    ),
                ],
            )
            secondary = connection.execute(
                """SELECT secondary_performance_offset,agility_dm,
                          purchase_second_propulsion_drive
                   FROM rule_vehicle_secondary_drive_option"""
            ).fetchone()
            self.assertEqual(secondary, (-1, -1, True))

    def test_contact_jump_offroad_and_tilt_options_are_typed(
        self,
    ) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            contact = connection.execute(
                """SELECT element_code,drive_price_percent_per_element,
                          drive_space_percent_per_element,
                          elements_per_terrain_penalty_reduction,
                          terrain_penalty_reduction,
                          standard_element_count,
                          small_vehicle_element_count,
                          small_vehicle_maximum_tons,
                          attack_dm_threshold_element_count,attack_dm
                   FROM rule_vehicle_extra_contact_element
                   ORDER BY element_code"""
            ).fetchall()
            self.assertEqual(
                contact,
                [
                    ("leg", 25, 5, 2, 1, 2, None, None, 4, 1),
                    (
                        "wheel-pair", 25, 25, 1, 1, 2, 1,
                        Decimal("0.5"), None, None,
                    ),
                ],
            )
            jump = connection.execute(
                """SELECT selected_drive_basis,
                          minimum_drive_performance,
                          drive_space_multiplier,
                          drive_price_multiplier,
                          flight_speed_multiplier,
                          fuel_consumption_multiplier,
                          maximum_altitude_metres
                   FROM rule_vehicle_jump_jet_option"""
            ).fetchone()
            self.assertEqual(
                jump,
                (
                    "thrust", 1, Decimal("0.75"), Decimal("0.75"),
                    Decimal("0.25"), 5, 100,
                ),
            )
            offroad = connection.execute(
                """SELECT contact_drive_price_percent,
                          base_speed_multiplier,
                          normal_off_road_agility_penalty_negated,
                          rough_terrain_agility_dm,
                          off_road_speed_reduction_negated
                   FROM rule_vehicle_off_road_option"""
            ).fetchone()
            self.assertEqual(
                offroad,
                (50, Decimal("0.9"), 2, -2, True),
            )
            tilt = connection.execute(
                """SELECT thrust_drive_price_multiplier,
                          vertical_takeoff,hover_capable
                   FROM rule_vehicle_tilt_rotor_jet_option"""
            ).fetchone()
            self.assertEqual(tilt, (3, True, True))

    def test_option_provenance_and_errata_are_complete(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            counts = connection.execute(
                """SELECT
                    (SELECT count(*)
                       FROM rule_vehicle_configuration),
                    (SELECT count(*)
                       FROM rule_vehicle_configuration_option),
                    (SELECT count(*) FROM rule_vehicle_drive_option),
                    (SELECT count(*)
                       FROM src_record_provenance provenance
                       JOIN rule_rule rule USING (rule_id)
                      WHERE rule.rule_code LIKE
                            'vehicle.configuration.%'
                         OR rule.rule_code LIKE
                            'vehicle.configuration-option.%'
                         OR rule.rule_code LIKE
                            'vehicle.drive-option.%'),
                    (SELECT count(*)
                       FROM src_issue
                      WHERE issue_code LIKE
                            'vehicle.configuration.%'),
                    (SELECT count(*)
                       FROM src_issue_comparison_check comparison
                       JOIN src_issue issue USING (source_issue_id)
                      WHERE issue.issue_code LIKE
                            'vehicle.configuration.%')"""
            ).fetchone()
            self.assertEqual(counts, (2, 11, 10, 46, 2, 2))
            issues = connection.execute(
                """SELECT issue_code,review_priority,
                          engine_disposition
                   FROM src_issue
                   WHERE issue_code LIKE 'vehicle.configuration.%'
                   ORDER BY issue_code"""
            ).fetchall()
            self.assertEqual(
                issues,
                [
                    (
                        "vehicle.configuration.open-frame-copy-error",
                        "high", "preserve_rule",
                    ),
                    (
                        "vehicle.configuration.submersible-ballast-rounding",
                        "medium", "preserve_rule",
                    ),
                ],
            )


if __name__ == "__main__":
    unittest.main()
