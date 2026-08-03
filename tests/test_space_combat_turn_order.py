import os
import unittest

import psycopg
from psycopg.errors import CheckViolation, RaiseException

from tests import test_space_combat_relational


@unittest.skipUnless(
    os.environ.get("BASE_CEPHEUS_DATABASE_URL"),
    "requires the project PostgreSQL database",
)
class SpaceCombatTurnOrderTests(unittest.TestCase):
    def setUp(self):
        self.helper = (
            test_space_combat_relational.SpaceCombatRelationalIntegrationTests()
        )

    def test_rule_and_atomic_round_order_receipts(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            rule = connection.execute(
                """SELECT higher_thrust_breaks_initiative_ties,
                          remaining_initiative_ties_simultaneous,
                          vessel_crew_acts_together,initiative_is_dynamic,
                          initiative_rerolled_each_round
                   FROM rule_space_combat_procedure
                   WHERE procedure_code='cepheus-standard'"""
            ).fetchone()
            self.assertEqual(rule, (True, True, True, True, False))

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
                       VALUES (%s,%s,'cepheus-standard')
                       RETURNING engagement_id""",
                    (encounter_id, campaign_id),
                ).fetchone()[0]
                forces = connection.execute(
                    """INSERT INTO senc_force
                       (engagement_id,campaign_id,side_code,force_name)
                       VALUES (%s,%s,'red','Red'),(%s,%s,'blue','Blue')
                       RETURNING force_id""",
                    (engagement_id, campaign_id, engagement_id, campaign_id),
                ).fetchall()
                initiatives = ((9, 1), (9, 2), (9, 2))
                vessels = []
                crews = []
                for index, (initiative, thrust) in enumerate(initiatives):
                    suffix = f"order-{index}"
                    ship_id = self.helper.ship(connection, campaign_id, suffix)
                    crews.append(self.helper.crew_assignment(
                        connection, campaign_id, ship_id, suffix
                    ))
                    vessels.append(connection.execute(
                        """INSERT INTO senc_vessel
                           (engagement_id,campaign_id,force_id,ship_id,
                            initiative_current,thrust_current,joined_round)
                           VALUES (%s,%s,%s,%s,%s,%s,1)
                           RETURNING senc_vessel_id""",
                        (engagement_id, campaign_id, forces[index % 2][0],
                         ship_id, initiative, thrust),
                    ).fetchone()[0])
                connection.execute(
                    """UPDATE senc_engagement SET engagement_status='active',
                              started_at=clock_timestamp()
                       WHERE engagement_id=%s""",
                    (engagement_id,),
                )
                round_id = connection.execute(
                    "SELECT senc_open_next_round(%s)", (engagement_id,)
                ).fetchone()[0]
                rows = connection.execute(
                    """SELECT senc_vessel_id,initiative_snapshot,
                              thrust_snapshot,turn_order_rank,
                              simultaneous_group_size
                       FROM senc_vessel_turn_order_receipt
                       WHERE space_combat_round_id=%s
                       ORDER BY turn_order_rank,senc_vessel_id""",
                    (round_id,),
                ).fetchall()
                self.assertEqual(
                    [(r[1], r[2], r[3], r[4]) for r in rows],
                    [(9, 2, 1, 2), (9, 2, 1, 2), (9, 1, 2, 1)],
                )
                with self.assertRaisesRegex(
                    (CheckViolation, RaiseException), "unfinished round"
                ):
                    with connection.transaction():
                        connection.execute(
                            "SELECT senc_open_next_round(%s)", (engagement_id,)
                        )
                with self.assertRaisesRegex(
                    (CheckViolation, RaiseException), "turn-order receipts are immutable"
                ):
                    with connection.transaction():
                        connection.execute(
                            """UPDATE senc_vessel_turn_order_receipt
                               SET initiative_snapshot=10
                               WHERE space_combat_round_id=%s
                                 AND senc_vessel_id=%s""",
                            (round_id, vessels[0]),
                        )
                with self.assertRaisesRegex(
                    (CheckViolation, RaiseException), "must match"
                ):
                    with connection.transaction():
                        connection.execute(
                            """INSERT INTO senc_crew_turn
                               (space_combat_round_id,engagement_id,campaign_id,
                                senc_vessel_id,crew_assignment_id,
                                initiative_at_action)
                               VALUES (%s,%s,%s,%s,%s,8)""",
                            (round_id, engagement_id, campaign_id,
                             vessels[0], crews[0]),
                        )


if __name__ == "__main__":
    unittest.main()
