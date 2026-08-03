import os,unittest
import psycopg
@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class CrewTargetSchemaTests(unittest.TestCase):
 def test_relational_target_and_consequence_tables(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   names={r[0] for r in c.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name LIKE 'senc_crew_damage_%'")}
   self.assertTrue({'senc_crew_damage_population','senc_crew_damage_population_receipt','senc_crew_damage_target','senc_crew_damage_target_receipt','senc_crew_damage_consequence_die','senc_crew_damage_consequence_receipt'}<=names)
if __name__=='__main__': unittest.main()
