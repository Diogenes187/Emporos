import os
import unittest
import psycopg
from psycopg.errors import RaiseException
from tests import test_space_combat_dodge

@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class SpaceCombatFireSandTests(unittest.TestCase):
    def setUp(self):
        self.helper=test_space_combat_dodge.SpaceCombatDodgeTests(); self.helper.setUp()
    def task(self,c,actor,effect):
        command=c.execute("""INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key,command_status,completed_at)
         VALUES('resolve_actor_task','test','fire-sand-task','completed',clock_timestamp()) RETURNING command_id""").fetchone()[0]
        characteristic=c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='characteristic.dexterity'").fetchone()[0]
        skill=c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='skill.turret-weapons'").fetchone()[0]
        difficulty=c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='difficulty.average'").fetchone()[0]
        c.execute("""INSERT INTO cmd_actor_task_receipt(command_id,actor_id,characteristic_rule_id,skill_rule_id,difficulty_rule_id,
         skill_modifier,characteristic_modifier,difficulty_modifier,circumstance_modifier,species_modifier,check_total,target_number,effect,succeeded)
         VALUES(%s,%s,%s,%s,%s,1,0,0,0,0,%s,8,%s,%s)""",(command,actor,characteristic,skill,difficulty,8+effect,effect,effect>=0))
        return command
    def test_success_consumes_canister_and_reduces_each_beam_separately(self):
        with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
            rule=c.execute("""SELECT canisters_per_reaction,beam_reduction_dice_per_beam,beam_reduction_die_sides,
             resolve_each_beam_separately,boarding_damage_dice,boarding_damage_die_sides,ammunition_consumed_on_failure
             FROM rule_space_combat_fire_sand""").fetchone()
            self.assertEqual(rule,(1,1,6,True,8,6,True))
            with c.transaction(force_rollback=True):
                campaign,engagement,ships,pilots,vessels,round_id,attack,dodge_turn=self.helper.fixture(c)
                gunner=self.helper.helper.helper.crew_assignment(c,campaign,ships[1],'sand-defender')
                actor=c.execute('SELECT actor_id FROM ship_crew_assignment WHERE crew_assignment_id=%s',(gunner,)).fetchone()[0]
                dex=c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='characteristic.dexterity'").fetchone()[0]
                skill=c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='skill.turret-weapons'").fetchone()[0]
                c.execute('INSERT INTO actor_characteristic VALUES(%s,%s,8,8)',(actor,dex)); c.execute('INSERT INTO actor_skill VALUES(%s,%s,1)',(actor,skill))
                class_id=c.execute('SELECT ship_class_rule_id FROM ship_ship WHERE ship_id=%s',(ships[1],)).fetchone()[0]
                sandcaster=c.execute("SELECT weapon_rule_id FROM ship_weapon_definition WHERE weapon_code='sandcaster'").fetchone()[0]
                mount=c.execute("INSERT INTO ship_class_weapon_mount(ship_class_rule_id,mount_code,mount_identifier,mount_count) VALUES(%s,'single-turret','sand-test',1) RETURNING class_weapon_mount_id",(class_id,)).fetchone()[0]
                c.execute("INSERT INTO ship_class_mount_weapon VALUES(%s,%s,1,%s)",(mount,class_id,sandcaster))
                c.execute("INSERT INTO ship_class_weapon(ship_class_rule_id,weapon_rule_id,mount_identifier,quantity) VALUES(%s,%s,'sand-test-legacy',1)",(class_id,sandcaster))
                c.execute("INSERT INTO ship_resource VALUES(%s,%s,'sand',3,3,clock_timestamp(),NULL)",(ships[1],campaign))
                turn=c.execute("""INSERT INTO senc_crew_turn(space_combat_round_id,engagement_id,campaign_id,senc_vessel_id,
                 crew_assignment_id,initiative_at_action,turn_status) VALUES(%s,%s,%s,%s,%s,8,'acting') RETURNING crew_turn_id""",
                 (round_id,engagement,campaign,vessels[1],gunner)).fetchone()[0]
                action=c.execute("""INSERT INTO senc_action(crew_turn_id,space_combat_round_id,engagement_id,campaign_id,
                 action_order,action_code) VALUES(%s,%s,%s,%s,1,'fire-sand') RETURNING space_combat_action_id""",
                 (turn,round_id,engagement,campaign)).fetchone()[0]
                reaction=c.execute("""INSERT INTO senc_reaction(triggering_action_id,reacting_action_id,engagement_id,campaign_id,reaction_order)
                 VALUES(%s,%s,%s,%s,1) RETURNING reaction_id""",(attack,action,engagement,campaign)).fetchone()[0]
                task=self.task(c,actor,2)
                attempt=c.execute("""INSERT INTO senc_fire_sand_attempt_receipt(reaction_id,engagement_id,campaign_id,
                 space_combat_round_id,round_number,senc_vessel_id,gunner_assignment_id,gunner_ship_id,task_command_id,
                 task_effect,task_succeeded,incoming_beam_count,sand_before,sand_after)
                 VALUES(%s,%s,%s,%s,1,%s,%s,%s,%s,2,true,2,3,2) RETURNING fire_sand_attempt_receipt_id""",
                 (reaction,engagement,campaign,round_id,vessels[1],gunner,ships[1],task)).fetchone()[0]
                self.assertEqual(c.execute("SELECT current_quantity FROM ship_resource WHERE ship_id=%s AND resource_type_code='sand'",(ships[1],)).fetchone()[0],2)
                self.assertEqual(c.execute("SELECT readiness_status FROM senc_weapon_readiness_state WHERE senc_vessel_id=%s AND class_weapon_mount_id=%s",(vessels[1],mount)).fetchone()[0],'spent')
                self.assertEqual(c.execute("SELECT quantity_consumed FROM senc_weapon_ammunition_consumption_receipt WHERE fire_sand_attempt_receipt_id=%s",(attempt,)).fetchone()[0],1)
                c.execute('INSERT INTO senc_fire_sand_reduction_die VALUES(%s,1,4),(%s,2,2)',(attempt,attempt))
                c.execute('INSERT INTO senc_fire_sand_final_receipt VALUES(%s,6,clock_timestamp())',(attempt,))
                self.assertEqual(c.execute('SELECT beam_order,result FROM senc_fire_sand_reduction_die WHERE fire_sand_attempt_receipt_id=%s ORDER BY beam_order',(attempt,)).fetchall(),[(1,4),(2,2)])
                with self.assertRaisesRegex(RaiseException,'immutable'):
                    with c.transaction(): c.execute('DELETE FROM senc_fire_sand_reduction_die WHERE fire_sand_attempt_receipt_id=%s',(attempt,))

if __name__=='__main__': unittest.main()
