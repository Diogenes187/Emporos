import os,unittest
import psycopg
from psycopg.errors import RaiseException
from tests import test_space_combat_coordinate_crew

@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class SpaceCombatSensorTargetingTests(unittest.TestCase):
 def setUp(self): self.helper=test_space_combat_coordinate_crew.SpaceCombatCoordinateCrewTests(); self.helper.setUp()
 def task(self,c,actor,effect,suffix):
  command=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key,command_status,completed_at) VALUES('resolve_actor_task','test',%s,'completed',clock_timestamp()) RETURNING command_id",(f'sensor-target-{suffix}',)).fetchone()[0]
  characteristic=c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='characteristic.education'").fetchone()[0]; skill=c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='skill.comms'").fetchone()[0]; difficulty=c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='difficulty.average'").fetchone()[0]
  total=8+effect
  c.execute('INSERT INTO cmd_actor_task_receipt(command_id,actor_id,characteristic_rule_id,skill_rule_id,difficulty_rule_id,skill_modifier,characteristic_modifier,difficulty_modifier,circumstance_modifier,species_modifier,check_total,target_number,effect,succeeded) VALUES(%s,%s,%s,%s,%s,0,0,0,0,0,%s,8,%s,%s)',(command,actor,characteristic,skill,difficulty,total,effect,total>=8)); return command
 def test_target_specific_exceptional_bonus_and_snapshot(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   self.assertEqual(c.execute('SELECT success_attack_bonus,exceptional_effect_threshold,exceptional_attack_bonus,missile_launch_check_benefits,missile_impact_roll_benefits,smart_missiles_benefit FROM rule_space_combat_sensor_targeting').fetchone(),(1,6,2,True,False,False))
   with c.transaction(force_rollback=True):
    campaign,engagement,ships,pilots,vessels=self.helper.helper.fixture(c)
    c.execute("INSERT INTO ship_class_electronics(ship_class_rule_id,electronics_code) SELECT ship_class_rule_id,'advanced' FROM ship_ship WHERE ship_id=%s ON CONFLICT(ship_class_rule_id) DO UPDATE SET electronics_code='advanced'",(ships[1],))
    actor=c.execute("INSERT INTO actor_actor(campaign_id,name,controller_reference) VALUES(%s,'Sensor Op','player') RETURNING actor_id",(campaign,)).fetchone()[0]
    comms=c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='skill.comms'").fetchone()[0]; c.execute('INSERT INTO actor_skill VALUES(%s,%s,0)',(actor,comms))
    assignment=self.helper.assignment(c,campaign,ships[0],actor,'other','sensor-op')
    c.execute("INSERT INTO senc_crew_role_assignment(engagement_id,campaign_id,senc_vessel_id,crew_assignment_id,ship_id,crew_role) VALUES(%s,%s,%s,%s,%s,'sensors_operator')",(engagement,campaign,vessels[0],assignment,ships[0]))
    round_id=c.execute('SELECT senc_open_next_round(%s)',(engagement,)).fetchone()[0]
    action=self.helper.helper.action(c,campaign,engagement,round_id,vessels[0],assignment,vessels[1],'sensor-targeting')
    task=self.task(c,actor,6,'exceptional')
    receipt=c.execute("INSERT INTO senc_sensor_targeting_receipt(action_id,engagement_id,campaign_id,space_combat_round_id,round_number,senc_vessel_id,target_vessel_id,operator_assignment_id,operator_ship_id,target_electronics_code,target_sensor_jamming_rating,task_command_id,task_effect,task_succeeded,attack_bonus) VALUES(%s,%s,%s,%s,1,%s,%s,%s,%s,'advanced',1,%s,6,true,2) RETURNING sensor_targeting_receipt_id",(action,engagement,campaign,round_id,vessels[0],vessels[1],assignment,ships[0],task)).fetchone()[0]
    with self.assertRaisesRegex(RaiseException,'immutable'):
     with c.transaction(): c.execute('DELETE FROM senc_sensor_targeting_receipt WHERE sensor_targeting_receipt_id=%s',(receipt,))

if __name__=='__main__': unittest.main()
