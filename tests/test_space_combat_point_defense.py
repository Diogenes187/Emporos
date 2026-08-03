import os,unittest
import psycopg
from psycopg.errors import CheckViolation
from tests import test_space_combat_dodge

@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class SpaceCombatPointDefenseTests(unittest.TestCase):
 def setUp(self): self.helper=test_space_combat_dodge.SpaceCombatDodgeTests(); self.helper.setUp()
 def task(self,c,actor,order,effect,modifier):
  cmd=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key,command_status,completed_at) VALUES('resolve_actor_task','test',%s,'completed',clock_timestamp()) RETURNING command_id",(f'pd-{order}',)).fetchone()[0]
  char=c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='characteristic.dexterity'").fetchone()[0]; skill=c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='skill.turret-weapons'").fetchone()[0]; diff=c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='difficulty.average'").fetchone()[0]
  c.execute("INSERT INTO cmd_actor_task_receipt(command_id,actor_id,characteristic_rule_id,skill_rule_id,difficulty_rule_id,skill_modifier,characteristic_modifier,difficulty_modifier,circumstance_modifier,species_modifier,check_total,target_number,effect,succeeded) VALUES(%s,%s,%s,%s,%s,1,0,0,%s,0,%s,8,%s,%s)",(cmd,actor,char,skill,diff,modifier,8+effect,effect,effect>=0)); return cmd
 def test_successes_destroy_missiles_until_first_failure(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    campaign,engagement,ships,pilots,vessels,round_id,attack_action,_=self.helper.fixture(c)
    missile=c.execute("SELECT weapon_rule_id FROM ship_weapon_definition WHERE weapon_code='missile-rack'").fetchone()[0]
    attack=c.execute("INSERT INTO senc_attack(space_combat_action_id,engagement_id,campaign_id,attacker_vessel_id,target_vessel_id,weapon_rule_id,attack_total,target_number,effect,hit,rolled_damage,net_damage) VALUES(%s,%s,%s,%s,%s,%s,7,8,-1,false,0,0) RETURNING attack_id",(attack_action,engagement,campaign,vessels[0],vessels[1],missile)).fetchone()[0]
    salvo=c.execute("INSERT INTO senc_missile_salvo(launch_attack_id,engagement_id,campaign_id,target_vessel_id,missile_count,smart_missiles,launched_round,impact_round,missiles_remaining) VALUES(%s,%s,%s,%s,3,false,1,2,3) RETURNING missile_salvo_id",(attack,engagement,campaign,vessels[1])).fetchone()[0]
    gunner=self.helper.helper.helper.crew_assignment(c,campaign,ships[1],'pd'); actor=c.execute('SELECT actor_id FROM ship_crew_assignment WHERE crew_assignment_id=%s',(gunner,)).fetchone()[0]
    dex=c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='characteristic.dexterity'").fetchone()[0]; tw=c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='skill.turret-weapons'").fetchone()[0]; c.execute('INSERT INTO actor_characteristic VALUES(%s,%s,8,8)',(actor,dex)); c.execute('INSERT INTO actor_skill VALUES(%s,%s,1)',(actor,tw))
    laser=c.execute("SELECT weapon_rule_id FROM ship_weapon_definition WHERE weapon_code='pulse-laser'").fetchone()[0]; class_id=c.execute('SELECT ship_class_rule_id FROM ship_ship WHERE ship_id=%s',(ships[1],)).fetchone()[0]; c.execute("INSERT INTO ship_class_weapon(ship_class_rule_id,weapon_rule_id,mount_identifier,quantity) VALUES(%s,%s,'pd-laser',1)",(class_id,laser))
    turn=c.execute("INSERT INTO senc_crew_turn(space_combat_round_id,engagement_id,campaign_id,senc_vessel_id,crew_assignment_id,initiative_at_action,turn_status) VALUES(%s,%s,%s,%s,%s,8,'acting') RETURNING crew_turn_id",(round_id,engagement,campaign,vessels[1],gunner)).fetchone()[0]
    action=c.execute("INSERT INTO senc_action(crew_turn_id,space_combat_round_id,engagement_id,campaign_id,action_order,action_code) VALUES(%s,%s,%s,%s,1,'point-defense') RETURNING space_combat_action_id",(turn,round_id,engagement,campaign)).fetchone()[0]
    reaction=c.execute("INSERT INTO senc_reaction(triggering_action_id,reacting_action_id,engagement_id,campaign_id,reaction_order) VALUES(%s,%s,%s,%s,1) RETURNING reaction_id",(attack_action,action,engagement,campaign)).fetchone()[0]
    seq=c.execute("INSERT INTO senc_point_defense_sequence(reaction_id,missile_salvo_id,engagement_id,campaign_id,space_combat_round_id,senc_vessel_id,gunner_assignment_id,gunner_ship_id,laser_weapon_rule_id,missiles_before) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,3) RETURNING point_defense_sequence_id",(reaction,salvo,engagement,campaign,round_id,vessels[1],gunner,ships[1],laser)).fetchone()[0]
    for order,effect,before,after in [(1,1,3,2),(2,1,2,1),(3,-1,1,1)]:
     task=self.task(c,actor,order,effect,-(order-1)); c.execute("INSERT INTO senc_point_defense_check_receipt VALUES(%s,%s,%s,%s,%s,%s,%s,%s,clock_timestamp())",(seq,order,task,-(order-1),effect,effect>=0,before,after))
    self.assertEqual(c.execute('SELECT missiles_remaining FROM senc_missile_salvo WHERE missile_salvo_id=%s',(salvo,)).fetchone()[0],1)
    with self.assertRaisesRegex(CheckViolation,'ended'):
     with c.transaction():
      task=self.task(c,actor,4,1,-3); c.execute("INSERT INTO senc_point_defense_check_receipt VALUES(%s,4,%s,-3,1,true,1,0,clock_timestamp())",(seq,task))

if __name__=='__main__': unittest.main()
