import os, unittest
import psycopg
from psycopg.errors import CheckViolation, RaiseException
from tests import test_space_combat_pursuit

@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class SpaceCombatCoordinateCrewTests(unittest.TestCase):
 def setUp(self): self.helper=test_space_combat_pursuit.SpaceCombatPursuitTests(); self.helper.setUp()
 def assignment(self,c,campaign,ship,actor,role,suffix):
  role_id=c.execute('SELECT crew_position_rule_id FROM ship_crew_position_definition WHERE position_code=%s',(role,)).fetchone()[0]
  position=c.execute("INSERT INTO ship_crew_position(ship_id,campaign_id,crew_position_rule_id,position_identifier) VALUES(%s,%s,%s,%s) RETURNING ship_crew_position_id",(ship,campaign,role_id,suffix)).fetchone()[0]
  return c.execute('INSERT INTO ship_crew_assignment(ship_crew_position_id,ship_id,campaign_id,actor_id) VALUES(%s,%s,%s,%s) RETURNING crew_assignment_id',(position,ship,campaign,actor)).fetchone()[0]
 def task(self,c,actor,effect):
  command=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key,command_status,completed_at) VALUES('resolve_actor_task','test',%s,'completed',clock_timestamp()) RETURNING command_id",(f'coordinate-{effect}',)).fetchone()[0]
  characteristic=c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='characteristic.intelligence'").fetchone()[0]
  skill=c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='skill.leadership'").fetchone()[0]
  difficulty=c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='difficulty.average'").fetchone()[0]
  total=8+effect
  c.execute('INSERT INTO cmd_actor_task_receipt(command_id,actor_id,characteristic_rule_id,skill_rule_id,difficulty_rule_id,skill_modifier,characteristic_modifier,difficulty_modifier,circumstance_modifier,species_modifier,check_total,target_number,effect,succeeded) VALUES(%s,%s,%s,%s,%s,0,0,0,0,0,%s,8,%s,%s)',(command,actor,characteristic,skill,difficulty,total,effect,total>=8))
  return command
 def test_pool_allocation_scope_cap_and_immutability(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   self.assertEqual(c.execute('SELECT minimum_pool_points,points_per_effect,modifier_per_point,individual_crew_allocations,current_round_only FROM rule_space_combat_coordinate_crew').fetchone(),(1,1,1,True,True))
   with c.transaction(force_rollback=True):
    campaign,engagement,ships,pilots,vessels=self.helper.fixture(c)
    actor=c.execute("INSERT INTO actor_actor(campaign_id,name,controller_reference) VALUES(%s,'Captain','player') RETURNING actor_id",(campaign,)).fetchone()[0]
    leadership=c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='skill.leadership'").fetchone()[0]
    c.execute('INSERT INTO actor_skill(actor_id,skill_rule_id,skill_level) VALUES(%s,%s,0)',(actor,leadership))
    captain=self.assignment(c,campaign,ships[0],actor,'master','captain')
    round_id=c.execute('SELECT senc_open_next_round(%s)',(engagement,)).fetchone()[0]
    action=self.helper.action(c,campaign,engagement,round_id,vessels[0],captain,None,'coordinate-crew')
    task=self.task(c,actor,3)
    receipt=c.execute('INSERT INTO senc_coordinate_crew_receipt(action_id,engagement_id,campaign_id,space_combat_round_id,round_number,senc_vessel_id,captain_assignment_id,captain_ship_id,task_command_id,task_effect,pool_points) VALUES(%s,%s,%s,%s,1,%s,%s,%s,%s,3,3) RETURNING coordinate_crew_receipt_id',(action,engagement,campaign,round_id,vessels[0],captain,ships[0],task)).fetchone()[0]
    allocation=c.execute('INSERT INTO senc_coordinate_crew_allocation(coordinate_crew_receipt_id,recipient_assignment_id,recipient_ship_id,campaign_id,points) VALUES(%s,%s,%s,%s,2) RETURNING coordinate_crew_allocation_id',(receipt,pilots[0][1],ships[0],campaign)).fetchone()[0]
    with self.assertRaisesRegex(CheckViolation,'exceeds'):
     with c.transaction(): c.execute('INSERT INTO senc_coordinate_crew_allocation(coordinate_crew_receipt_id,recipient_assignment_id,recipient_ship_id,campaign_id,points) VALUES(%s,%s,%s,%s,2)',(receipt,captain,ships[0],campaign))
    with self.assertRaisesRegex(RaiseException,'immutable'):
     with c.transaction(): c.execute('DELETE FROM senc_coordinate_crew_allocation WHERE coordinate_crew_allocation_id=%s',(allocation,))

if __name__=='__main__': unittest.main()
