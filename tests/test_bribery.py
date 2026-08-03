import os,unittest,uuid
import psycopg
from engine.bribery import attempt_bribery_command,resolve_bribery_consequence_command
class R:
 def __init__(self,v):self.v=iter(v)
 def randint(self,a,b):return next(self.v)
class BriberyTests(unittest.TestCase):
 def actor(self,c):
  camp=c.execute("INSERT INTO camp_campaign(name) VALUES(%s) RETURNING campaign_id",(str(uuid.uuid4()),)).fetchone()[0];aid,pub=c.execute("INSERT INTO actor_actor(campaign_id,name,controller_reference) VALUES(%s,'Fixer','p') RETURNING actor_id,public_id",(camp,)).fetchone();c.execute("""INSERT INTO actor_characteristic(actor_id,characteristic_rule_id,maximum_value,current_value) SELECT %s,rule_id,9,9 FROM rule_rule WHERE rule_code IN('characteristic.social-standing','characteristic.education')""",(aid,));c.execute("""INSERT INTO actor_skill SELECT %s,rule_id,0 FROM rule_rule WHERE rule_code='skill.bribery'""",(aid,));return str(pub)
 def test_minimum_overpayment_retry_and_charges(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    a=self.actor(c);first=attempt_bribery_command(c,initiator_reference='p',idempotency_key='b1',actor_public_id=a,target_reference='official',incident_reference='cargo',offense_code='minor',law_level=8,characteristic_rule_code='characteristic.education',offer_credits=100,random_source=R((4,)))
    self.assertTrue(first.automatic_failure);self.assertEqual(first.minimum_bribe_credits,200)
    second=attempt_bribery_command(c,initiator_reference='p',idempotency_key='b2',actor_public_id=a,target_reference='official',incident_reference='cargo',offense_code='minor',law_level=8,characteristic_rule_code='characteristic.education',offer_credits=200,random_source=R((1,1)))
    self.assertFalse(second.accepted);self.assertEqual(second.status,'pending_social_check')
    charged=resolve_bribery_consequence_command(c,initiator_reference='p',idempotency_key='bc',actor_public_id=a,target_reference='official',incident_reference='cargo',random_source=R((1,1)));self.assertTrue(charged)
 def test_example_cr200_and_overpayment_modifier(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    a=self.actor(c);r=attempt_bribery_command(c,initiator_reference='p',idempotency_key='ex',actor_public_id=a,target_reference='o',incident_reference='minor-smuggling',offense_code='minor',law_level=2,characteristic_rule_code='characteristic.education',offer_credits=400,random_source=R((4,6,6)))
    self.assertEqual(r.minimum_bribe_credits,200);self.assertEqual(r.offer_modifier,1);self.assertTrue(r.accepted)
