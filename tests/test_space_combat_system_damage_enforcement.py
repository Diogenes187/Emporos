import os
import unittest

import psycopg


@unittest.skipUnless(os.environ.get("BASE_CEPHEUS_DATABASE_URL"), "requires PostgreSQL")
class SpaceCombatSystemDamageEnforcementTests(unittest.TestCase):
    def test_action_guard_and_terminal_effects_exist(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as c:
            guard = c.execute(
                "SELECT pg_get_functiondef('senc_guard_damaged_system_action()'::regprocedure)"
            ).fetchone()[0]
            self.assertIn("Disabled or destroyed Bridge", guard)
            self.assertIn("Disabled or destroyed Sensors", guard)
            terminal = c.execute(
                "SELECT pg_get_functiondef('senc_apply_terminal_system_damage()'::regprocedure)"
            ).fetchone()[0]
            self.assertIn("vessel_status='disabled'", terminal)

    def test_system_damage_is_part_of_checks(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as c:
            columns = {
                row[0]
                for row in c.execute(
                    """SELECT table_name||'.'||column_name
                       FROM information_schema.columns
                       WHERE (table_name,column_name) IN (
                         ('senc_sensor_targeting_receipt','sensor_damage_modifier'),
                         ('senc_mount_weapon_attack_check','system_damage_modifier'))"""
                )
            }
            self.assertEqual(len(columns), 2)
            attack = c.execute(
                "SELECT pg_get_functiondef('senc_validate_mount_weapon_attack_check()'::regprocedure)"
            ).fetchone()[0]
            self.assertIn("mount_damage+bridge_damage", attack)
            declaration = c.execute(
                "SELECT pg_get_functiondef('senc_validate_mount_attack_declaration()'::regprocedure)"
            ).fetchone()[0]
            self.assertIn("actual_range<>'adjacent'", declaration)


if __name__ == "__main__":
    unittest.main()
