import os
import unittest
import psycopg
from psycopg.errors import CheckViolation, RaiseException
from tests import test_space_combat_pursuit

@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class SpaceCombatAvoidCollisionTests(unittest.TestCase):
    def setUp(self):
        self.helper=test_space_combat_pursuit.SpaceCombatPursuitTests(); self.helper.setUp()
    def task(self,c,actor,suffix,effect,difficulty_code,circumstance=0):
        command=c.execute("""INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key,command_status,completed_at)
         VALUES('resolve_actor_task','test',%s,'completed',clock_timestamp()) RETURNING command_id""",(f'avoid-{suffix}',)).fetchone()[0]
        characteristic=c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='characteristic.dexterity'").fetchone()[0]
        skill=c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='skill.piloting'").fetchone()[0]
        difficulty=c.execute('SELECT rule_id FROM rule_rule WHERE rule_code=%s',(difficulty_code,)).fetchone()[0]
        c.execute("""INSERT INTO cmd_actor_task_receipt(command_id,actor_id,characteristic_rule_id,skill_rule_id,difficulty_rule_id,
         skill_modifier,characteristic_modifier,difficulty_modifier,circumstance_modifier,species_modifier,check_total,target_number,effect,succeeded)
         VALUES(%s,%s,%s,%s,%s,1,0,0,%s,0,%s,8,%s,%s)""",
         (command,actor,characteristic,skill,difficulty,circumstance,8+effect,effect,effect>=0))
        return command
    def fixture(self,c,hazard='asteroid-heavy',speed_difference=True):
        campaign,engagement,ships,pilots,vessels=self.helper.fixture(c)
        round_id=c.execute('SELECT senc_open_next_round(%s)',(engagement,)).fetchone()[0]
        action=self.helper.action(c,campaign,engagement,round_id,vessels[0],pilots[0][1],None,'avoid-collision')
        hazard_id=c.execute("""INSERT INTO senc_collision_hazard(engagement_id,campaign_id,space_combat_round_id,
         round_number,senc_vessel_id,hazard_code,significant_speed_difference,range_band_snapshot,speed_snapshot)
         VALUES(%s,%s,%s,1,%s,%s,%s,'short',2) RETURNING collision_hazard_id""",
         (engagement,campaign,round_id,vessels[0],hazard,speed_difference)).fetchone()[0]
        return campaign,engagement,ships,pilots,vessels,round_id,action,hazard_id
    def test_failed_heavy_asteroid_check_applies_speed_dice_damage(self):
        with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
            self.assertEqual(c.execute("SELECT hazard_code,r.name FROM rule_space_collision_hazard h JOIN rule_rule r ON r.rule_id=h.difficulty_rule_id ORDER BY hazard_code").fetchall(),
             [('asteroid-average','Very Difficult'),('asteroid-heavy','Formidable'),('asteroid-light','Difficult'),('traffic-debris','Average')])
            with c.transaction(force_rollback=True):
                campaign,engagement,ships,pilots,vessels,round_id,action,hazard=self.fixture(c)
                with self.assertRaisesRegex(CheckViolation,'requires resolution'):
                    with c.transaction(): c.execute("UPDATE senc_round SET round_status='completed',ended_at=clock_timestamp() WHERE space_combat_round_id=%s",(round_id,))
                task=self.task(c,pilots[0][0],'fail',-1,'difficulty.formidable',-2)
                c.execute('INSERT INTO senc_collision_damage_die VALUES(%s,1,3),(%s,2,4)',(hazard,hazard))
                receipt=c.execute("""INSERT INTO senc_avoid_collision_receipt(collision_hazard_id,action_id,task_command_id,
                 task_effect,task_succeeded,rolled_damage,ship_id,armor_snapshot,net_damage,hull_before,hull_after,
                 structure_before,structure_after,version_before,version_after)
                 VALUES(%s,%s,%s,-1,false,7,%s,0,7,4,0,4,1,1,2) RETURNING avoid_collision_receipt_id""",
                 (hazard,action,task,ships[0])).fetchone()[0]
                self.assertEqual(c.execute('SELECT hull_current,structure_current FROM ship_ship WHERE ship_id=%s',(ships[0],)).fetchone(),(0,1))
                self.assertEqual(c.execute('SELECT damage_kind,damage_points FROM senc_collision_damage_allocation WHERE avoid_collision_receipt_id=%s ORDER BY damage_kind',(receipt,)).fetchall(),[('hull',4),('structure',3)])
                c.execute("UPDATE senc_round SET round_status='completed',ended_at=clock_timestamp() WHERE space_combat_round_id=%s",(round_id,))
                with self.assertRaisesRegex(RaiseException,'immutable'):
                    with c.transaction(): c.execute('DELETE FROM senc_collision_damage_die WHERE collision_hazard_id=%s',(hazard,))
    def test_success_has_no_collision_dice_or_damage(self):
        with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
            with c.transaction(force_rollback=True):
                campaign,engagement,ships,pilots,vessels,round_id,action,hazard=self.fixture(c,'traffic-debris',False)
                task=self.task(c,pilots[0][0],'success',1,'difficulty.average')
                c.execute("""INSERT INTO senc_avoid_collision_receipt(collision_hazard_id,action_id,task_command_id,
                 task_effect,task_succeeded,rolled_damage,ship_id,armor_snapshot,net_damage,hull_before,hull_after,
                 structure_before,structure_after,version_before,version_after)
                 VALUES(%s,%s,%s,1,true,0,%s,0,0,4,4,4,4,1,2)""",(hazard,action,task,ships[0]))
                self.assertEqual(c.execute('SELECT count(*) FROM senc_collision_damage_die WHERE collision_hazard_id=%s',(hazard,)).fetchone()[0],0)

if __name__=='__main__': unittest.main()
