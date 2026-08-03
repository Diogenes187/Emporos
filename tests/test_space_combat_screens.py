import os,unittest
import psycopg
from psycopg.errors import RaiseException
from tests import test_space_combat_dodge

@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class SpaceCombatScreenTests(unittest.TestCase):
 def setUp(self): self.helper=test_space_combat_dodge.SpaceCombatDodgeTests(); self.helper.setUp()
 def test_fusion_attack_reduction_uses_two_dice_plus_screen_skill(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   self.assertEqual(c.execute('SELECT minimum_skill_level,damage_reduction_dice,damage_reduction_die_sides,add_operator_skill,nuclear_removes_automatic_radiation,commander_or_gunner_may_operate FROM rule_space_combat_trigger_screens').fetchone(),(0,2,6,True,True,True))
   with c.transaction(force_rollback=True):
    campaign,engagement,ships,pilots,vessels,round_id,attack_action,_=self.helper.fixture(c)
    fusion=c.execute("SELECT weapon_rule_id FROM ship_weapon_definition WHERE weapon_code='fusion-gun-bay'").fetchone()[0]
    c.execute("INSERT INTO senc_attack(space_combat_action_id,engagement_id,campaign_id,attacker_vessel_id,target_vessel_id,weapon_rule_id,attack_total,target_number,effect,hit,rolled_damage,net_damage) VALUES(%s,%s,%s,%s,%s,%s,7,8,-1,false,0,0)",(attack_action,engagement,campaign,vessels[0],vessels[1],fusion))
    gunner=self.helper.helper.helper.crew_assignment(c,campaign,ships[1],'screen'); actor=c.execute('SELECT actor_id FROM ship_crew_assignment WHERE crew_assignment_id=%s',(gunner,)).fetchone()[0]
    screens=c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='skill.screens'").fetchone()[0]; c.execute('INSERT INTO actor_skill VALUES(%s,%s,0)',(actor,screens))
    class_id=c.execute('SELECT ship_class_rule_id FROM ship_ship WHERE ship_id=%s',(ships[1],)).fetchone()[0]; c.execute('UPDATE ship_class SET minimum_tech_level=12 WHERE ship_class_rule_id=%s',(class_id,)); c.execute("INSERT INTO ship_class_screen VALUES(%s,'nuclear-damper',1)",(class_id,))
    turn=c.execute("INSERT INTO senc_crew_turn(space_combat_round_id,engagement_id,campaign_id,senc_vessel_id,crew_assignment_id,initiative_at_action,turn_status) VALUES(%s,%s,%s,%s,%s,8,'acting') RETURNING crew_turn_id",(round_id,engagement,campaign,vessels[1],gunner)).fetchone()[0]
    action=c.execute("INSERT INTO senc_action(crew_turn_id,space_combat_round_id,engagement_id,campaign_id,action_order,action_code) VALUES(%s,%s,%s,%s,1,'trigger-screens') RETURNING space_combat_action_id",(turn,round_id,engagement,campaign)).fetchone()[0]
    reaction=c.execute("INSERT INTO senc_reaction(triggering_action_id,reacting_action_id,engagement_id,campaign_id,reaction_order) VALUES(%s,%s,%s,%s,1) RETURNING reaction_id",(attack_action,action,engagement,campaign)).fetchone()[0]
    attempt=c.execute("INSERT INTO senc_screen_attempt_receipt(reaction_id,engagement_id,campaign_id,space_combat_round_id,senc_vessel_id,operator_assignment_id,operator_ship_id,screen_code,incoming_weapon_kind,operator_skill_level) VALUES(%s,%s,%s,%s,%s,%s,%s,'nuclear-damper','fusion',0) RETURNING screen_attempt_receipt_id",(reaction,engagement,campaign,round_id,vessels[1],gunner,ships[1])).fetchone()[0]
    c.execute('INSERT INTO senc_screen_reduction_die VALUES(%s,1,4),(%s,2,3)',(attempt,attempt)); c.execute('INSERT INTO senc_screen_final_receipt VALUES(%s,7,7,false,clock_timestamp())',(attempt,))
    with self.assertRaisesRegex(RaiseException,'immutable'):
     with c.transaction(): c.execute('DELETE FROM senc_screen_reduction_die WHERE screen_attempt_receipt_id=%s',(attempt,))

if __name__=='__main__': unittest.main()
