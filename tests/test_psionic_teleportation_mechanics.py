import os
import unittest

import psycopg


DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class PsionicTeleportationMechanicsTests(unittest.TestCase):
    def test_load_destination_and_conservation_rules_are_normalized(self):
        with psycopg.connect(DSN) as connection:
            profiles = connection.execute(
                """SELECT profile.load_kind,difficulty.rule_code,
                          power.base_cost,profile.includes_clothing_or_possessions
                   FROM rule_psi_teleportation_power profile
                   JOIN psi_power power
                     ON power.power_rule_id=profile.power_rule_id
                   JOIN rule_rule difficulty
                     ON difficulty.rule_id=power.difficulty_rule_id
                   ORDER BY profile.display_order"""
            ).fetchall()
            self.assertEqual(profiles, [
                ("unclothed", "difficulty.average", 0, False),
                ("light", "difficulty.difficult", 2, True),
                ("moderate", "difficulty.very-difficult", 3, True),
                ("heavy", "difficulty.very-difficult", 4, True),
            ])
            system = connection.execute(
                """SELECT range_rule.rule_code,
                          maximum_safe_single_altitude_metres,
                          maximum_safe_hourly_altitude_metres,
                          temperature_change_celsius_per_km,
                          fast_vehicle_uses_ramming_damage,
                          recorded_image_prohibited
                   FROM rule_psi_teleportation_system system
                   JOIN rule_rule range_rule
                     ON range_rule.rule_id=
                        system.planetary_maximum_range_rule_id"""
            ).fetchone()
            self.assertEqual(
                system,
                ("psionics.range.very-distant", 400, 600, 2.5, True, True),
            )
            disorientation = connection.execute(
                """SELECT duration_dice_count,duration_die_sides,
                          duration_multiplier_seconds
                   FROM rule_psi_teleportation_disorientation"""
            ).fetchone()
            self.assertEqual(disorientation, (2, 6, 10))


if __name__ == "__main__":
    unittest.main()
