import os
import unittest

import psycopg
from psycopg.errors import RaiseException

from tests import test_space_combat_pursuit


@unittest.skipUnless(os.environ.get("BASE_CEPHEUS_DATABASE_URL"), "requires PostgreSQL")
class SpaceCombatEvasiveManeuverTests(unittest.TestCase):
    def setUp(self):
        self.helper = test_space_combat_pursuit.SpaceCombatPursuitTests()
        self.helper.setUp()

    def receipt(self, c, effect, suffix):
        campaign, engagement, ships, pilots, vessels = self.helper.fixture(c)
        round_id = c.execute("SELECT senc_open_next_round(%s)", (engagement,)).fetchone()[0]
        action = self.helper.action(c, campaign, engagement, round_id, vessels[0], pilots[0][1], None, 'evasive-maneuvers')
        task = self.helper.task(c, pilots[0][0], suffix, effect)
        return c.execute("""INSERT INTO senc_evasive_maneuver_receipt
          (engagement_id,campaign_id,space_combat_round_id,round_number,senc_vessel_id,
           action_id,pilot_assignment_id,pilot_ship_id,task_command_id,task_effect,
           task_succeeded,attack_penalty)
          VALUES(%s,%s,%s,1,%s,%s,%s,%s,%s,%s,%s,%s)
          RETURNING evasive_maneuver_receipt_id,attack_penalty""",
          (engagement, campaign, round_id, vessels[0], action, pilots[0][1], ships[0],
           task, effect, effect >= 0, -2 if effect >= 6 else (-1 if effect >= 0 else 0))).fetchone()

    def test_success_and_exceptional_success_penalties_are_immutable(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as c:
            rule = c.execute("""SELECT success_attack_penalty,exceptional_effect_threshold,
              exceptional_attack_penalty,applies_to_attacks_targeting_vessel,
              applies_current_round_only,failure_consumes_action
              FROM rule_space_combat_evasive_maneuvers""").fetchone()
            self.assertEqual(rule, (-1, 6, -2, True, True, True))
            with c.transaction(force_rollback=True):
                receipt, penalty = self.receipt(c, 2, 'ordinary')
                self.assertEqual(penalty, -1)
                with self.assertRaisesRegex(RaiseException, "immutable"):
                    with c.transaction():
                        c.execute("DELETE FROM senc_evasive_maneuver_receipt WHERE evasive_maneuver_receipt_id=%s", (receipt,))
            with c.transaction(force_rollback=True):
                self.assertEqual(self.receipt(c, 6, 'exceptional')[1], -2)

    def test_failure_spends_action_without_attack_penalty(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as c:
            with c.transaction(force_rollback=True):
                self.assertEqual(self.receipt(c, -1, 'failure')[1], 0)


if __name__ == "__main__":
    unittest.main()
