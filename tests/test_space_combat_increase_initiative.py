import os
import unittest

import psycopg
from psycopg.errors import RaiseException

from tests import test_space_combat_relational


@unittest.skipUnless(os.environ.get("BASE_CEPHEUS_DATABASE_URL"), "requires PostgreSQL")
class SpaceCombatIncreaseInitiativeTests(unittest.TestCase):
    def setUp(self):
        self.helper = test_space_combat_relational.SpaceCombatRelationalIntegrationTests()

    def captain(self, c, campaign, ship):
        actor = c.execute("INSERT INTO actor_actor(campaign_id,name,controller_reference) VALUES(%s,'Captain','player') RETURNING actor_id", (campaign,)).fetchone()[0]
        intelligence = c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='characteristic.intelligence'").fetchone()[0]
        leadership = c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='skill.leadership'").fetchone()[0]
        c.execute("INSERT INTO actor_characteristic VALUES(%s,%s,8,8)", (actor, intelligence))
        c.execute("INSERT INTO actor_skill VALUES(%s,%s,1)", (actor, leadership))
        role = c.execute("SELECT crew_position_rule_id FROM ship_crew_position_definition WHERE position_code='master'").fetchone()[0]
        position = c.execute("INSERT INTO ship_crew_position(ship_id,campaign_id,crew_position_rule_id,position_identifier) VALUES(%s,%s,%s,'master') RETURNING ship_crew_position_id", (ship, campaign, role)).fetchone()[0]
        assignment = c.execute("INSERT INTO ship_crew_assignment(ship_crew_position_id,ship_id,campaign_id,actor_id) VALUES(%s,%s,%s,%s) RETURNING crew_assignment_id", (position, ship, campaign, actor)).fetchone()[0]
        return actor, assignment

    def leadership_task(self, c, actor, effect):
        command = c.execute("""INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key,command_status,completed_at)
          VALUES('resolve_actor_task','test','increase-initiative','completed',clock_timestamp()) RETURNING command_id""").fetchone()[0]
        characteristic = c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='characteristic.intelligence'").fetchone()[0]
        skill = c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='skill.leadership'").fetchone()[0]
        difficulty = c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='difficulty.average'").fetchone()[0]
        total = 8 + effect
        c.execute("""INSERT INTO cmd_actor_task_receipt
          (command_id,actor_id,characteristic_rule_id,skill_rule_id,difficulty_rule_id,
           skill_modifier,characteristic_modifier,difficulty_modifier,circumstance_modifier,
           species_modifier,check_total,target_number,effect,succeeded)
          VALUES(%s,%s,%s,%s,%s,1,0,0,0,0,%s,8,%s,%s)""",
          (command, actor, characteristic, skill, difficulty, total, effect, total>=8))
        return command

    def test_positive_effect_applies_only_to_following_round(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as c:
            rule = c.execute("""SELECT applies_following_round_only,
              consumes_significant_action_on_failure,minimum_initiative_modifier,
              uses_positive_effect FROM rule_space_combat_increase_initiative""").fetchone()
            self.assertEqual(rule, (True, True, 0, True))
            with c.transaction(force_rollback=True):
                campaign = self.helper.campaign(c)
                encounter_rule = c.execute("SELECT rule_id FROM rule_encounter_type WHERE encounter_type_code='starship'").fetchone()[0]
                encounter = c.execute("INSERT INTO enc_encounter(campaign_id,encounter_type_rule_id,current_mode) VALUES(%s,%s,'starship') RETURNING encounter_id", (campaign, encounter_rule)).fetchone()[0]
                engagement = c.execute("INSERT INTO senc_engagement(encounter_id,campaign_id,procedure_code) VALUES(%s,%s,'cepheus-standard') RETURNING engagement_id", (encounter, campaign)).fetchone()[0]
                forces = c.execute("INSERT INTO senc_force(engagement_id,campaign_id,side_code,force_name) VALUES(%s,%s,'a','A'),(%s,%s,'b','B') RETURNING force_id", (engagement,campaign,engagement,campaign)).fetchall()
                ships = [self.helper.ship(c,campaign,f"increase-{i}") for i in range(2)]
                captain_actor,captain_assignment = self.captain(c,campaign,ships[0])
                other_assignment = self.helper.crew_assignment(c,campaign,ships[1],"increase-other")
                vessels=[]
                for i in range(2):
                    vessels.append(c.execute("INSERT INTO senc_vessel(engagement_id,campaign_id,force_id,ship_id,initiative_current,thrust_current,joined_round) VALUES(%s,%s,%s,%s,8,2,1) RETURNING senc_vessel_id", (engagement,campaign,forces[i][0],ships[i])).fetchone()[0])
                c.execute("UPDATE senc_engagement SET engagement_status='active',started_at=clock_timestamp() WHERE engagement_id=%s",(engagement,))
                round1=c.execute("SELECT senc_open_next_round(%s)",(engagement,)).fetchone()[0]
                turn=c.execute("INSERT INTO senc_crew_turn(space_combat_round_id,engagement_id,campaign_id,senc_vessel_id,crew_assignment_id,initiative_at_action,turn_status) VALUES(%s,%s,%s,%s,%s,8,'acting') RETURNING crew_turn_id",(round1,engagement,campaign,vessels[0],captain_assignment)).fetchone()[0]
                action=c.execute("INSERT INTO senc_action(crew_turn_id,space_combat_round_id,engagement_id,campaign_id,action_order,action_code) VALUES(%s,%s,%s,%s,1,'increase-initiative') RETURNING space_combat_action_id",(turn,round1,engagement,campaign)).fetchone()[0]
                task=self.leadership_task(c,captain_actor,2)
                receipt=c.execute("""INSERT INTO senc_increase_initiative_receipt
                  (engagement_id,campaign_id,senc_vessel_id,source_round_id,source_round_number,
                   applies_round_number,action_id,captain_assignment_id,captain_ship_id,
                   task_command_id,task_effect,initiative_bonus)
                  VALUES(%s,%s,%s,%s,1,2,%s,%s,%s,%s,2,2)
                  RETURNING increase_initiative_receipt_id""",
                  (engagement,campaign,vessels[0],round1,action,captain_assignment,ships[0],task)).fetchone()[0]
                c.execute("UPDATE senc_round SET round_status='completed',ended_at=clock_timestamp() WHERE space_combat_round_id=%s",(round1,))
                round2=c.execute("SELECT senc_open_next_round(%s)",(engagement,)).fetchone()[0]
                self.assertEqual(c.execute("SELECT initiative_snapshot FROM senc_vessel_turn_order_receipt WHERE space_combat_round_id=%s AND senc_vessel_id=%s",(round2,vessels[0])).fetchone()[0],10)
                c.execute("UPDATE senc_round SET round_status='completed',ended_at=clock_timestamp() WHERE space_combat_round_id=%s",(round2,))
                round3=c.execute("SELECT senc_open_next_round(%s)",(engagement,)).fetchone()[0]
                self.assertEqual(c.execute("SELECT initiative_snapshot FROM senc_vessel_turn_order_receipt WHERE space_combat_round_id=%s AND senc_vessel_id=%s",(round3,vessels[0])).fetchone()[0],8)
                with self.assertRaisesRegex(RaiseException,"immutable"):
                    with c.transaction(): c.execute("DELETE FROM senc_increase_initiative_receipt WHERE increase_initiative_receipt_id=%s",(receipt,))


if __name__ == "__main__": unittest.main()
