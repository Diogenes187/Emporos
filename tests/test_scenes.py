import os,unittest,uuid
import psycopg
from engine.scenes import SceneFact,create_scene_snapshot_command
class SceneTests(unittest.TestCase):
 def test_templates_snapshot_required_slots_and_immutability(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   self.assertEqual(c.execute('SELECT count(*) FROM rule_scene_template').fetchone()[0],8);self.assertEqual(c.execute('SELECT count(*) FROM rule_scene_template_slot').fetchone()[0],32)
   _,pub=c.execute("INSERT INTO camp_campaign(name,owner_reference) VALUES(%s,'p') RETURNING campaign_id,public_id",(str(uuid.uuid4()),)).fetchone()
   result=create_scene_snapshot_command(c,initiator_reference='p',idempotency_key='port',campaign_public_id=str(pub),template_code='docking-customs',scene_reference='arrival-1',facts=(SceneFact('facility','Highport 3'),SceneFact('clearance','Provisional'),SceneFact('inspection','Cargo declaration review','law-level-7')))
   self.assertEqual(result.fact_count,3);self.assertTrue(create_scene_snapshot_command(c,initiator_reference='p',idempotency_key='port',campaign_public_id=str(pub),template_code='law-stop',scene_reference='changed',facts=(SceneFact('authority','x'),)).replayed)
   with self.assertRaises(psycopg.Error):c.execute("UPDATE camp_scene_fact SET fact_value='changed' WHERE scene_snapshot_id=(SELECT scene_snapshot_id FROM camp_scene_snapshot WHERE public_id=%s) AND slot_code='clearance'",(result.scene_public_id,))
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   _,pub=c.execute("INSERT INTO camp_campaign(name,owner_reference) VALUES(%s,'p') RETURNING campaign_id,public_id",(str(uuid.uuid4()),)).fetchone()
   with self.assertRaises(psycopg.Error):create_scene_snapshot_command(c,initiator_reference='p',idempotency_key='bad',campaign_public_id=str(pub),template_code='law-stop',scene_reference='bad',facts=(SceneFact('authority','Patrol'),))
if __name__=='__main__':unittest.main()
