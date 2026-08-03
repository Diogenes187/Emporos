import os
import unittest

import psycopg
from psycopg.errors import CheckViolation, RaiseException

from tests import test_space_combat_relational


@unittest.skipUnless(os.environ.get("BASE_CEPHEUS_DATABASE_URL"), "requires PostgreSQL")
class SpaceCombatPursuitTests(unittest.TestCase):
    def setUp(self):
        self.helper = test_space_combat_relational.SpaceCombatRelationalIntegrationTests()

    def pilot(self, c, campaign, ship, suffix):
        actor = c.execute(
            "INSERT INTO actor_actor(campaign_id,name,controller_reference) VALUES(%s,%s,'player') RETURNING actor_id",
            (campaign, f"Pilot {suffix}"),
        ).fetchone()[0]
        dexterity = c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='characteristic.dexterity'").fetchone()[0]
        piloting = c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='skill.piloting'").fetchone()[0]
        c.execute("INSERT INTO actor_characteristic VALUES(%s,%s,8,8)", (actor, dexterity))
        c.execute("INSERT INTO actor_skill VALUES(%s,%s,1)", (actor, piloting))
        role = c.execute("SELECT crew_position_rule_id FROM ship_crew_position_definition WHERE position_code='pilot'").fetchone()[0]
        position = c.execute(
            "INSERT INTO ship_crew_position(ship_id,campaign_id,crew_position_rule_id,position_identifier) VALUES(%s,%s,%s,%s) RETURNING ship_crew_position_id",
            (ship, campaign, role, f"pilot-{suffix}"),
        ).fetchone()[0]
        assignment = c.execute(
            "INSERT INTO ship_crew_assignment(ship_crew_position_id,ship_id,campaign_id,actor_id) VALUES(%s,%s,%s,%s) RETURNING crew_assignment_id",
            (position, ship, campaign, actor),
        ).fetchone()[0]
        return actor, assignment

    def task(self, c, actor, suffix, effect):
        command = c.execute(
            """INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key,command_status,completed_at)
               VALUES('resolve_actor_task','test',%s,'completed',clock_timestamp()) RETURNING command_id""",
            (f"pursuit-{suffix}",),
        ).fetchone()[0]
        characteristic = c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='characteristic.dexterity'").fetchone()[0]
        skill = c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='skill.piloting'").fetchone()[0]
        difficulty = c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='difficulty.average'").fetchone()[0]
        # The receipt trigger incorporates the trained Piloting +1 into check_total.
        total = 8 + effect
        c.execute(
            """INSERT INTO cmd_actor_task_receipt
               (command_id,actor_id,characteristic_rule_id,skill_rule_id,difficulty_rule_id,
                skill_modifier,characteristic_modifier,difficulty_modifier,circumstance_modifier,
                species_modifier,check_total,target_number,effect,succeeded)
               VALUES(%s,%s,%s,%s,%s,1,0,0,0,0,%s,8,%s,%s)""",
            (command, actor, characteristic, skill, difficulty, total, effect, total >= 8),
        )
        return command

    def fixture(self, c):
        campaign = self.helper.campaign(c)
        encounter_rule = c.execute("SELECT rule_id FROM rule_encounter_type WHERE encounter_type_code='starship'").fetchone()[0]
        encounter = c.execute("INSERT INTO enc_encounter(campaign_id,encounter_type_rule_id,current_mode) VALUES(%s,%s,'starship') RETURNING encounter_id", (campaign, encounter_rule)).fetchone()[0]
        engagement = c.execute("INSERT INTO senc_engagement(encounter_id,campaign_id,procedure_code) VALUES(%s,%s,'cepheus-standard') RETURNING engagement_id", (encounter, campaign)).fetchone()[0]
        forces = c.execute("INSERT INTO senc_force(engagement_id,campaign_id,side_code,force_name) VALUES(%s,%s,'a','A'),(%s,%s,'b','B') RETURNING force_id", (engagement, campaign, engagement, campaign)).fetchall()
        ships = [self.helper.ship(c, campaign, f"pursuit-{i}") for i in range(2)]
        pilots = [self.pilot(c, campaign, ships[i], str(i)) for i in range(2)]
        vessels = [c.execute(
            "INSERT INTO senc_vessel(engagement_id,campaign_id,force_id,ship_id,initiative_current,thrust_current,speed_current,joined_round) VALUES(%s,%s,%s,%s,%s,2,2,1) RETURNING senc_vessel_id",
            (engagement, campaign, forces[i][0], ships[i], 9-i),
        ).fetchone()[0] for i in range(2)]
        c.execute("INSERT INTO senc_vessel_range(engagement_id,campaign_id,first_vessel_id,second_vessel_id,range_band_code) VALUES(%s,%s,%s,%s,'short')", (engagement, campaign, vessels[0], vessels[1]))
        c.execute("UPDATE senc_engagement SET engagement_status='active',started_at=clock_timestamp() WHERE engagement_id=%s", (engagement,))
        return campaign, engagement, ships, pilots, vessels

    def action(self, c, campaign, engagement, round_id, vessel, assignment, target, code, order=1):
        turn = c.execute(
            "INSERT INTO senc_crew_turn(space_combat_round_id,engagement_id,campaign_id,senc_vessel_id,crew_assignment_id,initiative_at_action,turn_status) VALUES(%s,%s,%s,%s,%s,9,'acting') RETURNING crew_turn_id",
            (round_id, engagement, campaign, vessel, assignment),
        ).fetchone()[0]
        return c.execute(
            "INSERT INTO senc_action(crew_turn_id,space_combat_round_id,engagement_id,campaign_id,action_order,action_code,target_vessel_id) VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING space_combat_action_id",
            (turn, round_id, engagement, campaign, order, code, target),
        ).fetchone()[0]

    def test_establish_maintain_and_immediate_range_invalidation(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as c:
            rule = c.execute("""SELECT establishment_range_codes,equal_speed_required,
              maintenance_requires_significant_action,maintenance_requires_check,
              first_turn_attack_modifier,attack_modifier_per_later_turn,maximum_attack_modifier,
              automatic_break_speed_advantage,immediate_automatic_break,reestablishment_required_after_break
              FROM rule_space_combat_pursuit""").fetchone()
            self.assertEqual(rule, (['close', 'short'], True, True, False, 0, 1, 4, 7, True, True))
            with c.transaction(force_rollback=True):
                campaign, engagement, ships, pilots, vessels = self.fixture(c)
                round1 = c.execute("SELECT senc_open_next_round(%s)", (engagement,)).fetchone()[0]
                action1 = self.action(c, campaign, engagement, round1, vessels[0], pilots[0][1], vessels[1], 'pursuit')
                tasks = [self.task(c, pilots[0][0], 'win', 2), self.task(c, pilots[1][0], 'lose', 0)]
                pursuit = c.execute("""INSERT INTO senc_pursuit
                  (engagement_id,campaign_id,pursuing_vessel_id,target_vessel_id,pursuit_status,
                   established_round,last_maintained_round,consecutive_maintained_turns,attack_modifier)
                  VALUES(%s,%s,%s,%s,'active',1,1,1,0) RETURNING pursuit_id""",
                  (engagement, campaign, vessels[0], vessels[1])).fetchone()[0]
                receipt = c.execute("""INSERT INTO senc_pursuit_action_receipt
                  (pursuit_id,engagement_id,campaign_id,space_combat_round_id,round_number,action_kind,
                   acting_vessel_id,opposing_vessel_id,action_id,acting_task_command_id,opposing_task_command_id,
                   acting_effect,opposing_effect,acting_characteristic_value,opposing_characteristic_value,acting_won,
                   range_band_snapshot,acting_speed_snapshot,opposing_speed_snapshot,attack_modifier_before,attack_modifier_after)
                  VALUES(%s,%s,%s,%s,1,'establish',%s,%s,%s,%s,%s,2,0,8,8,true,'short',2,2,0,0)
                  RETURNING pursuit_action_receipt_id""",
                  (pursuit, engagement, campaign, round1, vessels[0], vessels[1], action1, tasks[0], tasks[1])).fetchone()[0]
                c.execute("UPDATE senc_round SET round_status='completed',ended_at=clock_timestamp() WHERE space_combat_round_id=%s", (round1,))
                round2 = c.execute("SELECT senc_open_next_round(%s)", (engagement,)).fetchone()[0]
                action2 = self.action(c, campaign, engagement, round2, vessels[0], pilots[0][1], vessels[1], 'pursuit')
                c.execute("""INSERT INTO senc_pursuit_action_receipt
                  (pursuit_id,engagement_id,campaign_id,space_combat_round_id,round_number,action_kind,
                   acting_vessel_id,opposing_vessel_id,action_id,range_band_snapshot,acting_speed_snapshot,
                   opposing_speed_snapshot,attack_modifier_before,attack_modifier_after)
                  VALUES(%s,%s,%s,%s,2,'maintain',%s,%s,%s,'short',2,2,0,1)""",
                  (pursuit, engagement, campaign, round2, vessels[0], vessels[1], action2))
                self.assertEqual(c.execute("SELECT pursuit_status,attack_modifier FROM senc_pursuit WHERE pursuit_id=%s", (pursuit,)).fetchone(), ('active', 1))
                c.execute("UPDATE senc_vessel_range SET range_band_code='medium' WHERE engagement_id=%s", (engagement,))
                self.assertEqual(c.execute("SELECT pursuit_status,attack_modifier,ended_reason FROM senc_pursuit WHERE pursuit_id=%s", (pursuit,)).fetchone(), ('broken', 0, 'range'))
                self.assertEqual(c.execute("SELECT transition_kind,reason,attack_modifier_before,attack_modifier_after FROM senc_pursuit_transition_receipt WHERE pursuit_id=%s ORDER BY pursuit_transition_receipt_id DESC LIMIT 1", (pursuit,)).fetchone(), ('broken', 'range', 1, 0))
                # A fresh opposed action is required before the other automatic
                # break condition can apply to a newly active pursuit.
                c.execute("UPDATE senc_vessel_range SET range_band_code='short' WHERE engagement_id=%s", (engagement,))
                c.execute("UPDATE senc_round SET round_status='completed',ended_at=clock_timestamp() WHERE space_combat_round_id=%s", (round2,))
                round3 = c.execute("SELECT senc_open_next_round(%s)", (engagement,)).fetchone()[0]
                action3 = self.action(c, campaign, engagement, round3, vessels[0], pilots[0][1], vessels[1], 'pursuit')
                tasks2 = [self.task(c, pilots[0][0], 'speed-win', 2), self.task(c, pilots[1][0], 'speed-lose', 0)]
                pursuit2 = c.execute("""INSERT INTO senc_pursuit
                  (engagement_id,campaign_id,pursuing_vessel_id,target_vessel_id,pursuit_status,
                   established_round,last_maintained_round,consecutive_maintained_turns,attack_modifier)
                  VALUES(%s,%s,%s,%s,'active',3,3,1,0) RETURNING pursuit_id""",
                  (engagement, campaign, vessels[0], vessels[1])).fetchone()[0]
                c.execute("""INSERT INTO senc_pursuit_action_receipt
                  (pursuit_id,engagement_id,campaign_id,space_combat_round_id,round_number,action_kind,
                   acting_vessel_id,opposing_vessel_id,action_id,acting_task_command_id,opposing_task_command_id,
                   acting_effect,opposing_effect,acting_characteristic_value,opposing_characteristic_value,acting_won,
                   range_band_snapshot,acting_speed_snapshot,opposing_speed_snapshot,attack_modifier_before,attack_modifier_after)
                  VALUES(%s,%s,%s,%s,3,'establish',%s,%s,%s,%s,%s,2,0,8,8,true,'short',2,2,0,0)""",
                  (pursuit2, engagement, campaign, round3, vessels[0], vessels[1], action3, tasks2[0], tasks2[1]))
                c.execute("UPDATE senc_vessel SET speed_current=9 WHERE senc_vessel_id=%s", (vessels[1],))
                self.assertEqual(c.execute("SELECT pursuit_status,attack_modifier,ended_reason FROM senc_pursuit WHERE pursuit_id=%s", (pursuit2,)).fetchone(), ('broken', 0, 'speed'))
                with self.assertRaisesRegex(RaiseException, "immutable"):
                    with c.transaction():
                        c.execute("DELETE FROM senc_pursuit_action_receipt WHERE pursuit_action_receipt_id=%s", (receipt,))

    def test_full_opposed_tie_requires_reroll(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as c:
            with c.transaction(force_rollback=True):
                campaign, engagement, ships, pilots, vessels = self.fixture(c)
                round1 = c.execute("SELECT senc_open_next_round(%s)", (engagement,)).fetchone()[0]
                action = self.action(c, campaign, engagement, round1, vessels[0], pilots[0][1], vessels[1], 'pursuit')
                tasks = [self.task(c, pilots[i][0], f"tie-{i}", 1) for i in range(2)]
                pursuit = c.execute("""INSERT INTO senc_pursuit
                  (engagement_id,campaign_id,pursuing_vessel_id,target_vessel_id,pursuit_status,
                   established_round,last_maintained_round,consecutive_maintained_turns,attack_modifier)
                  VALUES(%s,%s,%s,%s,'active',1,1,1,0) RETURNING pursuit_id""",
                  (engagement, campaign, vessels[0], vessels[1])).fetchone()[0]
                with self.assertRaisesRegex(CheckViolation, "tie requires reroll"):
                    with c.transaction():
                        c.execute("""INSERT INTO senc_pursuit_action_receipt
                          (pursuit_id,engagement_id,campaign_id,space_combat_round_id,round_number,action_kind,
                           acting_vessel_id,opposing_vessel_id,action_id,acting_task_command_id,opposing_task_command_id,
                           acting_effect,opposing_effect,acting_characteristic_value,opposing_characteristic_value,acting_won,
                           range_band_snapshot,acting_speed_snapshot,opposing_speed_snapshot,attack_modifier_before,attack_modifier_after)
                          VALUES(%s,%s,%s,%s,1,'establish',%s,%s,%s,%s,%s,1,1,8,8,false,'short',2,2,0,0)""",
                          (pursuit, engagement, campaign, round1, vessels[0], vessels[1], action, tasks[0], tasks[1]))


if __name__ == "__main__":
    unittest.main()
