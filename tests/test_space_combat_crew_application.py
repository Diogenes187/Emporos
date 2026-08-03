import os,unittest
import psycopg
@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class CrewApplicationSchemaTests(unittest.TestCase):
 def test_damage_origin_and_radiation_state_are_relational(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   self.assertEqual(c.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN('actor_radiation_state','health_radiation_exposure','senc_crew_damage_application_receipt')").fetchone()[0],3)
   definition=c.execute("SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid='health_damage_instance'::regclass AND conname='health_damage_exactly_one_source_check'").fetchone()[0]
   self.assertIn('crew_damage_location_hit_receipt_id',definition)
if __name__=='__main__': unittest.main()
