import os
import unittest

import psycopg
from psycopg.errors import RaiseException

from tests import test_space_combat_relational


@unittest.skipUnless(os.environ.get("BASE_CEPHEUS_DATABASE_URL"), "requires PostgreSQL")
class SpaceCombatRangeCheckTests(unittest.TestCase):
    def setUp(self):
        self.helper = test_space_combat_relational.SpaceCombatRelationalIntegrationTests()

    def navigator(self, c, campaign, ship, suffix):
        actor = c.execute(
            "INSERT INTO actor_actor(campaign_id,name,controller_reference) VALUES(%s,%s,'player') RETURNING actor_id",
            (campaign, f"Navigator {suffix}"),
        ).fetchone()[0]
        edu = c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='characteristic.education'").fetchone()[0]
        c.execute("INSERT INTO actor_characteristic VALUES(%s,%s,8,8)", (actor, edu))
        navigation = c.execute(
            "SELECT rule_id FROM rule_rule WHERE rule_code='skill.navigation'"
        ).fetchone()[0]
        c.execute(
            "INSERT INTO actor_skill(actor_id,skill_rule_id,skill_level) VALUES(%s,%s,0)",
            (actor, navigation),
        )
        role = c.execute("SELECT crew_position_rule_id FROM ship_crew_position_definition WHERE position_code='navigator'").fetchone()[0]
        position = c.execute(
            "INSERT INTO ship_crew_position(ship_id,campaign_id,crew_position_rule_id,position_identifier) VALUES(%s,%s,%s,%s) RETURNING ship_crew_position_id",
            (ship, campaign, role, f"navigator-{suffix}"),
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
            (f"range-{suffix}",),
        ).fetchone()[0]
        characteristic = c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='characteristic.education'").fetchone()[0]
        skill = c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='skill.navigation'").fetchone()[0]
        difficulty = c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='difficulty.average'").fetchone()[0]
        total = 8 + effect
        c.execute(
            """INSERT INTO cmd_actor_task_receipt
               (command_id,actor_id,characteristic_rule_id,skill_rule_id,difficulty_rule_id,
                skill_modifier,characteristic_modifier,difficulty_modifier,circumstance_modifier,
                species_modifier,check_total,target_number,effect,succeeded)
               VALUES(%s,%s,%s,%s,%s,0,0,0,0,0,%s,8,%s,%s)""",
            (command, actor, characteristic, skill, difficulty, total, effect, total >= 8),
        )
        return command

    def test_opposed_check_changes_one_band_and_is_immutable(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as c:
            with c.transaction(force_rollback=True):
                campaign = self.helper.campaign(c)
                encounter_rule = c.execute("SELECT rule_id FROM rule_encounter_type WHERE encounter_type_code='starship'").fetchone()[0]
                encounter = c.execute("INSERT INTO enc_encounter(campaign_id,encounter_type_rule_id,current_mode) VALUES(%s,%s,'starship') RETURNING encounter_id", (campaign, encounter_rule)).fetchone()[0]
                engagement = c.execute("INSERT INTO senc_engagement(encounter_id,campaign_id,procedure_code) VALUES(%s,%s,'cepheus-standard') RETURNING engagement_id", (encounter, campaign)).fetchone()[0]
                forces = c.execute("INSERT INTO senc_force(engagement_id,campaign_id,side_code,force_name) VALUES(%s,%s,'a','A'),(%s,%s,'b','B') RETURNING force_id", (engagement, campaign, engagement, campaign)).fetchall()
                ships = [self.helper.ship(c, campaign, f"range-{i}") for i in range(2)]
                crew = [self.navigator(c, campaign, ships[i], str(i)) for i in range(2)]
                vessels = []
                for i in range(2):
                    vessels.append(c.execute("INSERT INTO senc_vessel(engagement_id,campaign_id,force_id,ship_id,initiative_current,thrust_current,joined_round) VALUES(%s,%s,%s,%s,%s,2,1) RETURNING senc_vessel_id", (engagement, campaign, forces[i][0], ships[i], 9-i)).fetchone()[0])
                c.execute("INSERT INTO senc_vessel_range(engagement_id,campaign_id,first_vessel_id,second_vessel_id,range_band_code) VALUES(%s,%s,%s,%s,'short')", (engagement, campaign, vessels[0], vessels[1]))
                c.execute("UPDATE senc_engagement SET engagement_status='active',started_at=clock_timestamp() WHERE engagement_id=%s", (engagement,))
                round_id = c.execute("SELECT senc_open_next_round(%s)", (engagement,)).fetchone()[0]
                actions = []
                for i in range(2):
                    turn = c.execute("INSERT INTO senc_crew_turn(space_combat_round_id,engagement_id,campaign_id,senc_vessel_id,crew_assignment_id,initiative_at_action,turn_status) VALUES(%s,%s,%s,%s,%s,%s,'acting') RETURNING crew_turn_id", (round_id, engagement, campaign, vessels[i], crew[i][1], 9-i)).fetchone()[0]
                    actions.append(c.execute("INSERT INTO senc_action(crew_turn_id,space_combat_round_id,engagement_id,campaign_id,action_order,action_code,target_vessel_id) VALUES(%s,%s,%s,%s,1,'range-check',%s) RETURNING space_combat_action_id", (turn, round_id, engagement, campaign, vessels[1-i])).fetchone()[0])
                tasks = [self.task(c, crew[0][0], 'a', 2), self.task(c, crew[1][0], 'b', 0)]
                receipt = c.execute(
                    """INSERT INTO senc_range_check_receipt
                       (engagement_id,campaign_id,space_combat_round_id,first_vessel_id,second_vessel_id,
                        first_action_id,second_action_id,first_task_command_id,second_task_command_id,
                        first_effect,second_effect,first_characteristic_value,second_characteristic_value,
                        winning_vessel_id,resolution_status,elected_change,range_band_before,range_band_after,
                        range_version_before,range_version_after)
                       VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,2,0,8,8,%s,'resolved','increase','short','medium',1,2)
                       RETURNING range_check_receipt_id""",
                    (engagement, campaign, round_id, vessels[0], vessels[1], actions[0], actions[1], tasks[0], tasks[1], vessels[0]),
                ).fetchone()[0]
                self.assertEqual(c.execute("SELECT range_band_code,range_version FROM senc_vessel_range WHERE engagement_id=%s", (engagement,)).fetchone(), ('medium', 2))
                with self.assertRaisesRegex(RaiseException, "immutable"):
                    with c.transaction():
                        c.execute("DELETE FROM senc_range_check_receipt WHERE range_check_receipt_id=%s", (receipt,))


if __name__ == "__main__":
    unittest.main()
