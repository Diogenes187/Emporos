import os
import unittest

import psycopg
from psycopg.errors import CheckViolation, RaiseException

from tests import test_space_combat_pursuit


@unittest.skipUnless(os.environ.get("BASE_CEPHEUS_DATABASE_URL"), "requires PostgreSQL")
class SpaceCombatDockingTests(unittest.TestCase):
    def setUp(self):
        self.helper = test_space_combat_pursuit.SpaceCombatPursuitTests()
        self.helper.setUp()

    def task(self, c, actor, suffix, effect, circumstance):
        command = c.execute(
            """INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key,command_status,completed_at)
               VALUES('resolve_actor_task','test',%s,'completed',clock_timestamp()) RETURNING command_id""",
            (f"docking-{suffix}",),
        ).fetchone()[0]
        characteristic = c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='characteristic.dexterity'").fetchone()[0]
        skill = c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='skill.piloting'").fetchone()[0]
        difficulty = c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='difficulty.average'").fetchone()[0]
        c.execute(
            """INSERT INTO cmd_actor_task_receipt
               (command_id,actor_id,characteristic_rule_id,skill_rule_id,difficulty_rule_id,
                skill_modifier,characteristic_modifier,difficulty_modifier,circumstance_modifier,
                species_modifier,check_total,target_number,effect,succeeded)
               VALUES(%s,%s,%s,%s,%s,1,0,0,%s,0,%s,8,%s,%s)""",
            (command, actor, characteristic, skill, difficulty, circumstance, 8 + effect, effect, effect >= 0),
        )
        return command

    def setup_attempt(self, c):
        campaign, engagement, ships, pilots, vessels = self.helper.fixture(c)
        c.execute("UPDATE senc_vessel_range SET range_band_code='adjacent' WHERE engagement_id=%s", (engagement,))
        round_id = c.execute("SELECT senc_open_next_round(%s)", (engagement,)).fetchone()[0]
        action = self.helper.action(c, campaign, engagement, round_id, vessels[0], pilots[0][1], vessels[1], 'dock')
        return campaign, engagement, ships, pilots, vessels, round_id, action

    def test_unresisted_success_atomically_establishes_docked_range(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as c:
            rule = c.execute("""SELECT resisted_docking_modifier,required_start_range_code,
              success_range_code,opposed_tie_uses_characteristic,full_tie_requires_reroll,
              success_allows_boarding FROM rule_space_combat_docking""").fetchone()
            self.assertEqual(rule, (-2, 'adjacent', 'docked', True, True, True))
            with c.transaction(force_rollback=True):
                campaign, engagement, ships, pilots, vessels, round_id, action = self.setup_attempt(c)
                task = self.task(c, pilots[0][0], 'unresisted', 1, 0)
                receipt = c.execute("""INSERT INTO senc_docking_receipt
                  (engagement_id,campaign_id,space_combat_round_id,round_number,docking_vessel_id,
                   target_vessel_id,action_id,docking_pilot_assignment_id,docking_pilot_ship_id,
                   resisted,docking_task_command_id,docking_effect,docking_characteristic_value,
                   resolution_status,range_band_before,range_band_after,range_version_before,range_version_after)
                  VALUES(%s,%s,%s,1,%s,%s,%s,%s,%s,false,%s,1,8,
                   'succeeded','adjacent','docked',1,2) RETURNING docking_receipt_id""",
                  (engagement, campaign, round_id, vessels[0], vessels[1], action,
                   pilots[0][1], ships[0], task)).fetchone()[0]
                self.assertEqual(c.execute("SELECT range_band_code,range_version FROM senc_vessel_range WHERE engagement_id=%s", (engagement,)).fetchone(), ('docked', 2))
                with self.assertRaisesRegex(RaiseException, 'immutable'):
                    with c.transaction():
                        c.execute("DELETE FROM senc_docking_receipt WHERE docking_receipt_id=%s", (receipt,))

    def test_resisted_docking_enforces_penalty_and_full_tie_reroll(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as c:
            with c.transaction(force_rollback=True):
                campaign, engagement, ships, pilots, vessels, round_id, action = self.setup_attempt(c)
                docking_task = self.task(c, pilots[0][0], 'resisted-a', 1, -2)
                opposing_task = self.task(c, pilots[1][0], 'resisted-b', 1, 0)
                c.execute("""INSERT INTO senc_docking_receipt
                  (engagement_id,campaign_id,space_combat_round_id,round_number,docking_vessel_id,
                   target_vessel_id,action_id,docking_pilot_assignment_id,docking_pilot_ship_id,
                   resisted,docking_task_command_id,opposing_task_command_id,docking_effect,opposing_effect,
                   docking_characteristic_value,opposing_characteristic_value,resolution_status,
                   range_band_before,range_band_after,range_version_before,range_version_after)
                  VALUES(%s,%s,%s,1,%s,%s,%s,%s,%s,true,%s,%s,1,1,8,8,
                   'reroll-required','adjacent','adjacent',1,1)""",
                  (engagement, campaign, round_id, vessels[0], vessels[1], action,
                   pilots[0][1], ships[0], docking_task, opposing_task))
                self.assertEqual(c.execute("SELECT range_band_code,range_version FROM senc_vessel_range WHERE engagement_id=%s", (engagement,)).fetchone(), ('adjacent', 1))

    def test_close_range_attempt_is_rejected(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as c:
            with c.transaction(force_rollback=True):
                campaign, engagement, ships, pilots, vessels, round_id, action = self.setup_attempt(c)
                c.execute("UPDATE senc_vessel_range SET range_band_code='close' WHERE engagement_id=%s", (engagement,))
                task = self.task(c, pilots[0][0], 'too-far', 1, 0)
                with self.assertRaisesRegex(CheckViolation, 'adjacent'):
                    with c.transaction():
                        c.execute("""INSERT INTO senc_docking_receipt
                          (engagement_id,campaign_id,space_combat_round_id,round_number,docking_vessel_id,
                           target_vessel_id,action_id,docking_pilot_assignment_id,docking_pilot_ship_id,
                           resisted,docking_task_command_id,docking_effect,docking_characteristic_value,
                           resolution_status,range_band_before,range_band_after,range_version_before,range_version_after)
                          VALUES(%s,%s,%s,1,%s,%s,%s,%s,%s,false,%s,1,8,
                           'succeeded','adjacent','docked',1,2)""",
                          (engagement, campaign, round_id, vessels[0], vessels[1], action,
                           pilots[0][1], ships[0], task))


if __name__ == '__main__':
    unittest.main()
