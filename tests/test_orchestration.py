import os,unittest,uuid
import psycopg
from engine.orchestration import GameplayOrchestrator,available_tools
class R:
 def randint(self,a,b):return 4
class OrchestrationContractTests(unittest.TestCase):
 def test_registry_is_explicit_and_host_arguments_are_hidden(self):
  specs=available_tools();self.assertEqual(len(specs),13);self.assertEqual(len({s.name for s in specs}),13);self.assertIn('start_spacecraft_journey_leg',{s.name for s in specs});self.assertTrue(all('initiator_reference' not in s.required_arguments+s.optional_arguments for s in specs))
@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class OrchestrationDatabaseTests(unittest.TestCase):
 def test_dispatch_preserves_command_idempotency_and_rejects_injection(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    camp=c.execute("INSERT INTO camp_campaign(name,owner_reference) VALUES(%s,'p') RETURNING campaign_id",(str(uuid.uuid4()),)).fetchone()[0];aid,apub=c.execute("INSERT INTO actor_actor(campaign_id,name,controller_reference) VALUES(%s,'Scout','p') RETURNING actor_id,public_id",(camp,)).fetchone();char=c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='characteristic.intelligence'").fetchone()[0];skill=c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='skill.recon'").fetchone()[0];c.execute("INSERT INTO actor_characteristic VALUES(%s,%s,7,7) ON CONFLICT(actor_id,characteristic_rule_id) DO UPDATE SET maximum_value=7,current_value=7",(aid,char));c.execute("INSERT INTO actor_skill VALUES(%s,%s,1) ON CONFLICT(actor_id,skill_rule_id) DO UPDATE SET skill_level=1",(aid,skill));o=GameplayOrchestrator(c,authority_reference='p',random_source=R());args={'actor_public_id':str(apub),'operation_code':'spot-threat','subject_reference':'hangar','characteristic_rule_code':'characteristic.intelligence','difficulty_rule_code':'difficulty.average'}
    first=o.invoke('resolve_recon',idempotency_key='scan',arguments=args);second=o.invoke('resolve_recon',idempotency_key='scan',arguments=args);self.assertEqual(first.command_public_id,second.command_public_id);self.assertTrue(second.replayed)
    with self.assertRaisesRegex(TypeError,'host-controlled'):o.invoke('resolve_recon',idempotency_key='bad',arguments={**args,'initiator_reference':'attacker'})
    with self.assertRaises(KeyError):o.invoke('arbitrary_python',idempotency_key='bad2',arguments={})
