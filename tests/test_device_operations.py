import os,unittest,uuid
import psycopg
from engine.devices import resolve_device_operation_command
class R:
 def randint(self,a,b):return 4
@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class DeviceOperationTests(unittest.TestCase):
 def test_operation_selects_published_skill_and_replays(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    camp=c.execute("INSERT INTO camp_campaign(name,owner_reference) VALUES(%s,'p') RETURNING campaign_id",(str(uuid.uuid4()),)).fetchone()[0];aid,apub=c.execute("INSERT INTO actor_actor(campaign_id,name,controller_reference) VALUES(%s,'Tech','p') RETURNING actor_id,public_id",(camp,)).fetchone();c.execute("INSERT INTO actor_characteristic(actor_id,characteristic_rule_id,maximum_value,current_value) SELECT %s,rule_id,7,7 FROM rule_rule WHERE rule_code='characteristic.education'",(aid,));c.execute("INSERT INTO actor_skill SELECT %s,rule_id,1 FROM rule_rule WHERE rule_code='skill.electronics'",(aid,))
    result=resolve_device_operation_command(c,initiator_reference='p',idempotency_key='alarm',actor_public_id=str(apub),operation_code='disarm-electronic-alarm',device_reference='vault alarm',characteristic_rule_code='characteristic.education',difficulty_rule_code='difficulty.average',random_source=R());self.assertEqual(result.skill_rule_code,'skill.electronics');self.assertEqual(result.check_total,9);self.assertTrue(result.succeeded)
    replay=resolve_device_operation_command(c,initiator_reference='p',idempotency_key='alarm',actor_public_id=str(apub),operation_code='assemble-bomb',device_reference='changed',characteristic_rule_code='characteristic.education',difficulty_rule_code='difficulty.average',random_source=R());self.assertTrue(replay.replayed);self.assertEqual(replay.operation_code,'disarm-electronic-alarm')
