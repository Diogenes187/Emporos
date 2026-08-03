import os,unittest,psycopg
@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class OffworldLawTests(unittest.TestCase):
 def test_law_encounters_and_sentencing_tables(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   self.assertEqual(c.execute('SELECT count(*),min(encounter_dm),max(encounter_dm) FROM rule_law_encounter_situation').fetchone(),(8,-4,0));self.assertEqual(c.execute('SELECT count(*) FROM rule_sentencing_crime').fetchone()[0],6);self.assertEqual(c.execute('SELECT count(*) FROM rule_sentencing_band').fetchone()[0],9);self.assertEqual(c.execute('SELECT count(*) FROM rule_sentencing_consequence').fetchone()[0],15);self.assertEqual(c.execute("SELECT count(DISTINCT work.work_code) FROM src_record_provenance provenance JOIN rule_rule rule USING(rule_id) JOIN src_locator locator USING(source_locator_id) JOIN src_work work ON work.source_work_id=locator.source_work_id WHERE rule.rule_code='world.law-enforcement'").fetchone()[0],2)
if __name__=='__main__':unittest.main()
