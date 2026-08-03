import os,unittest,uuid
import psycopg
from engine.computer import perform_computer_basic_operation_command
@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class ComputerBasicOperationTests(unittest.TestCase):
 def actor(self,c,trained=True):
  camp=c.execute("INSERT INTO camp_campaign(name,owner_reference) VALUES(%s,'player') RETURNING campaign_id",(str(uuid.uuid4()),)).fetchone()[0];aid,pub=c.execute("INSERT INTO actor_actor(campaign_id,name,controller_reference) VALUES(%s,'Operator','player') RETURNING actor_id,public_id",(camp,)).fetchone()
  if trained:c.execute("INSERT INTO actor_skill SELECT %s,rule_id,0 FROM rule_rule WHERE rule_code='skill.computer'",(aid,))
  return str(pub)
 def test_computer_zero_performs_published_operation_without_random_draw(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    actor=self.actor(c);r=perform_computer_basic_operation_command(c,initiator_reference='player',idempotency_key='public-search',actor_public_id=actor,operation_code='public-information-search',target_reference='Regina port directory');self.assertTrue(r.performed_without_check);self.assertEqual(r.computer_skill_level,0)
    replay=perform_computer_basic_operation_command(c,initiator_reference='player',idempotency_key='public-search',actor_public_id=actor,operation_code='data-retrieval',target_reference='changed');self.assertTrue(replay.replayed);self.assertEqual(replay.operation_code,'public-information-search')
    draws=c.execute("SELECT count(*) FROM cmd_random_draw d JOIN cmd_command x USING(command_id) WHERE x.public_id=%s",(r.command_public_id,)).fetchone()[0];self.assertEqual(draws,0)
    with self.assertRaises(psycopg.Error):
     with c.transaction():c.execute("UPDATE cmd_computer_basic_operation_receipt SET computer_skill_level=1 WHERE command_id=(SELECT command_id FROM cmd_command WHERE public_id=%s)",(r.command_public_id,))
 def test_untrained_actor_cannot_claim_automatic_operation(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    actor=self.actor(c,False)
    with self.assertRaisesRegex(ValueError,'Computer-0'):
     perform_computer_basic_operation_command(c,initiator_reference='player',idempotency_key='no-training',actor_public_id=actor,operation_code='datanet-login',target_reference='local datanet')
