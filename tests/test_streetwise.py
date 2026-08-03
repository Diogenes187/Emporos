import os,unittest,uuid
import psycopg
from engine.streetwise import resolve_streetwise_command
class R:
 def randint(self,a,b):return 4
@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class StreetwiseTests(unittest.TestCase):
 def test_streetwise_task_receipt_and_replay(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    camp=c.execute("INSERT INTO camp_campaign(name,owner_reference) VALUES(%s,'p') RETURNING campaign_id",(str(uuid.uuid4()),)).fetchone()[0];aid,apub=c.execute("INSERT INTO actor_actor(campaign_id,name,controller_reference) VALUES(%s,'Operator','p') RETURNING actor_id,public_id",(camp,)).fetchone();c.execute("INSERT INTO actor_characteristic(actor_id,characteristic_rule_id,maximum_value,current_value) SELECT %s,rule_id,7,7 FROM rule_rule WHERE rule_code='characteristic.social-standing'",(aid,));c.execute("INSERT INTO actor_skill SELECT %s,rule_id,1 FROM rule_rule WHERE rule_code='skill.streetwise'",(aid,))
    result=resolve_streetwise_command(c,initiator_reference='p',idempotency_key='lead',actor_public_id=str(apub),operation_code='find-information',objective_reference='dockside smuggling routes',characteristic_rule_code='characteristic.social-standing',difficulty_rule_code='difficulty.average',random_source=R());self.assertTrue(result.succeeded);self.assertEqual(result.check_total,9)
    replay=resolve_streetwise_command(c,initiator_reference='p',idempotency_key='lead',actor_public_id=str(apub),operation_code='locate-fringe-contact',objective_reference='different',characteristic_rule_code='characteristic.social-standing',difficulty_rule_code='difficulty.average',random_source=R());self.assertTrue(replay.replayed);self.assertEqual(replay.operation_code,'find-information')
    with self.assertRaises(psycopg.Error):
     with c.transaction():c.execute("DELETE FROM cmd_streetwise_receipt WHERE command_id=(SELECT command_id FROM cmd_command WHERE public_id=%s)",(result.command_public_id,))
