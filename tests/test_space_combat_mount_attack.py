import os,unittest
import psycopg
from psycopg.errors import UniqueViolation
from tests import test_space_combat_dodge

@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class SpaceCombatMountAttackTests(unittest.TestCase):
 def setUp(self): self.helper=test_space_combat_dodge.SpaceCombatDodgeTests(); self.helper.setUp()
 def task(self,c,actor,effect,circumstance,suffix):
  command=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key,command_status,completed_at) VALUES('resolve_actor_task','test',%s,'completed',clock_timestamp()) RETURNING command_id",(f'mount-attack-{suffix}',)).fetchone()[0]
  characteristic=c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='characteristic.dexterity'").fetchone()[0]; skill=c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='skill.turret-weapons'").fetchone()[0]; difficulty=c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='difficulty.average'").fetchone()[0]
  total=8+effect
  c.execute('INSERT INTO cmd_actor_task_receipt(command_id,actor_id,characteristic_rule_id,skill_rule_id,difficulty_rule_id,skill_modifier,characteristic_modifier,difficulty_modifier,circumstance_modifier,species_modifier,check_total,target_number,effect,succeeded) VALUES(%s,%s,%s,%s,%s,0,0,0,%s,0,%s,8,%s,%s)',(command,actor,characteristic,skill,difficulty,circumstance,total,effect,total>=8)); return command
 def test_installed_mount_once_per_round_and_authoritative_check(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    campaign,engagement,ships,pilots,vessels,round_id,action,_=self.helper.fixture(c)
    gunner=c.execute('SELECT turn.crew_assignment_id FROM senc_action action JOIN senc_crew_turn turn USING(crew_turn_id) WHERE action.space_combat_action_id=%s',(action,)).fetchone()[0]
    actor=c.execute('SELECT actor_id FROM ship_crew_assignment WHERE crew_assignment_id=%s',(gunner,)).fetchone()[0]; skill=c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='skill.turret-weapons'").fetchone()[0]; c.execute('INSERT INTO actor_skill VALUES(%s,%s,0)',(actor,skill))
    c.execute("INSERT INTO senc_crew_role_assignment(engagement_id,campaign_id,senc_vessel_id,crew_assignment_id,ship_id,crew_role) VALUES(%s,%s,%s,%s,%s,'gunner')",(engagement,campaign,vessels[0],gunner,ships[0]))
    class_id=c.execute('SELECT ship_class_rule_id FROM ship_ship WHERE ship_id=%s',(ships[0],)).fetchone()[0]
    mount=c.execute("INSERT INTO ship_class_weapon_mount(ship_class_rule_id,mount_code,mount_identifier,mount_count) VALUES(%s,'single-turret','attack-test',1) RETURNING class_weapon_mount_id",(class_id,)).fetchone()[0]
    weapon=c.execute("SELECT weapon_rule_id FROM ship_weapon_definition WHERE weapon_code='pulse-laser'").fetchone()[0]; c.execute('INSERT INTO ship_class_mount_weapon VALUES(%s,%s,1,%s)',(mount,class_id,weapon))
    declaration=c.execute("INSERT INTO senc_mount_attack_declaration(action_id,engagement_id,campaign_id,space_combat_round_id,round_number,attacker_vessel_id,target_vessel_id,gunner_assignment_id,gunner_ship_id,class_weapon_mount_id,ship_class_rule_id,mount_instance,mount_code,mount_kind,range_band_code) VALUES(%s,%s,%s,%s,1,%s,%s,%s,%s,%s,%s,1,'single-turret','turret','short') RETURNING mount_attack_declaration_id",(action,engagement,campaign,round_id,vessels[0],vessels[1],gunner,ships[0],mount,class_id)).fetchone()[0]
    task=self.task(c,actor,1,-2,'hit')
    check_id=c.execute("INSERT INTO senc_mount_weapon_attack_check(mount_attack_declaration_id,weapon_slot,weapon_rule_id,weapon_profile_code,task_command_id,difficulty_rule_id,weapon_modifier,total_circumstance_modifier,attack_total,target_number,effect,hit) SELECT %s,1,%s,'pulse-laser',%s,rule_id,-2,-2,9,8,1,true FROM rule_rule WHERE rule_code='difficulty.average' RETURNING mount_weapon_attack_check_id",(declaration,weapon,task)).fetchone()[0]
    c.execute('INSERT INTO senc_weapon_damage_attempt(mount_weapon_attack_check_id,target_ship_id,campaign_id,damage_dice_count,damage_die_sides,damage_modifier,armor_snapshot,ignores_armor) VALUES(%s,%s,%s,2,6,0,0,false)',(check_id,ships[1],campaign))
    c.execute('INSERT INTO senc_weapon_damage_die VALUES(%s,1,4),(%s,2,5)',(check_id,check_id))
    c.execute('INSERT INTO senc_weapon_damage_final_receipt(mount_weapon_attack_check_id,rolled_damage,post_armor_damage) VALUES(%s,9,9)',(check_id,))
    c.execute("INSERT INTO senc_mount_damage_final_receipt(mount_attack_declaration_id,post_armor_damage_total,net_damage,single_hit_groups,double_hit_groups,triple_hit_groups) VALUES(%s,9,9,0,1,0)",(declaration,))
    c.execute('INSERT INTO senc_damage_location_group_roll VALUES(%s,1,2,3,4,7,clock_timestamp())',(declaration,))
    c.execute('INSERT INTO senc_damage_location_roll_set_receipt VALUES(%s,0,1,0,1,clock_timestamp())',(declaration,))
    first=c.execute('SELECT senc_apply_next_damage_location_hit(%s)',(declaration,)).fetchone()[0]
    second=c.execute('SELECT senc_apply_next_damage_location_hit(%s)',(declaration,)).fetchone()[0]
    self.assertNotEqual(first,second)
    self.assertEqual(c.execute('SELECT group_order,hit_order,rolled_location,applied_location FROM senc_damage_location_hit_receipt WHERE mount_attack_declaration_id=%s ORDER BY hit_order',(declaration,)).fetchall(),[(1,1,'armor','hull'),(1,2,'armor','hull')])
    self.assertEqual(c.execute('SELECT hull_before,hull_after FROM senc_damage_location_hit_receipt WHERE mount_attack_declaration_id=%s ORDER BY hit_order',(declaration,)).fetchall(),[(4,3),(3,2)])
    self.assertEqual(c.execute('SELECT hull_current FROM ship_ship WHERE ship_id=%s',(ships[1],)).fetchone()[0],2)
    with self.assertRaises(UniqueViolation):
     with c.transaction(): c.execute("INSERT INTO senc_mount_attack_declaration(action_id,engagement_id,campaign_id,space_combat_round_id,round_number,attacker_vessel_id,target_vessel_id,gunner_assignment_id,gunner_ship_id,class_weapon_mount_id,ship_class_rule_id,mount_instance,mount_code,mount_kind,range_band_code) VALUES(%s,%s,%s,%s,1,%s,%s,%s,%s,%s,%s,1,'single-turret','turret','short')",(action,engagement,campaign,round_id,vessels[0],vessels[1],gunner,ships[0],mount,class_id))

if __name__=='__main__': unittest.main()
