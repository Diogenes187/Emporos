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
class VehicleWeaponsOrdnanceTests(unittest.TestCase):
    def test_vehicle_weapon_range_matrix_is_relational(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            counts = connection.execute(
                """SELECT
                    (SELECT count(*)
                       FROM rule_vehicle_weapon_target_range),
                    (SELECT count(*)
                       FROM rule_vehicle_weapon_range_profile),
                    (SELECT count(*)
                       FROM rule_vehicle_weapon_range_difficulty)"""
            ).fetchone()
            self.assertEqual(counts, (10, 13, 73))

            selected = connection.execute(
                """SELECT matrix.range_profile_code,
                          matrix.target_range_code,
                          difficulty.rule_code
                   FROM rule_vehicle_weapon_range_difficulty matrix
                   JOIN rule_rule difficulty
                     ON difficulty.rule_id=matrix.difficulty_rule_id
                   WHERE (
                       matrix.range_profile_code,
                       matrix.target_range_code
                   ) IN (
                       ('rifle','distant'),
                       ('very-distant','very-distant'),
                       ('continental','continental')
                   )
                   ORDER BY matrix.range_profile_code"""
            ).fetchall()
            self.assertEqual(
                selected,
                [
                    (
                        "continental", "continental",
                        "difficulty.formidable",
                    ),
                    ("rifle", "distant", "difficulty.very-difficult"),
                    (
                        "very-distant", "very-distant",
                        "difficulty.formidable",
                    ),
                ],
            )

    def test_all_published_vehicle_weapons_are_typed(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            counts = connection.execute(
                """SELECT
                    (SELECT count(*)
                       FROM rule_vehicle_weapon_family),
                    (SELECT count(*)
                       FROM rule_vehicle_weapon_definition),
                    (SELECT count(*)
                       FROM rule_vehicle_weapon_definition
                      WHERE range_by_missile),
                    (SELECT count(*)
                       FROM rule_vehicle_weapon_definition
                      WHERE damage_by_missile)"""
            ).fetchone()
            self.assertEqual(counts, (19, 76, 1, 1))

            selected = connection.execute(
                """SELECT weapon_code,minimum_tech_level,
                          unit_cost_minor,unit_spaces,
                          single_shot_rate,burst_shot_rate,
                          automatic_fire_rate,range_profile_code,
                          damage_dice_count,blast_radius_metres,
                          blast_radius_squares,has_recoil,
                          illegal_at_law_level
                   FROM rule_vehicle_weapon_definition
                   WHERE weapon_code IN (
                       'artillery-gun-tl-17',
                       'gauss-cannon-tl-12',
                       'machine-gun-tl-5',
                       'missile-rack'
                   )
                   ORDER BY weapon_code"""
            ).fetchall()
            self.assertEqual(
                selected,
                [
                    (
                        "artillery-gun-tl-17", 17, 800000, 24,
                        1, 2, None, "extreme", 17, 60, 40,
                        False, 3,
                    ),
                    (
                        "gauss-cannon-tl-12", 12, 450000, 24,
                        1, 10, None, "distant", 11, 6, 4,
                        True, 3,
                    ),
                    (
                        "machine-gun-tl-5", 5, 6000, 3,
                        None, 20, None, "rifle", 4, None, None,
                        True, 3,
                    ),
                    (
                        "missile-rack", 6, 48000, 12,
                        1, 3, None, None, None, None, None,
                        True, 3,
                    ),
                ],
            )

    def test_special_weapon_effects_are_reusable(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            rules = connection.execute(
                """SELECT special_rule_code,
                          effect_equals_target_armor,
                          ignores_armor,
                          automatic_crew_radiation_hits,attack_dm
                   FROM rule_vehicle_weapon_special_rule
                   ORDER BY special_rule_code"""
            ).fetchall()
            self.assertEqual(
                rules,
                [
                    ("disintegrator", True, False, 0, 0),
                    ("meson", False, True, 1, 0),
                    ("pulse", False, False, 0, -2),
                ],
            )
            links = connection.execute(
                """SELECT count(*)
                   FROM rule_vehicle_weapon_family_special_rule"""
            ).fetchone()[0]
            self.assertEqual(links, 5)

    def test_ammunition_schedules_preserve_exact_units(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            rows = connection.execute(
                """SELECT weapon_family_code,price_basis,
                          price_per_space_minor,rounds_per_space
                   FROM rule_vehicle_weapon_ammunition
                   ORDER BY weapon_family_code"""
            ).fetchall()
            self.assertEqual(len(rows), 11)
            self.assertIn(
                ("gauss-cannon", "per-space", 25000, 18000),
                rows,
            )
            self.assertIn(
                ("mass-driver", "per-space", 9000, 2),
                rows,
            )
            self.assertIn(
                ("missile-rack", "by-missile", None, 1),
                rows,
            )

    def test_ordnance_bays_and_payloads_are_typed(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            bays = connection.execute(
                """SELECT bay_code,cost_per_capacity_space_minor,
                          single_ordnance_type_only,reloadable,
                          rate_of_fire_basis,
                          missile_launches_per_round,
                          torpedo_launches_per_round,
                          bomb_capacity_fraction_per_round
                   FROM rule_vehicle_ordnance_bay
                   ORDER BY bay_code"""
            ).fetchall()
            self.assertEqual(
                bays,
                [
                    (
                        "dedicated", 5000, True, True,
                        "ordnance-count", None, None, None,
                    ),
                    (
                        "general-purpose", 10000, False, True,
                        "one-missile-or-torpedo-or-half-bomb-capacity",
                        1, 1, Decimal("0.5"),
                    ),
                ],
            )
            formula = connection.execute(
                """SELECT bay_spaces_per_weapon_point,
                          minimum_weapon_points,allocation_rounding
                   FROM rule_vehicle_ordnance_bay_weapon_point_formula"""
            ).fetchone()
            self.assertEqual(formula, (60, 1, "ceiling"))

            count = connection.execute(
                "SELECT count(*) FROM rule_vehicle_ordnance_definition"
            ).fetchone()[0]
            self.assertEqual(count, 12)
            malformed = connection.execute(
                """SELECT range_profile_code,published_range_token,
                          range_status,damage_dice_count,
                          radiation_dice_count,radiation_die_sides,
                          radiation_multiplier,radiation_unit_status,
                          treated_as_aquatic_missile
                   FROM rule_vehicle_ordnance_definition
                   WHERE ordnance_code='torpedo-nuclear-heavy'"""
            ).fetchone()
            self.assertEqual(
                malformed,
                (
                    "very-distant", "ranged (very distant)",
                    "adjudicated", 28, 2, 6, 10,
                    "adjudicated-rads", True,
                ),
            )

    def test_missiles_preserve_smart_and_radiation_rules(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            count = connection.execute(
                "SELECT count(*) FROM rule_vehicle_missile"
            ).fetchone()[0]
            self.assertEqual(count, 10)
            selected = connection.execute(
                """SELECT missile_code,guidance_code,
                          range_profile_code,damage_dice_count,
                          radiation_hit_count,fixed_attack_target,
                          may_repeat_missed_attack,
                          radiation_rule_status
                   FROM rule_vehicle_missile
                   WHERE missile_code IN (
                       'antimatter-smart-ai-guided',
                       'nuclear-nas-guided'
                   )
                   ORDER BY missile_code"""
            ).fetchall()
            self.assertEqual(
                selected,
                [
                    (
                        "antimatter-smart-ai-guided",
                        "smart-ai-guided", "extreme", 20, 1,
                        8, True, "published",
                    ),
                    (
                        "nuclear-nas-guided", "nas-guided",
                        "very-long", 13, 1, None, False,
                        "adjudicated",
                    ),
                ],
            )

    def test_anti_missile_systems_are_mechanical(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            general = connection.execute(
                """SELECT base_target_number,additional_target_dm,
                          negates_missiles,negates_rockets,
                          negates_launched_grenades,
                          negates_mortar_rounds
                   FROM rule_vehicle_anti_missile_resolution"""
            ).fetchone()
            self.assertEqual(general, (8, -1, True, True, True, True))

            selected = connection.execute(
                """SELECT system_code,minimum_tech_level,
                          interception_dm,
                          laser_damage_reduction_dice,
                          unit_spaces,unit_cost_minor,
                          minimum_effective_range_code,
                          uses_before_reload,reload_cost_minor,
                          applies_to_all_supported_threats
                   FROM rule_vehicle_anti_missile_system
                   WHERE system_code IN (
                       'laser','prismatic-aerosols','vrf-gauss'
                   )
                   ORDER BY system_code"""
            ).fetchall()
            self.assertEqual(
                selected,
                [
                    (
                        "laser", 10, 1, None, 12, 250000,
                        "medium", None, None, True,
                    ),
                    (
                        "prismatic-aerosols", 9, 2, 2,
                        Decimal("1.5"), 4000, None, 6, 500, False,
                    ),
                    (
                        "vrf-gauss", 11, 0, None, 9, 200000,
                        "medium", 15, 20000, True,
                    ),
                ],
            )
            decoy_claims = connection.execute(
                """SELECT guidance_code,claim_role
                   FROM rule_vehicle_anti_missile_guidance_claim claim
                   JOIN rule_vehicle_anti_missile_system system
                     USING (system_rule_id)
                   WHERE system.system_code='decoys'
                   ORDER BY guidance_code"""
            ).fetchall()
            self.assertEqual(
                decoy_claims,
                [
                    ("radar-guided", "parenthetical-label"),
                    ("smart-ai-guided", "primary-label"),
                    ("smart-computer-guided", "primary-label"),
                ],
            )

    def test_provenance_and_source_findings_are_complete(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            counts = connection.execute(
                """SELECT
                    (SELECT count(*)
                       FROM src_record_provenance provenance
                       JOIN rule_rule rule USING (rule_id)
                      WHERE rule.rule_code LIKE 'vehicle.weapon.%'
                         OR rule.rule_code LIKE
                            'vehicle.weapon-special.%'
                         OR rule.rule_code LIKE 'vehicle.ordnance%'
                         OR rule.rule_code LIKE 'vehicle.missile.%'
                         OR rule.rule_code=
                            'vehicle.anti-missile.general'
                         OR rule.rule_code LIKE
                            'vehicle.anti-missile-system.%'),
                    (SELECT count(*)
                       FROM src_issue_locator locator
                       JOIN src_issue issue USING (source_issue_id)
                      WHERE issue.issue_code IN (
                          'vehicle.ordnance.heavy-nuclear-torpedo-row',
                          'vehicle.missile.nas-radiation-hit',
                          'vehicle.anti-missile.decoy-guidance-label'
                      )),
                    (SELECT count(*)
                       FROM src_issue_comparison_check comparison
                       JOIN src_issue issue USING (source_issue_id)
                      WHERE issue.issue_code IN (
                          'vehicle.ordnance.heavy-nuclear-torpedo-row',
                          'vehicle.missile.nas-radiation-hit',
                          'vehicle.anti-missile.decoy-guidance-label'
                      ))"""
            ).fetchone()
            self.assertEqual(counts, (226, 6, 3))

    def test_smart_missile_constraint_is_enforced(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            with connection.transaction(force_rollback=True):
                with self.assertRaises(CheckViolation):
                    connection.execute(
                        """UPDATE rule_vehicle_missile
                           SET fixed_attack_target=NULL
                           WHERE missile_code=
                             'antimatter-smart-ai-guided'"""
                    )


if __name__ == "__main__":
    unittest.main()
