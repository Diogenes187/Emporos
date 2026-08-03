import os
import unittest

import psycopg


@unittest.skipUnless(os.environ.get("BASE_CEPHEUS_DATABASE_URL"), "requires PostgreSQL")
class SpaceCombatCrewDamageRollTests(unittest.TestCase):
    def test_runtime_is_relational_and_immutable(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            names={row[0] for row in connection.execute(
                """SELECT table_name FROM information_schema.tables
                   WHERE table_schema='public' AND table_name LIKE 'senc_crew_damage_%'"""
            )}
            self.assertTrue({
                'senc_crew_damage_attempt','senc_crew_damage_outcome_die',
                'senc_crew_damage_outcome_receipt'
            }.issubset(names))
            self.assertEqual(connection.execute(
                """SELECT count(*) FROM information_schema.triggers
                   WHERE event_object_table IN ('senc_crew_damage_attempt',
                     'senc_crew_damage_outcome_die','senc_crew_damage_outcome_receipt')
                     AND action_timing='BEFORE'"""
            ).fetchone()[0],9)


if __name__ == "__main__": unittest.main()
