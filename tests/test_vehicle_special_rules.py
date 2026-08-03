from __future__ import annotations

import os
import unittest
from decimal import Decimal

import psycopg


@unittest.skipUnless(
    os.environ.get("BASE_CEPHEUS_DATABASE_URL"),
    "BASE_CEPHEUS_DATABASE_URL is not configured",
)
class VehicleSpecialRuleTests(unittest.TestCase):
    def test_lift_envelope_rules_are_numeric(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            formula = connection.execute(
                """SELECT stored_size_fraction,
                          structure_spaces_per_point,
                          non_explosive_hit_damage,
                          automatic_hit_damage_basis
                   FROM rule_vehicle_lift_envelope"""
            ).fetchone()
            self.assertEqual(
                formula,
                (
                    Decimal("0.01"), 60, 1,
                    "weapon-automatic-rating",
                ),
            )
            media = connection.execute(
                """SELECT lift_medium_code,duration_basis,
                          duration_hours_per_tech_level,
                          envelope_multiplier_class
                   FROM rule_vehicle_lift_medium
                   ORDER BY lift_medium_code"""
            ).fetchall()
            self.assertEqual(
                media,
                [
                    ("helium", "indefinite", None, "light-gas"),
                    ("hot-air", "tech-level-hours", 2, "hot-air"),
                    ("hydrogen", "indefinite", None, "light-gas"),
                ],
            )
            atmosphere = connection.execute(
                """SELECT atmosphere_density_code,
                          light_gas_size_multiplier,
                          hot_air_size_multiplier
                   FROM rule_vehicle_lift_envelope_atmosphere
                   ORDER BY display_order"""
            ).fetchall()
            self.assertEqual(
                atmosphere,
                [
                    ("very-thin", 100, 200),
                    ("thin", 25, 50),
                    ("standard", 10, 20),
                    ("dense", 5, 10),
                ],
            )

    def test_aircraft_environment_boundary_is_explicit(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            rows = connection.execute(
                """SELECT environment_code,
                          exact_match_maximum_code_difference,
                          operational_maximum_code_difference,
                          degraded_agility_dm,
                          degraded_in_all_environments,
                          minimum_atmosphere_code,
                          additional_base_price_multiplier
                   FROM rule_vehicle_aircraft_environment
                   ORDER BY environment_code"""
            ).fetchall()
            self.assertEqual(
                rows,
                [
                    ("extended", 0, 2, -1, True, 1, 1),
                    ("standard", 0, 1, -1, False, 1, 0),
                ],
            )

    def test_missile_impact_times_preserve_prohibited_ranges(
        self,
    ) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            rows = connection.execute(
                """SELECT target_range_code,attack_permitted,
                          turns_to_impact
                   FROM rule_vehicle_missile_impact_time
                   ORDER BY CASE target_range_code
                       WHEN 'personal' THEN 1
                       WHEN 'close' THEN 2
                       WHEN 'short' THEN 3
                       WHEN 'medium' THEN 4
                       WHEN 'long' THEN 5
                       WHEN 'very-long' THEN 6
                       WHEN 'distant' THEN 7
                       WHEN 'very-distant' THEN 8
                       WHEN 'extreme' THEN 9
                   END"""
            ).fetchall()
            self.assertEqual(
                rows,
                [
                    ("personal", False, None),
                    ("close", False, None),
                    ("short", True, 0),
                    ("medium", True, 0),
                    ("long", True, 0),
                    ("very-long", True, 0),
                    ("distant", True, 1),
                    ("very-distant", True, 4),
                    ("extreme", True, 8),
                ],
            )

    def test_missile_launch_skills_and_effects_are_typed(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            skills = connection.execute(
                """SELECT skill.rule_code
                   FROM rule_vehicle_missile_launch_skill launch
                   JOIN rule_rule skill
                     ON skill.rule_id=launch.skill_rule_id
                   ORDER BY skill.rule_code"""
            ).fetchall()
            self.assertEqual(
                skills,
                [("skill.bay-weapons",), ("skill.turret-weapons",)],
            )
            effects = connection.execute(
                """SELECT effect_minimum,effect_maximum,
                          skill_check_succeeded,
                          missile_target_number
                   FROM rule_vehicle_missile_launch_effect
                   ORDER BY display_order"""
            ).fetchall()
            self.assertEqual(
                effects,
                [
                    (None, -6, False, 11),
                    (-5, -1, False, 10),
                    (0, 0, True, 8),
                    (1, 5, True, 7),
                    (6, None, True, 6),
                ],
            )

    def test_animal_power_gaits_and_profiles_are_relational(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            formula = connection.execute(
                """SELECT strength_required_per_chassis_space,
                          rail_strength_divisor,
                          strength_deficit_per_reduction_step,
                          speed_and_range_reduction_per_step,
                          minimum_speed_fraction
                   FROM rule_vehicle_animal_power"""
            ).fetchone()
            self.assertEqual(
                formula,
                (1, 2, 5, Decimal("0.1"), 0),
            )
            gaits = connection.execute(
                """SELECT gait_code,speed_multiplier,
                          endurance_minutes_multiplier
                   FROM rule_vehicle_animal_gait
                   ORDER BY display_order"""
            ).fetchall()
            self.assertEqual(
                gaits,
                [
                    ("walk", 1, 30),
                    ("trot", 2, 15),
                    ("canter", 3, 2),
                    ("run", 4, 1),
                ],
            )
            profiles = connection.execute(
                """SELECT animal_code,strength,walk_speed_kph,
                          run_speed_kph,endurance
                   FROM rule_vehicle_draft_animal_profile
                   ORDER BY animal_code"""
            ).fetchall()
            self.assertEqual(len(profiles), 5)
            self.assertIn(("horse", 10, 7, 28, 12), profiles)
            self.assertIn(("ox", 18, 5, 20, 18), profiles)

    def test_wind_and_off_road_movement_are_typed(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            wind = connection.execute(
                """SELECT vehicle_medium_code,
                          under_ten_tons_speed_fraction,
                          ten_tons_or_more_speed_fraction
                   FROM rule_vehicle_wind_sailing_speed
                   ORDER BY vehicle_medium_code"""
            ).fetchall()
            self.assertEqual(
                wind,
                [
                    ("air", Decimal("0.35"), Decimal("0.4")),
                    ("ground", Decimal("0.2"), Decimal("0.15")),
                    ("water", Decimal("0.2"), Decimal("0.3")),
                ],
            )
            off_road = connection.execute(
                """SELECT off_road_capable,
                          normal_off_road_agility_dm,
                          normal_off_road_speed_fraction,
                          rough_terrain_permitted,
                          rough_terrain_agility_dm
                   FROM rule_vehicle_off_road_movement
                   ORDER BY off_road_capable"""
            ).fetchall()
            self.assertEqual(
                off_road,
                [
                    (False, -2, Decimal("0.25"), False, None),
                    (True, 0, 1, True, -2),
                ],
            )

    def test_alien_design_assumption_remains_referee_extensible(
        self,
    ) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            row = connection.execute(
                """SELECT assumes_humanlike_physiology,
                          accommodation_exceptions_allowed,
                          referee_is_final_arbiter
                   FROM rule_vehicle_alien_design_assumption"""
            ).fetchone()
            self.assertEqual(row, (True, True, True))

    def test_provenance_and_aircraft_issue_are_complete(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            counts = connection.execute(
                """SELECT
                    (SELECT count(*)
                       FROM src_record_provenance provenance
                       JOIN rule_rule rule USING (rule_id)
                      WHERE rule.rule_code LIKE
                            'vehicle.special.%'),
                    (SELECT count(*)
                       FROM src_issue_locator locator
                       JOIN src_issue issue USING (source_issue_id)
                      WHERE issue.issue_code=
                            'vehicle.aircraft.environment-tolerance-wording'),
                    (SELECT count(*)
                       FROM src_issue_comparison_check comparison
                       JOIN src_issue issue USING (source_issue_id)
                      WHERE issue.issue_code=
                            'vehicle.aircraft.environment-tolerance-wording')"""
            ).fetchone()
            self.assertEqual(counts, (18, 2, 1))


if __name__ == "__main__":
    unittest.main()
