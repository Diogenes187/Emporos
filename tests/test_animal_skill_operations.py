import os,unittest,uuid
import psycopg
from engine.animal_skills import resolve_animal_skill_operation_command
class R:
 def randint(self,a,b):return 4
@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class AnimalSkillOperationTests(unittest.TestCase):
 def test_riding_requires_campaign_animal_and_replays(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    camp=c.execute("INSERT INTO camp_campaign(name,owner_reference) VALUES(%s,'p') RETURNING campaign_id",(str(uuid.uuid4()),)).fetchone()[0];aid,apub=c.execute("INSERT INTO actor_actor(campaign_id,name,controller_reference) VALUES(%s,'Rider','p') RETURNING actor_id,public_id",(camp,)).fetchone();animal,animalpub=c.execute("INSERT INTO actor_actor(campaign_id,name,controller_reference) VALUES(%s,'Mount','p') RETURNING actor_id,public_id",(camp,)).fetchone();subtype=c.execute("SELECT rule_id FROM rule_animal_subtype ORDER BY rule_id LIMIT 1").fetchone()[0];c.execute("INSERT INTO actor_animal_profile VALUES(%s,%s,'test-mount')",(animal,subtype));c.execute("INSERT INTO actor_characteristic(actor_id,characteristic_rule_id,maximum_value,current_value) SELECT %s,rule_id,7,7 FROM rule_rule WHERE rule_code='characteristic.dexterity'",(aid,));c.execute("INSERT INTO actor_skill SELECT %s,rule_id,1 FROM rule_rule WHERE rule_code='skill.riding'",(aid,))
    result=resolve_animal_skill_operation_command(c,initiator_reference='p',idempotency_key='ride',actor_public_id=str(apub),operation_code='maneuver-riding-animal',objective_reference='cross the ravine',subject_animal_public_id=str(animalpub),characteristic_rule_code='characteristic.dexterity',difficulty_rule_code='difficulty.average',random_source=R());self.assertEqual(result.skill_rule_code,'skill.riding');self.assertTrue(result.succeeded)
    replay=resolve_animal_skill_operation_command(c,initiator_reference='p',idempotency_key='ride',actor_public_id=str(apub),operation_code='grow-crops',objective_reference='changed',characteristic_rule_code='characteristic.dexterity',difficulty_rule_code='difficulty.average',random_source=R());self.assertTrue(replay.replayed);self.assertEqual(replay.operation_code,'maneuver-riding-animal')
