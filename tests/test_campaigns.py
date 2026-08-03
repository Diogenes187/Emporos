import os
import unittest
import uuid

import psycopg

from engine.campaigns import create_campaign_command


@unittest.skipUnless(
    os.environ.get("BASE_CEPHEUS_DATABASE_URL"), "requires PostgreSQL"
)
class CampaignCommandTests(unittest.TestCase):
    def test_campaign_creation_is_atomic_audited_and_idempotent(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                key = "test-campaign-" + str(uuid.uuid4())
                result = create_campaign_command(
                    connection,
                    initiator_reference="emporos-test",
                    idempotency_key=key,
                    name="  The Long Account  ",
                    play_mode="ai_refereed",
                    day_number=1105001,
                )
                replay = create_campaign_command(
                    connection,
                    initiator_reference="emporos-test",
                    idempotency_key=key,
                    name="ignored on replay",
                )
                self.assertEqual(result.name, "The Long Account")
                self.assertEqual(result.campaign_public_id, replay.campaign_public_id)
                self.assertTrue(replay.replayed)
                receipt = connection.execute(
                    """
                    SELECT event.event_type,clock.day_number
                      FROM cmd_campaign_creation_receipt receipt
                      JOIN cmd_domain_event event USING (command_id)
                      JOIN camp_clock clock USING (campaign_id)
                     WHERE receipt.command_id=(
                         SELECT command_id FROM cmd_command
                          WHERE public_id=%s
                     )
                    """,
                    (result.command_public_id,),
                ).fetchone()
                self.assertEqual(receipt, ("campaign_created", 1105001))

    def test_campaign_creation_rejects_invalid_inputs_before_writing(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with self.assertRaises(ValueError):
                create_campaign_command(
                    connection,
                    initiator_reference="emporos-test",
                    idempotency_key="invalid",
                    name=" ",
                )


if __name__ == "__main__":
    unittest.main()
