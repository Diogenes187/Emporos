import os, unittest
import psycopg
@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class BattlefieldRepairTests(unittest.TestCase):
 def test_rules_and_runtime_are_relational(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   self.assertEqual(c.execute("SELECT array_agg(hits_repaired ORDER BY effect_min) FROM rule_space_combat_repair_effect_band").fetchone()[0],[1,2,3])
   self.assertEqual(c.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN('senc_system_battlefield_repair_receipt','senc_system_temporary_repair_state')").fetchone()[0],2)
   definition=c.execute("SELECT pg_get_functiondef('senc_apply_battlefield_system_repair()'::regprocedure)").fetchone()[0]
   self.assertIn("role.crew_role='damage_control'",definition); self.assertIn("skill.mechanics",definition)
   expiration=c.execute("SELECT pg_get_functiondef('senc_expire_battlefield_repairs()'::regprocedure)").fetchone()[0]
   self.assertIn("restoration_status='expired'",expiration); self.assertIn("least(3",expiration)
if __name__=='__main__': unittest.main()
