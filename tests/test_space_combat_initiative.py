import os
import unittest

import psycopg
from psycopg.errors import CheckViolation, RaiseException

from tests import test_space_combat_relational


@unittest.skipUnless(
    os.environ.get("BASE_CEPHEUS_DATABASE_URL"),
    "requires the project PostgreSQL database",
)
class SpaceCombatInitiativeTests(unittest.TestCase):
    def setUp(self):
        self.helper = (
            test_space_combat_relational.SpaceCombatRelationalIntegrationTests()
        )

    def crew(self, connection, campaign_id, ship_id, role, suffix, dexterity=None):
        actor_id = connection.execute(
            """INSERT INTO actor_actor(campaign_id,name,controller_reference)
               VALUES (%s,%s,'player') RETURNING actor_id""",
            (campaign_id, f"{role.title()} {suffix}"),
        ).fetchone()[0]
        if dexterity is not None:
            dex_rule = connection.execute(
                "SELECT rule_id FROM rule_rule WHERE rule_code='characteristic.dexterity'"
            ).fetchone()[0]
            connection.execute(
                """INSERT INTO actor_characteristic
                   (actor_id,characteristic_rule_id,maximum_value,current_value)
                   VALUES (%s,%s,%s,%s)""",
                (actor_id, dex_rule, dexterity, dexterity),
            )
        position_rule = connection.execute(
            """SELECT crew_position_rule_id
               FROM ship_crew_position_definition WHERE position_code=%s""",
            (role,),
        ).fetchone()[0]
        position_id = connection.execute(
            """INSERT INTO ship_crew_position
               (ship_id,campaign_id,crew_position_rule_id,position_identifier)
               VALUES (%s,%s,%s,%s) RETURNING ship_crew_position_id""",
            (ship_id, campaign_id, position_rule, f"{role}-{suffix}"),
        ).fetchone()[0]
        return connection.execute(
            """INSERT INTO ship_crew_assignment
               (ship_crew_position_id,ship_id,campaign_id,actor_id)
               VALUES (%s,%s,%s,%s) RETURNING crew_assignment_id""",
            (position_id, ship_id, campaign_id, actor_id),
        ).fetchone()[0]

    def test_adjudicated_rule_has_paired_provenance(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            rule = connection.execute(
                """SELECT dice_count,die_sides,awareness_fixed_total,
                          awareness_uses_pilot_dexterity,
                          compare_highest_hostile_thrust,higher_thrust_modifier,
                          vessel_tactics_scope,fleet_tactics_scope,
                          tactics_scopes_stack
                   FROM rule_space_combat_initiative"""
            ).fetchone()
            self.assertEqual(rule, (2, 6, 12, True, True, 1, True, True, False))
            provenance = connection.execute(
                """SELECT work.work_code
                   FROM rule_rule rule
                   JOIN src_record_provenance provenance USING(rule_id)
                   JOIN src_locator locator USING(source_locator_id)
                   JOIN src_work work USING(source_work_id)
                   WHERE rule.rule_code='combat.space.initiative'
                   ORDER BY work.work_code"""
            ).fetchall()
            self.assertEqual(provenance, [
                ("cepheus-engine.github-v9.1",), ("cepheus-engine.ogn",)
            ])

    def test_awareness_and_hostile_thrust_receipts(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                campaign_id = self.helper.campaign(connection)
                encounter_rule = connection.execute(
                    """SELECT rule_id FROM rule_encounter_type
                       WHERE encounter_type_code='starship'"""
                ).fetchone()[0]
                encounter_id = connection.execute(
                    """INSERT INTO enc_encounter
                       (campaign_id,encounter_type_rule_id,current_mode)
                       VALUES (%s,%s,'starship') RETURNING encounter_id""",
                    (campaign_id, encounter_rule),
                ).fetchone()[0]
                engagement_id = connection.execute(
                    """INSERT INTO senc_engagement
                       (encounter_id,campaign_id,procedure_code)
                       VALUES (%s,%s,'cepheus-standard') RETURNING engagement_id""",
                    (encounter_id, campaign_id),
                ).fetchone()[0]
                forces = connection.execute(
                    """INSERT INTO senc_force
                       (engagement_id,campaign_id,side_code,force_name)
                       VALUES (%s,%s,'red','Red'),(%s,%s,'blue','Blue')
                       RETURNING force_id""",
                    (engagement_id, campaign_id, engagement_id, campaign_id),
                ).fetchall()
                fast_ship = self.helper.ship(connection, campaign_id, "initiative-fast")
                slow_ship = self.helper.ship(connection, campaign_id, "initiative-slow")
                pilot = self.crew(connection, campaign_id, fast_ship, "pilot", "fast", 9)
                fast_vessel = connection.execute(
                    """INSERT INTO senc_vessel
                       (engagement_id,campaign_id,force_id,ship_id,
                        thrust_current,joined_round)
                       VALUES (%s,%s,%s,%s,3,1) RETURNING senc_vessel_id""",
                    (engagement_id, campaign_id, forces[0][0], fast_ship),
                ).fetchone()[0]
                slow_vessel = connection.execute(
                    """INSERT INTO senc_vessel
                       (engagement_id,campaign_id,force_id,ship_id,
                        thrust_current,joined_round)
                       VALUES (%s,%s,%s,%s,2,1) RETURNING senc_vessel_id""",
                    (engagement_id, campaign_id, forces[1][0], slow_ship),
                ).fetchone()[0]
                fast_receipt = connection.execute(
                    """INSERT INTO senc_vessel_initiative_receipt
                       (engagement_id,campaign_id,senc_vessel_id,force_id,ship_id,
                        aware_at_start,base_total,pilot_assignment_id,
                        pilot_dexterity_value,pilot_dexterity_modifier,
                        vessel_thrust_snapshot,highest_hostile_thrust_snapshot,
                        higher_thrust_modifier,tactics_effect,initiative_total)
                       VALUES (%s,%s,%s,%s,%s,true,12,%s,9,1,3,2,1,0,14)
                       RETURNING vessel_initiative_receipt_id""",
                    (engagement_id, campaign_id, fast_vessel, forces[0][0],
                     fast_ship, pilot),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO senc_vessel_initiative_receipt
                       (engagement_id,campaign_id,senc_vessel_id,force_id,ship_id,
                        aware_at_start,die_one,die_two,base_total,
                        pilot_dexterity_modifier,vessel_thrust_snapshot,
                        highest_hostile_thrust_snapshot,higher_thrust_modifier,
                        tactics_effect,initiative_total)
                       VALUES (%s,%s,%s,%s,%s,false,3,4,7,0,2,3,0,0,7)""",
                    (engagement_id, campaign_id, slow_vessel, forces[1][0], slow_ship),
                )
                totals = connection.execute(
                    """SELECT senc_vessel_id,initiative_current FROM senc_vessel
                       WHERE engagement_id=%s ORDER BY senc_vessel_id""",
                    (engagement_id,),
                ).fetchall()
                self.assertEqual(totals, [(fast_vessel, 14), (slow_vessel, 7)])
                with self.assertRaisesRegex(
                    (CheckViolation, RaiseException), "receipts are immutable"
                ):
                    with connection.transaction():
                        connection.execute(
                            """DELETE FROM senc_vessel_initiative_receipt
                               WHERE vessel_initiative_receipt_id=%s""",
                            (fast_receipt,),
                        )


if __name__ == "__main__":
    unittest.main()
