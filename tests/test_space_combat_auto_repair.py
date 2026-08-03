import os,unittest
import psycopg
@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class AutoRepairTests(unittest.TestCase):
 def test_ce_sc_011_and_allocation_are_relational(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   self.assertEqual(c.execute("SELECT count(*) FROM rule_interpretation WHERE decision_register_entry='CE-SC-011'").fetchone()[0],1)
   self.assertEqual(c.execute("SELECT maximum_checks_per_round,standard_check_modifier FROM rule_space_combat_auto_repair").fetchone(),(2,1))
   definition=c.execute("SELECT pg_get_functiondef('senc_validate_repair_drone_allocation()'::regprocedure)").fetchone()[0]
   self.assertIn("hangar_option_code='repair-drones'",definition); self.assertIn("software_code='auto-repair'",definition)
   self.assertEqual(c.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN('senc_auto_repair_attempt','senc_auto_repair_temporary_state','senc_auto_repair_expiration_receipt')").fetchone()[0],3)
   resolution=c.execute("SELECT pg_get_functiondef('senc_apply_auto_repair_attempt()'::regprocedure)").fetchone()[0]
   self.assertIn("NEW.check_order>allocation.autonomous_check_capacity",resolution)
   self.assertIn("difficulty.is_default",resolution)
   expiration=c.execute("SELECT pg_get_functiondef('senc_expire_battlefield_repairs()'::regprocedure)").fetchone()[0]
   self.assertIn("senc_auto_repair_temporary_state",expiration); self.assertIn("senc_auto_repair_expiration_receipt",expiration)
if __name__=='__main__': unittest.main()
