import os
import unittest

import psycopg


@unittest.skipUnless(
    os.environ.get("BASE_CEPHEUS_DATABASE_URL"), "requires PostgreSQL"
)
class SpaceCombatStorageDamageTests(unittest.TestCase):
    def test_storage_damage_is_relational_and_campaign_safe(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as c:
            names = {
                row[0]
                for row in c.execute(
                    """SELECT table_name FROM information_schema.tables
                       WHERE table_schema='public' AND table_name IN(
                         'ship_cargo_lot','senc_ship_fuel_leak_state',
                         'senc_storage_damage_attempt','senc_storage_damage_die',
                         'senc_storage_damage_final_receipt',
                         'senc_storage_damage_allocation_receipt')"""
                )
            }
            self.assertEqual(len(names), 6)
            definition = c.execute(
                "SELECT pg_get_functiondef('senc_apply_storage_damage()'::regprocedure)"
            ).fetchone()[0]
            self.assertIn("current_quantity_tons*expected_loss", definition)
            self.assertIn("refined_fuel", definition)
            self.assertIn("unrefined_fuel", definition)
            timing = c.execute(
                """SELECT action_timing FROM information_schema.triggers
                   WHERE event_object_table='senc_storage_damage_final_receipt'
                     AND trigger_name='senc_storage_damage_final_apply'"""
            ).fetchone()[0]
            self.assertEqual(timing, "AFTER")

    def test_ce_sc_009_is_recorded(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as c:
            self.assertEqual(
                c.execute(
                    """SELECT count(*) FROM rule_interpretation
                       WHERE decision_register_entry='CE-SC-009'"""
                ).fetchone()[0],
                1,
            )


if __name__ == "__main__":
    unittest.main()
