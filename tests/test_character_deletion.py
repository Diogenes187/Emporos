import os
import unittest
import uuid

import psycopg

from engine.campaigns import create_campaign_command
from engine.character_creation import initialize_character_command
from engine.character_deletion import delete_character_command


@unittest.skipUnless(
    os.environ.get("BASE_CEPHEUS_DATABASE_URL"), "requires PostgreSQL"
)
class CharacterDeletionTests(unittest.TestCase):
    def test_deletion_removes_character_from_play_and_replays(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                suffix = str(uuid.uuid4())
                campaign = create_campaign_command(
                    connection,
                    initiator_reference="delete-test",
                    idempotency_key="campaign-" + suffix,
                    name="Deletion Test",
                )
                actor = initialize_character_command(
                    connection,
                    initiator_reference="delete-test",
                    idempotency_key="actor-" + suffix,
                    campaign_public_id=campaign.campaign_public_id,
                    character_name="Temporary Traveller",
                )

                command_id = delete_character_command(
                    connection,
                    initiator_reference="delete-test",
                    idempotency_key="delete-" + suffix,
                    actor_public_id=actor.actor_public_id,
                )
                replay_id = delete_character_command(
                    connection,
                    initiator_reference="delete-test",
                    idempotency_key="delete-" + suffix,
                    actor_public_id=actor.actor_public_id,
                )

                self.assertEqual(command_id, replay_id)
                lifecycle_status = connection.execute(
                    "SELECT lifecycle_status FROM actor_actor WHERE public_id=%s",
                    (actor.actor_public_id,),
                ).fetchone()[0]
                self.assertEqual(lifecycle_status, "deleted")
                active_controllers = connection.execute(
                    """SELECT count(*) FROM iam_character_controller controller
                       JOIN actor_actor actor USING(actor_id)
                       WHERE actor.public_id=%s
                         AND controller.controller_status='active'""",
                    (actor.actor_public_id,),
                ).fetchone()[0]
                self.assertEqual(active_controllers, 0)


if __name__ == "__main__":
    unittest.main()
