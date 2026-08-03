import os
import unittest

import psycopg


@unittest.skipUnless(os.environ.get("BASE_CEPHEUS_DATABASE_URL"), "requires PostgreSQL")
class SpaceCombatMDriveDamageTests(unittest.TestCase):
    def test_adjudication_and_immutable_receipt_exist(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as c:
            self.assertEqual(
                c.execute(
                    "SELECT count(*) FROM rule_interpretation WHERE decision_register_entry='CE-SC-010'"
                ).fetchone()[0],
                1,
            )
            definition = c.execute(
                "SELECT pg_get_functiondef('senc_apply_mdrive_thrust_damage()'::regprocedure)"
            ).fetchone()[0]
            self.assertIn("floor(vessel_row.thrust_current::numeric/2)", definition)
            self.assertIn("speed_current", definition)
            triggers = c.execute(
                """SELECT count(DISTINCT trigger_name) FROM information_schema.triggers
                   WHERE event_object_table='senc_mdrive_thrust_damage_receipt'
                     AND action_timing='BEFORE'"""
            ).fetchone()[0]
            self.assertEqual(triggers, 1)


if __name__ == "__main__":
    unittest.main()
