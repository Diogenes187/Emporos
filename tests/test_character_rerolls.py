import os
import unittest
import uuid

import psycopg

from engine.campaigns import create_campaign_command
from engine.character_creation import initialize_character_command
from engine.character_rerolls import reroll_characteristics_command


class FixedRandom:
    def __init__(self, value):
        self.value = value

    def randint(self, lower, upper):
        return min(self.value, upper)


@unittest.skipUnless(
    os.environ.get("BASE_CEPHEUS_DATABASE_URL"), "requires PostgreSQL"
)
class CharacteristicRerollTests(unittest.TestCase):
    def test_precareer_reroll_replaces_all_scores_and_replays(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                suffix = str(uuid.uuid4())
                campaign = create_campaign_command(
                    connection, initiator_reference="reroll-test",
                    idempotency_key="campaign-" + suffix, name="Reroll Test",
                )
                actor = initialize_character_command(
                    connection, initiator_reference="reroll-test",
                    idempotency_key="actor-" + suffix,
                    campaign_public_id=campaign.campaign_public_id,
                    character_name="Unnamed Traveller",
                    random_source=FixedRandom(1),
                )
                result = reroll_characteristics_command(
                    connection, initiator_reference="reroll-test",
                    idempotency_key="reroll-" + suffix,
                    actor_public_id=actor.actor_public_id,
                    random_source=FixedRandom(6),
                )
                self.assertEqual(len(result.scores), 6)
                self.assertTrue(all(score[1:] == (2, 12) for score in result.scores))
                replay = reroll_characteristics_command(
                    connection, initiator_reference="reroll-test",
                    idempotency_key="reroll-" + suffix,
                    actor_public_id=actor.actor_public_id,
                    random_source=FixedRandom(1),
                )
                self.assertTrue(replay.replayed)
                self.assertEqual(result.scores, replay.scores)


if __name__ == "__main__":
    unittest.main()
