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
class VehicleArmamentMountingTests(unittest.TestCase):
    def test_weapon_points_and_gun_port_are_typed(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            formula = connection.execute(
                """SELECT displacement_tons_per_weapon_point,
                          minimum_weapon_points,allocation_rounding
                   FROM rule_vehicle_weapon_point_formula
                   WHERE formula_code='standard'"""
            ).fetchone()
            self.assertEqual(formula, (5, 1, "floor"))

            gun_port = connection.execute(
                """SELECT unit_cost_minor,unit_spaces,
                          weapon_points_required,stabilized,
                          fire_control_supported,
                          personal_weapon_ranges_only,
                          grants_vehicle_armor,
                          adjacent_attack_ignores_vehicle_armor
                   FROM rule_vehicle_gun_port"""
            ).fetchone()
            self.assertEqual(
                gun_port,
                (250, 0, 0, False, False, True, True, True),
            )

    def test_gun_port_weapon_catalogue_preserves_source_values(
        self,
    ) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            counts = connection.execute(
                """SELECT count(*),
                          count(*) FILTER (
                              WHERE catalogue_link_status='linked'
                          ),
                          count(*) FILTER (
                              WHERE catalogue_link_status=
                                    'source-item-not-imported'
                          )
                   FROM rule_vehicle_gun_port_weapon"""
            ).fetchone()
            self.assertEqual(counts, (24, 16, 8))

            selected = connection.execute(
                """SELECT weapon_code,minimum_tech_level,
                          unit_cost_minor,unit_spaces,
                          single_shot_rate,burst_shot_rate,
                          automatic_fire_rate,attack_profile_code,
                          damage_dice_count,damage_die_sides,
                          special_damage_code,has_recoil,
                          illegal_at_law_level
                   FROM rule_vehicle_gun_port_weapon
                   WHERE weapon_code IN (
                       'fusion-gun-man-portable',
                       'gauss-rifle',
                       'grenade-launcher'
                   )
                   ORDER BY weapon_code"""
            ).fetchall()
            self.assertEqual(
                selected,
                [
                    (
                        "fusion-gun-man-portable", 14, 100000,
                        Decimal("0.14"), 1, 4, None, "rifle",
                        16, 6, None, True, 2,
                    ),
                    (
                        "gauss-rifle", 12, 1500, Decimal("0.04"),
                        1, 4, 10, "rifle", 4, 6, None, False, 6,
                    ),
                    (
                        "grenade-launcher", 7, 400,
                        Decimal("0.07"), 1, None, None, "shotgun",
                        None, None, "by-grenade", True, 3,
                    ),
                ],
            )

    def test_mounts_and_gun_shields_are_relational(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            mounts = connection.execute(
                """SELECT mount_code,minimum_tech_level,
                          unit_cost_minor,maximum_weapon_spaces,
                          stabilized,fixed_direction,removable
                   FROM rule_vehicle_weapon_mount
                   ORDER BY mount_code"""
            ).fetchall()
            self.assertEqual(len(mounts), 5)
            self.assertIn(
                (
                    "fixed", 1, 0, None, False, True, False,
                ),
                mounts,
            )
            self.assertIn(
                (
                    "ring-powered", 7, 2150, Decimal("3"),
                    True, False, True,
                ),
                mounts,
            )

            shield = connection.execute(
                """SELECT cost_per_armor_point_minor,
                          armor_tech_level_divisor,armor_rounding,
                          minimum_armor,facing_only,
                          count(shield_mount.*)
                   FROM rule_vehicle_gun_shield shield
                   JOIN rule_vehicle_gun_shield_mount shield_mount
                     USING (option_rule_id)
                   GROUP BY shield.option_rule_id"""
            ).fetchone()
            self.assertEqual(shield, (200, 2, "floor", 1, True, 4))

    def test_turret_formulae_are_numeric(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            turrets = connection.execute(
                """SELECT turret_code,base_spaces,
                          weapon_volume_multiplier,
                          price_per_base_space_minor,
                          operator_capacity,remotely_controlled,
                          weapon_points_per_spaces,
                          weapon_point_rounding
                   FROM rule_vehicle_turret
                   ORDER BY turret_code"""
            ).fetchall()
            self.assertEqual(
                turrets,
                [
                    (
                        "large", 3, 1, 16000, 1, False,
                        60, "ceiling",
                    ),
                    (
                        "small", Decimal("0.5"), 1, 8000, 0,
                        True, 60, "ceiling",
                    ),
                ],
            )
            coaxial = connection.execute(
                """SELECT shared_firing_arc,
                          additional_weapon_points_per_weapon_after_first
                   FROM rule_vehicle_coaxial_mount
                   WHERE formula_code='standard'"""
            ).fetchone()
            self.assertEqual(coaxial, (True, 1))
            pop_up = connection.execute(
                """SELECT total_space_multiplier,
                          additional_price_per_total_space_minor,
                          concealed_while_retracted
                   FROM rule_vehicle_pop_up_turret"""
            ).fetchone()
            self.assertEqual(pop_up, (2, 4000, True))

    def test_armament_options_have_typed_effects_and_eligibility(
        self,
    ) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            options = connection.execute(
                """SELECT option_code,minimum_tech_level,
                          fixed_cost_minor,unit_spaces,
                          weapon_price_multiplier,
                          rate_of_fire_multiplier,
                          range_band_steps,damage_dice_modifier,
                          attack_dm,target_motion_requirement
                   FROM rule_vehicle_armament_option
                   ORDER BY option_code"""
            ).fetchall()
            self.assertEqual(len(options), 5)
            self.assertIn(
                (
                    "heavy-turret-weapon", 3, None, None,
                    Decimal("1.5"), Decimal("0.5"), None, 1,
                    None, None,
                ),
                options,
            )
            self.assertIn(
                (
                    "missile-guidance-system", 5, 10000,
                    Decimal("6"), None, None, None, None, 1,
                    "moving",
                ),
                options,
            )
            family_count = connection.execute(
                """SELECT count(*)
                   FROM rule_vehicle_armament_option_weapon_family"""
            ).fetchone()[0]
            incompatibility_count = connection.execute(
                """SELECT count(*)
                   FROM rule_vehicle_armament_option_incompatibility"""
            ).fetchone()[0]
            scope_count = connection.execute(
                """SELECT count(*)
                   FROM rule_vehicle_armament_option_scope"""
            ).fetchone()[0]
            self.assertEqual(
                (family_count, scope_count, incompatibility_count),
                (5, 3, 1),
            )

    def test_provenance_and_erratum_are_complete(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            counts = connection.execute(
                """SELECT
                    (SELECT count(*)
                       FROM src_record_provenance provenance
                       JOIN rule_rule rule USING (rule_id)
                      WHERE rule.rule_code=
                            'vehicle.armament.gun-port'
                         OR rule.rule_code LIKE
                            'vehicle.gun-port-weapon.%'
                         OR rule.rule_code LIKE
                            'vehicle.weapon-mount.%'
                         OR rule.rule_code LIKE
                            'vehicle.weapon-mount-option.%'
                         OR rule.rule_code LIKE 'vehicle.turret.%'
                         OR rule.rule_code LIKE
                            'vehicle.turret-option.%'
                         OR rule.rule_code LIKE
                            'vehicle.armament-option.%'),
                    (SELECT count(*)
                       FROM src_issue_locator locator
                       JOIN src_issue issue USING (source_issue_id)
                      WHERE issue.issue_code=
                            'vehicle.armament.heavy-weapon-rof-rounding'),
                    (SELECT count(*)
                       FROM src_issue_comparison_check comparison
                       JOIN src_issue issue USING (source_issue_id)
                      WHERE issue.issue_code=
                            'vehicle.armament.heavy-weapon-rof-rounding')"""
            ).fetchone()
            self.assertEqual(counts, (78, 2, 1))

    def test_gun_port_damage_shape_constraint_is_enforced(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            with connection.transaction(force_rollback=True):
                with self.assertRaises(CheckViolation):
                    connection.execute(
                        """UPDATE rule_vehicle_gun_port_weapon
                           SET special_damage_code='also-dice'
                           WHERE weapon_code='gauss-rifle'"""
                    )


if __name__ == "__main__":
    unittest.main()
