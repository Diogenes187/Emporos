import os,unittest,uuid
import psycopg
from engine.survival import resolve_survival_task_command
class R:
 def randint(self,a,b):return 4
@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class SurvivalTests(unittest.TestCase):
 def test_availability_gate_and_task_receipts(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    camp=c.execute("INSERT INTO camp_campaign(name,owner_reference) VALUES(%s,'p') RETURNING campaign_id",(str(uuid.uuid4()),)).fetchone()[0];aid,apub=c.execute("INSERT INTO actor_actor(campaign_id,name,controller_reference) VALUES(%s,'Scout','p') RETURNING actor_id,public_id",(camp,)).fetchone();c.execute("INSERT INTO actor_characteristic(actor_id,characteristic_rule_id,maximum_value,current_value) SELECT %s,rule_id,7,7 FROM rule_rule WHERE rule_code='characteristic.endurance'",(aid,));c.execute("INSERT INTO actor_skill SELECT %s,rule_id,1 FROM rule_rule WHERE rule_code='skill.survival'",(aid,))
    absent=resolve_survival_task_command(c,initiator_reference='p',idempotency_key='water-none',actor_public_id=str(apub),operation_code='locate-fresh-water',objective_reference='desert water',characteristic_rule_code='characteristic.endurance',difficulty_rule_code='difficulty.average',opportunity_available=False,random_source=R());self.assertTrue(absent.automatic_failure);self.assertIsNone(absent.check_total)
    shelter=resolve_survival_task_command(c,initiator_reference='p',idempotency_key='shelter',actor_public_id=str(apub),operation_code='find-shelter',objective_reference='storm shelter',characteristic_rule_code='characteristic.endurance',difficulty_rule_code='difficulty.average',random_source=R());self.assertTrue(shelter.succeeded);self.assertEqual(shelter.check_total,9)
    replay=resolve_survival_task_command(c,initiator_reference='p',idempotency_key='shelter',actor_public_id=str(apub),operation_code='hunt-animals',objective_reference='changed',characteristic_rule_code='characteristic.endurance',difficulty_rule_code='difficulty.average',random_source=R());self.assertTrue(replay.replayed);self.assertEqual(replay.operation_code,'find-shelter')
