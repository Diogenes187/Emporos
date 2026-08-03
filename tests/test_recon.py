import os,unittest,uuid
import psycopg
from engine.recon import resolve_recon_command
class R:
 def randint(self,a,b):return 4
@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class ReconTests(unittest.TestCase):
 def test_recon_is_campaign_safe_task_backed_and_replayable(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    camp=c.execute("INSERT INTO camp_campaign(name,owner_reference) VALUES(%s,'p') RETURNING campaign_id",(str(uuid.uuid4()),)).fetchone()[0];aid,apub=c.execute("INSERT INTO actor_actor(campaign_id,name,controller_reference) VALUES(%s,'Scout','p') RETURNING actor_id,public_id",(camp,)).fetchone();target=c.execute("INSERT INTO actor_actor(campaign_id,name,controller_reference) VALUES(%s,'Stranger','x') RETURNING public_id",(camp,)).fetchone()[0];c.execute("INSERT INTO actor_characteristic(actor_id,characteristic_rule_id,maximum_value,current_value) SELECT %s,rule_id,7,7 FROM rule_rule WHERE rule_code='characteristic.intelligence'",(aid,));c.execute("INSERT INTO actor_skill SELECT %s,rule_id,1 FROM rule_rule WHERE rule_code='skill.recon'",(aid,))
    result=resolve_recon_command(c,initiator_reference='p',idempotency_key='spot',actor_public_id=str(apub),operation_code='spot-out-of-place-person',subject_reference='quiet passenger',characteristic_rule_code='characteristic.intelligence',difficulty_rule_code='difficulty.average',target_actor_public_id=str(target),random_source=R());self.assertTrue(result.succeeded);self.assertEqual(result.check_total,9)
    replay=resolve_recon_command(c,initiator_reference='p',idempotency_key='spot',actor_public_id=str(apub),operation_code='remain-unseen',subject_reference='different',characteristic_rule_code='characteristic.intelligence',difficulty_rule_code='difficulty.average',random_source=R());self.assertTrue(replay.replayed);self.assertEqual(replay.operation_code,'spot-out-of-place-person')
    with self.assertRaises(psycopg.Error):
     with c.transaction():c.execute("UPDATE cmd_recon_receipt SET succeeded=false WHERE command_id=(SELECT command_id FROM cmd_command WHERE public_id=%s)",(result.command_public_id,))
