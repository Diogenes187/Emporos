import os,unittest,uuid
import psycopg
from engine.regulatory import resolve_regulatory_task_command
class R:
 def randint(self,a,b):return 4
@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class RegulatoryTests(unittest.TestCase):
 def test_advocate_inspection_uses_law_level_and_illegal_modifier(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    camp=c.execute("INSERT INTO camp_campaign(name,owner_reference) VALUES(%s,'p') RETURNING campaign_id",(str(uuid.uuid4()),)).fetchone()[0];aid,apub=c.execute("INSERT INTO actor_actor(campaign_id,name,controller_reference) VALUES(%s,'Advocate','p') RETURNING actor_id,public_id",(camp,)).fetchone();c.execute("INSERT INTO actor_characteristic(actor_id,characteristic_rule_id,maximum_value,current_value) SELECT %s,rule_id,7,7 FROM rule_rule WHERE rule_code='characteristic.education'",(aid,));c.execute("INSERT INTO actor_skill SELECT %s,rule_id,1 FROM rule_rule WHERE rule_code='skill.advocate'",(aid,))
    result=resolve_regulatory_task_command(c,initiator_reference='p',idempotency_key='inspection',actor_public_id=str(apub),operation_code='pass-ship-inspection',skill_rule_code='skill.advocate',case_reference='arrival-1',authority_reference='port authority',law_level=4,characteristic_rule_code='characteristic.education',illegal_material_present=True,random_source=R());self.assertEqual(result.illegal_modifier,-2);self.assertEqual(result.check_total,5);self.assertFalse(result.succeeded)
    replay=resolve_regulatory_task_command(c,initiator_reference='p',idempotency_key='inspection',actor_public_id=str(apub),operation_code='deal-with-bureaucrat',skill_rule_code='skill.admin',case_reference='changed',authority_reference='changed',law_level=0,characteristic_rule_code='characteristic.education',random_source=R());self.assertTrue(replay.replayed);self.assertEqual(replay.operation_code,'pass-ship-inspection')
    with self.assertRaises(ValueError):resolve_regulatory_task_command(c,initiator_reference='p',idempotency_key='wrong-skill',actor_public_id=str(apub),operation_code='pass-ship-inspection',skill_rule_code='skill.admin',case_reference='x',authority_reference='x',law_level=4,characteristic_rule_code='characteristic.education',random_source=R())
