import os
import unittest

import psycopg


DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class PsionicAssaultMechanicsTests(unittest.TestCase):
    def test_activation_and_damage_mechanics_are_complete(self):
        with psycopg.connect(DSN) as connection:
            power = connection.execute(
                """SELECT difficulty.rule_code,power.timing_dice_count,
                          power.timing_die_sides,power.timing_unit,
                          power.base_cost,power.adds_range_cost,
                          power.mechanics_complete
                   FROM psi_power power
                   JOIN rule_rule difficulty
                     ON difficulty.rule_id=power.difficulty_rule_id
                   WHERE power.power_code='assault'"""
            ).fetchone()
            self.assertEqual(power, (
                "difficulty.formidable", 1, 6, "seconds", 8, True, True,
            ))
            mechanic = connection.execute(
                """SELECT damage_dice_count,damage_die_sides,
                          adds_activation_effect_to_damage,
                          damage_psionic_strength_first,
                          damage_intelligence_second,
                          damage_endurance_third,
                          intelligence_points_per_day,
                          shielded_target_uses_opposed_telepathy,
                          attacker_win_damages_shielded_target
                   FROM rule_psi_assault"""
            ).fetchone()
            self.assertEqual(
                mechanic, (2, 6, True, True, True, True, 1, True, True)
            )


if __name__ == "__main__":
    unittest.main()
