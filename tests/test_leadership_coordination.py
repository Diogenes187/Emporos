import os,unittest,uuid
import psycopg
from engine.leadership import begin_leadership_coordination_command,allocate_leadership_coordination_command
from engine.tasks import resolve_actor_task_command
class R:
 def __init__(self,v):self.v=iter(v)
 def randint(self,a,b):return next(self.v)
class LeadershipCoordinationTests(unittest.TestCase):
 def actors(self,c):
  camp=c.execute("INSERT INTO camp_campaign(name) VALUES(%s) RETURNING campaign_id",(str(uuid.uuid4()),)).fetchone()[0];out=[]
  for name,controller in [('Leader','p'),('Teammate','q')]:
   aid,pub=c.execute("INSERT INTO actor_actor(campaign_id,name,controller_reference) VALUES(%s,%s,%s) RETURNING actor_id,public_id",(camp,name,controller)).fetchone();c.execute("""INSERT INTO actor_characteristic(actor_id,characteristic_rule_id,maximum_value,current_value) SELECT %s,rule_id,7,7 FROM rule_rule WHERE rule_code='characteristic.intelligence'""",(aid,));c.execute("""INSERT INTO actor_skill SELECT %s,rule_id,CASE WHEN rule_code='skill.leadership' THEN 1 ELSE 0 END FROM rule_rule WHERE rule_code IN('skill.leadership','skill.athletics')""",(aid,));out.append(str(pub))
  return out
 def test_effect_pool_allocation_and_goal_bound_consumption(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    leader,mate=self.actors(c);coord=begin_leadership_coordination_command(c,initiator_reference='p',idempotency_key='lead',leader_actor_public_id=leader,goal_reference='raise-vault-door',characteristic_rule_code='characteristic.intelligence',random_source=R((6,6)));self.assertEqual(coord.total_points,5)
    allocation=allocate_leadership_coordination_command(c,initiator_reference='p',idempotency_key='alloc',coordination_public_id=coord.coordination_public_id,recipient_actor_public_id=mate,points=3);self.assertEqual(allocation.remaining_points,2)
    with self.assertRaises(ValueError):resolve_actor_task_command(c,initiator_reference='q',idempotency_key='wrong-goal',actor_public_id=mate,characteristic_rule_code='characteristic.intelligence',skill_rule_code='skill.athletics',difficulty_rule_code='difficulty.average',leadership_allocation_public_id=allocation.allocation_public_id,goal_reference='other-goal',random_source=R((6,6)))
    task=resolve_actor_task_command(c,initiator_reference='q',idempotency_key='team-task',actor_public_id=mate,characteristic_rule_code='characteristic.intelligence',skill_rule_code='skill.athletics',difficulty_rule_code='difficulty.average',leadership_allocation_public_id=allocation.allocation_public_id,goal_reference='raise-vault-door',random_source=R((2,2)));self.assertEqual(task.leadership_modifier,3);self.assertEqual(task.total,7)
    with self.assertRaises(ValueError):resolve_actor_task_command(c,initiator_reference='q',idempotency_key='reuse',actor_public_id=mate,characteristic_rule_code='characteristic.intelligence',skill_rule_code='skill.athletics',difficulty_rule_code='difficulty.average',leadership_allocation_public_id=allocation.allocation_public_id,goal_reference='raise-vault-door',random_source=R((6,6)))
 def test_failed_leadership_check_still_creates_minimum_one_point(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    leader,_=self.actors(c);coord=begin_leadership_coordination_command(c,initiator_reference='p',idempotency_key='minimum',leader_actor_public_id=leader,goal_reference='survive-storm',characteristic_rule_code='characteristic.intelligence',random_source=R((1,1)));self.assertEqual(coord.total_points,1)
