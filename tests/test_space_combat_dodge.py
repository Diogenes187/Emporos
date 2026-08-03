import os
import unittest
import psycopg
from psycopg.errors import CheckViolation, RaiseException
from tests import test_space_combat_pursuit

@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class SpaceCombatDodgeTests(unittest.TestCase):
    def setUp(self):
        self.helper=test_space_combat_pursuit.SpaceCombatPursuitTests(); self.helper.setUp()
    def fixture(self,c):
        campaign,engagement,ships,pilots,vessels=self.helper.fixture(c)
        gunner=self.helper.helper.crew_assignment(c,campaign,ships[0],'dodge-attacker')
        round_id=c.execute('SELECT senc_open_next_round(%s)',(engagement,)).fetchone()[0]
        attack_turn=c.execute("""INSERT INTO senc_crew_turn(space_combat_round_id,engagement_id,campaign_id,senc_vessel_id,
         crew_assignment_id,initiative_at_action,turn_status) VALUES(%s,%s,%s,%s,%s,9,'acting') RETURNING crew_turn_id""",
         (round_id,engagement,campaign,vessels[0],gunner)).fetchone()[0]
        attack=c.execute("""INSERT INTO senc_action(crew_turn_id,space_combat_round_id,engagement_id,campaign_id,
         action_order,action_code,target_vessel_id) VALUES(%s,%s,%s,%s,1,'attack',%s) RETURNING space_combat_action_id""",
         (attack_turn,round_id,engagement,campaign,vessels[1])).fetchone()[0]
        dodge_turn=c.execute("""INSERT INTO senc_crew_turn(space_combat_round_id,engagement_id,campaign_id,senc_vessel_id,
         crew_assignment_id,initiative_at_action,turn_status) VALUES(%s,%s,%s,%s,%s,8,'acting') RETURNING crew_turn_id""",
         (round_id,engagement,campaign,vessels[1],pilots[1][1])).fetchone()[0]
        return campaign,engagement,ships,pilots,vessels,round_id,attack,dodge_turn
    def reaction(self,c,campaign,engagement,round_id,attack,dodge_turn,order):
        action=c.execute("""INSERT INTO senc_action(crew_turn_id,space_combat_round_id,engagement_id,campaign_id,
         action_order,action_code) VALUES(%s,%s,%s,%s,%s,'dodge') RETURNING space_combat_action_id""",
         (dodge_turn,round_id,engagement,campaign,order)).fetchone()[0]
        return c.execute("""INSERT INTO senc_reaction(triggering_action_id,reacting_action_id,engagement_id,campaign_id,reaction_order)
         VALUES(%s,%s,%s,%s,%s) RETURNING reaction_id""",(attack,action,engagement,campaign,order)).fetchone()[0]
    def test_successful_dodge_applies_minus_two_and_is_immutable(self):
        with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
            self.assertEqual(c.execute('SELECT minimum_initiative,maximum_initiative,maximum_reactions FROM rule_space_combat_reaction_limit ORDER BY minimum_initiative').fetchall(),[(0,4,1),(5,8,2),(9,12,3),(13,None,4)])
            with c.transaction(force_rollback=True):
                campaign,engagement,ships,pilots,vessels,round_id,attack,dodge_turn=self.fixture(c)
                reaction=self.reaction(c,campaign,engagement,round_id,attack,dodge_turn,1)
                task=self.helper.task(c,pilots[1][0],'dodge-success',1)
                receipt=c.execute("""INSERT INTO senc_dodge_receipt(reaction_id,engagement_id,campaign_id,
                 space_combat_round_id,round_number,senc_vessel_id,pilot_assignment_id,pilot_ship_id,
                 task_command_id,task_effect,task_succeeded,attack_modifier)
                 VALUES(%s,%s,%s,%s,1,%s,%s,%s,%s,1,true,-2) RETURNING dodge_receipt_id""",
                 (reaction,engagement,campaign,round_id,vessels[1],pilots[1][1],ships[1],task)).fetchone()[0]
                with self.assertRaisesRegex(RaiseException,'immutable'):
                    with c.transaction(): c.execute('DELETE FROM senc_dodge_receipt WHERE dodge_receipt_id=%s',(receipt,))
    def test_initiative_eight_allows_only_two_reactions(self):
        with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
            with c.transaction(force_rollback=True):
                campaign,engagement,ships,pilots,vessels,round_id,attack,dodge_turn=self.fixture(c)
                self.reaction(c,campaign,engagement,round_id,attack,dodge_turn,1)
                self.reaction(c,campaign,engagement,round_id,attack,dodge_turn,2)
                with self.assertRaisesRegex(CheckViolation,'budget'):
                    with c.transaction(): self.reaction(c,campaign,engagement,round_id,attack,dodge_turn,3)

if __name__=='__main__': unittest.main()
