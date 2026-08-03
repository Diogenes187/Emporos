import os,unittest
import psycopg
@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class DamageCompletionSchemaTests(unittest.TestCase):
 def test_completion_receipt_and_status_guard_exist(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   self.assertEqual(c.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='senc_mount_damage_application_receipt'").fetchone()[0],1)
   definition=c.execute("SELECT pg_get_functiondef('senc_reject_staged_damage_mutation()'::regprocedure)").fetchone()[0]
   self.assertIn("NEW.damage_status='applied'",definition)
if __name__=='__main__': unittest.main()
