import os
import unittest

import psycopg


@unittest.skipUnless(
    os.environ.get("BASE_CEPHEUS_DATABASE_URL"), "requires PostgreSQL"
)
class SpaceCombatLocationEffectTests(unittest.TestCase):
    def test_published_progressions_are_complete(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            self.assertEqual(
                connection.execute(
                    "SELECT count(*) FROM rule_space_combat_location_effect"
                ).fetchone()[0],
                52,
            )
            self.assertEqual(
                connection.execute(
                    """
                    SELECT effect_code,attack_dm,overflow_location_code
                    FROM rule_space_combat_location_effect effect
                    JOIN rule_rule rule ON rule.rule_id=effect.hit_location_rule_id
                    WHERE rule.rule_code='combat.space.hit-locations'
                      AND location_code='turret' AND hit_ordinal IN (1,4)
                    ORDER BY hit_ordinal
                    """
                ).fetchall(),
                [("tracking-damaged", -2, None), ("overflow", 0, "hull")],
            )
            self.assertEqual(
                connection.execute(
                    """
                    SELECT effect_code,thrust_factor
                    FROM rule_space_combat_location_effect effect
                    JOIN rule_rule rule ON rule.rule_id=effect.hit_location_rule_id
                    WHERE rule.rule_code='combat.space.hit-locations'
                      AND location_code='m-drive' AND hit_ordinal IN (2,3)
                    ORDER BY hit_ordinal
                    """
                ).fetchall(),
                [("halve-thrust", 0.500), ("disabled", 0.000)],
            )


if __name__ == "__main__":
    unittest.main()
