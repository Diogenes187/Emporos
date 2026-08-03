import os
import unittest
import psycopg
from psycopg.errors import CheckViolation, RaiseException
from tests import test_space_combat_pursuit

@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class SpaceCombatPilotMovementTests(unittest.TestCase):
    def setUp(self):
        self.helper=test_space_combat_pursuit.SpaceCombatPursuitTests(); self.helper.setUp()
    def fixture(self,c,code):
        campaign,engagement,ships,pilots,vessels=self.helper.fixture(c)
        round_id=c.execute('SELECT senc_open_next_round(%s)',(engagement,)).fetchone()[0]
        action=self.helper.action(c,campaign,engagement,round_id,vessels[0],pilots[0][1],None,code)
        return campaign,engagement,ships,pilots,vessels,round_id,action
    def test_adjust_speed_is_thrust_bounded_and_atomic(self):
        with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
            rule=c.execute("""SELECT speed_change_limited_by_thrust,minimum_speed,adjust_requires_check,
             maintain_requires_check,maintain_preserves_speed,both_are_minor_actions FROM rule_space_combat_pilot_movement""").fetchone()
            self.assertEqual(rule,(True,0,False,False,True,True))
            with c.transaction(force_rollback=True):
                campaign,engagement,ships,pilots,vessels,round_id,action=self.fixture(c,'adjust-speed')
                receipt=c.execute("""INSERT INTO senc_pilot_movement_receipt
                 (engagement_id,campaign_id,space_combat_round_id,round_number,senc_vessel_id,action_id,
                  pilot_assignment_id,pilot_ship_id,movement_kind,speed_before,speed_after,thrust_snapshot)
                 VALUES(%s,%s,%s,1,%s,%s,%s,%s,'adjust-speed',2,4,2) RETURNING pilot_movement_receipt_id""",
                 (engagement,campaign,round_id,vessels[0],action,pilots[0][1],ships[0])).fetchone()[0]
                self.assertEqual(c.execute('SELECT speed_current FROM senc_vessel WHERE senc_vessel_id=%s',(vessels[0],)).fetchone()[0],4)
                with self.assertRaisesRegex(RaiseException,'immutable'):
                    with c.transaction(): c.execute('DELETE FROM senc_pilot_movement_receipt WHERE pilot_movement_receipt_id=%s',(receipt,))
            with c.transaction(force_rollback=True):
                campaign,engagement,ships,pilots,vessels,round_id,action=self.fixture(c,'adjust-speed')
                with self.assertRaises(CheckViolation):
                    with c.transaction(): c.execute("""INSERT INTO senc_pilot_movement_receipt
                     (engagement_id,campaign_id,space_combat_round_id,round_number,senc_vessel_id,action_id,
                      pilot_assignment_id,pilot_ship_id,movement_kind,speed_before,speed_after,thrust_snapshot)
                     VALUES(%s,%s,%s,1,%s,%s,%s,%s,'adjust-speed',2,5,2)""",
                     (engagement,campaign,round_id,vessels[0],action,pilots[0][1],ships[0]))
    def test_maintain_course_preserves_speed(self):
        with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
            with c.transaction(force_rollback=True):
                campaign,engagement,ships,pilots,vessels,round_id,action=self.fixture(c,'maintain-course')
                c.execute("""INSERT INTO senc_pilot_movement_receipt
                 (engagement_id,campaign_id,space_combat_round_id,round_number,senc_vessel_id,action_id,
                  pilot_assignment_id,pilot_ship_id,movement_kind,speed_before,speed_after,thrust_snapshot)
                 VALUES(%s,%s,%s,1,%s,%s,%s,%s,'maintain-course',2,2,2)""",
                 (engagement,campaign,round_id,vessels[0],action,pilots[0][1],ships[0]))
                self.assertEqual(c.execute('SELECT speed_current FROM senc_vessel WHERE senc_vessel_id=%s',(vessels[0],)).fetchone()[0],2)

if __name__=='__main__': unittest.main()
