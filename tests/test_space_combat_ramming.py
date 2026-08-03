import os
import unittest

import psycopg
from psycopg.errors import CheckViolation, RaiseException

from tests import test_space_combat_pursuit


@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'), 'requires PostgreSQL')
class SpaceCombatRammingTests(unittest.TestCase):
    def setUp(self):
        self.helper = test_space_combat_pursuit.SpaceCombatPursuitTests()
        self.helper.setUp()

    def fixture(self, c, effects=(2, 0), characteristics=(8, 8)):
        campaign, engagement, ships, pilots, vessels = self.helper.fixture(c)
        c.execute("UPDATE senc_vessel_range SET range_band_code='close' WHERE engagement_id=%s", (engagement,))
        c.execute("UPDATE senc_vessel SET speed_current=4 WHERE senc_vessel_id=%s", (vessels[0],))
        round_id = c.execute('SELECT senc_open_next_round(%s)', (engagement,)).fetchone()[0]
        action = self.helper.action(c, campaign, engagement, round_id, vessels[0], pilots[0][1], vessels[1], 'ram')
        tasks = [self.helper.task(c, pilots[i][0], f'ram-{i}-{effects[i]}', effects[i]) for i in range(2)]
        status = ('succeeded' if effects[0] > effects[1] else
                  'failed' if effects[0] < effects[1] else
                  'succeeded' if characteristics[0] > characteristics[1] else
                  'failed' if characteristics[0] < characteristics[1] else 'reroll-required')
        attempt = c.execute("""INSERT INTO senc_ram_attempt_receipt
          (engagement_id,campaign_id,space_combat_round_id,round_number,ramming_vessel_id,target_vessel_id,
           action_id,ramming_task_command_id,target_task_command_id,ramming_effect,target_effect,
           ramming_characteristic_value,target_characteristic_value,resolution_status,range_band_snapshot,
           ramming_speed_snapshot,target_speed_snapshot,speed_difference)
          VALUES(%s,%s,%s,1,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'close',4,2,2)
          RETURNING ram_attempt_receipt_id""",
          (engagement, campaign, round_id, vessels[0], vessels[1], action, tasks[0], tasks[1],
           effects[0], effects[1], characteristics[0], characteristics[1], status)).fetchone()[0]
        return campaign, ships, vessels, attempt, status

    def test_success_uses_one_roll_and_damages_both_vessels(self):
        with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
            rule = c.execute("""SELECT required_range_code,rammer_must_be_faster,damage_dice_per_speed_difference,
              damage_die_sides,full_tie_requires_reroll,shared_damage_roll,damage_applies_to_both_vessels,
              armor_applies_independently FROM rule_space_combat_ram""").fetchone()
            self.assertEqual(rule, ('close', True, 1, 6, True, True, True, True))
            with c.transaction(force_rollback=True):
                campaign, ships, vessels, attempt, status = self.fixture(c)
                self.assertEqual(status, 'succeeded')
                c.execute("INSERT INTO senc_ram_damage_die VALUES(%s,1,3),(%s,2,4)", (attempt, attempt))
                c.execute("""INSERT INTO senc_ram_final_receipt
                  (ram_attempt_receipt_id,rolled_damage,rammer_ship_id,target_ship_id,
                   rammer_armor_snapshot,target_armor_snapshot,rammer_net_damage,target_net_damage,
                   rammer_hull_before,rammer_hull_after,rammer_structure_before,rammer_structure_after,
                   target_hull_before,target_hull_after,target_structure_before,target_structure_after,
                   rammer_version_before,rammer_version_after,target_version_before,target_version_after)
                  VALUES(%s,7,%s,%s,0,0,7,7,4,0,4,1,4,0,4,1,1,2,1,2)""", (attempt, ships[0], ships[1]))
                states = c.execute("SELECT hull_current,structure_current,concurrency_version FROM ship_ship WHERE ship_id=ANY(%s) ORDER BY ship_id", (ships,)).fetchall()
                self.assertEqual(states, [(0, 1, 2), (0, 1, 2)])
                allocations = c.execute("SELECT affected_vessel,damage_kind,damage_points FROM senc_ram_damage_allocation WHERE ram_attempt_receipt_id=%s ORDER BY affected_vessel,damage_kind", (attempt,)).fetchall()
                self.assertEqual(allocations, [('rammer', 'hull', 4), ('rammer', 'structure', 3), ('target', 'hull', 4), ('target', 'structure', 3)])
                with self.assertRaisesRegex(CheckViolation, 'unfinalized'):
                    with c.transaction():
                        c.execute('INSERT INTO senc_ram_damage_die VALUES(%s,3,6)', (attempt,))
                with self.assertRaisesRegex(RaiseException, 'immutable'):
                    with c.transaction():
                        c.execute('DELETE FROM senc_ram_damage_die WHERE ram_attempt_receipt_id=%s', (attempt,))

    def test_full_tie_has_no_dice_or_damage(self):
        with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
            with c.transaction(force_rollback=True):
                campaign, ships, vessels, attempt, status = self.fixture(c, effects=(1, 1))
                self.assertEqual(status, 'reroll-required')
                c.execute("""INSERT INTO senc_ram_final_receipt
                  (ram_attempt_receipt_id,rolled_damage,rammer_ship_id,target_ship_id,
                   rammer_armor_snapshot,target_armor_snapshot,rammer_net_damage,target_net_damage,
                   rammer_hull_before,rammer_hull_after,rammer_structure_before,rammer_structure_after,
                   target_hull_before,target_hull_after,target_structure_before,target_structure_after,
                   rammer_version_before,rammer_version_after,target_version_before,target_version_after)
                  VALUES(%s,0,%s,%s,0,0,0,0,4,4,4,4,4,4,4,4,1,2,1,2)""", (attempt, ships[0], ships[1]))
                self.assertEqual(c.execute('SELECT count(*) FROM senc_ram_damage_allocation WHERE ram_attempt_receipt_id=%s', (attempt,)).fetchone()[0], 0)


if __name__ == '__main__':
    unittest.main()
