import os
import unittest

import psycopg


@unittest.skipUnless(os.environ.get("BASE_CEPHEUS_DATABASE_URL"), "requires PostgreSQL")
class SpaceCombatCrewDamageBandTests(unittest.TestCase):
    def test_all_ten_published_outcomes_are_normalized(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            self.assertEqual(connection.execute(
                "SELECT count(*) FROM rule_space_combat_crew_damage_band"
            ).fetchone()[0],10)
            self.assertEqual(connection.execute(
                """SELECT target_scope,damage_dice_count,radiation_multiplier_rads
                   FROM rule_space_combat_crew_damage_band
                   WHERE damage_kind='radiation' AND roll_range @> 9"""
            ).fetchone(),('one-random',4,10))
            self.assertEqual(connection.execute(
                """SELECT target_scope,damage_dice_count
                   FROM rule_space_combat_crew_damage_band
                   WHERE damage_kind='normal' AND roll_range @> 12"""
            ).fetchone(),('all',4))


if __name__ == "__main__": unittest.main()
