import os
import unittest
import uuid

import psycopg

from engine.liaison import resolve_liaison_negotiation_command


class FixedRandom:
    def __init__(self, values):
        self.values = iter(values)

    def randint(self, minimum, maximum):
        return next(self.values)


@unittest.skipUnless(os.environ.get("BASE_CEPHEUS_DATABASE_URL"), "requires PostgreSQL")
class LiaisonNegotiationTests(unittest.TestCase):
    def actors(self, connection):
        campaign_id = connection.execute(
            """INSERT INTO camp_campaign(name,owner_reference)
               VALUES (%s,'ref') RETURNING campaign_id""",
            (str(uuid.uuid4()),),
        ).fetchone()[0]
        actors = []
        for order, level in enumerate((1, 0)):
            actor_id, public_id = connection.execute(
                """INSERT INTO actor_actor
                   (campaign_id,name,controller_reference)
                   VALUES (%s,%s,%s) RETURNING actor_id,public_id""",
                (campaign_id, f"Diplomat {order}", f"player-{order}"),
            ).fetchone()
            connection.execute(
                """INSERT INTO actor_characteristic
                   (actor_id,characteristic_rule_id,maximum_value,current_value)
                   SELECT %s,rule_id,7,7 FROM rule_rule
                   WHERE rule_code='characteristic.social-standing'""",
                (actor_id,),
            )
            connection.execute(
                """INSERT INTO actor_skill(actor_id,skill_rule_id,skill_level)
                   SELECT %s,rule_id,%s FROM rule_rule
                   WHERE rule_code='skill.liaison'""",
                (actor_id, level),
            )
            actors.append(str(public_id))
        return actors

    @staticmethod
    def participants(actors):
        return [{
            "actor_public_id": actor,
            "characteristic_rule_code": "characteristic.social-standing",
        } for actor in actors]

    def test_highest_actor_derived_liaison_total_gains_advantage_and_replays(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                actors = self.actors(connection)
                result = resolve_liaison_negotiation_command(
                    connection, referee_reference="ref",
                    idempotency_key="ducal-tariff",
                    scene_reference="ducal-audience",
                    subject_reference="tariff-concession",
                    participants=self.participants(actors),
                    random_source=FixedRandom((4, 4, 3, 3)),
                )
                self.assertEqual(result.status, "resolved")
                self.assertEqual(result.winner_actor_public_id, actors[0])
                self.assertEqual(result.winning_total, 9)
                self.assertEqual(
                    [p.gained_advantage for p in result.participants],
                    [True, False],
                )
                replay = resolve_liaison_negotiation_command(
                    connection, referee_reference="ref",
                    idempotency_key="ducal-tariff",
                    scene_reference="changed", subject_reference="changed",
                    participants=self.participants(actors),
                    random_source=FixedRandom((1, 1, 6, 6)),
                )
                self.assertTrue(replay.replayed)
                self.assertEqual(replay.command_public_id, result.command_public_id)
                with self.assertRaises(psycopg.Error):
                    with connection.transaction():
                        connection.execute(
                            """UPDATE cmd_liaison_negotiation_participant
                               SET check_total=99 WHERE command_id=(
                                SELECT command_id FROM cmd_command
                                WHERE initiator_reference='ref'
                                  AND idempotency_key='ducal-tariff')""")

    def test_equal_highest_totals_remain_unresolved(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                actors = self.actors(connection)
                result = resolve_liaison_negotiation_command(
                    connection, referee_reference="ref",
                    idempotency_key="border-dispute",
                    scene_reference="neutral-station",
                    subject_reference="border-dispute",
                    participants=self.participants(actors),
                    random_source=FixedRandom((3, 3, 3, 4)),
                )
                self.assertEqual(result.status, "tied")
                self.assertIsNone(result.winner_actor_public_id)
                self.assertFalse(any(
                    participant.gained_advantage
                    for participant in result.participants))
