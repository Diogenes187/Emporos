import os
import unittest
import uuid

import psycopg

from engine.campaigns import create_campaign_command
from engine.external_referee import (
    complete_external_referee_turn_command,
    submit_external_referee_turn_command,
)


@unittest.skipUnless(
    os.environ.get("BASE_CEPHEUS_DATABASE_URL"), "requires PostgreSQL"
)
class ExternalRefereeVisibilityTests(unittest.TestCase):
    def test_pending_player_action_is_visible_until_mcp_referee_completes_it(self):
        dsn = os.environ["BASE_CEPHEUS_DATABASE_URL"]
        with psycopg.connect(dsn) as connection:
            with connection.transaction(force_rollback=True):
                owner = "external-referee-" + str(uuid.uuid4())
                campaign = create_campaign_command(
                    connection,
                    initiator_reference=owner,
                    idempotency_key="campaign-" + str(uuid.uuid4()),
                    name="External Referee",
                    play_mode="ai_refereed",
                )
                pending = submit_external_referee_turn_command(
                    connection,
                    initiator_reference=owner,
                    idempotency_key="submit-" + str(uuid.uuid4()),
                    campaign_public_id=campaign.campaign_public_id,
                    player_text="I look around.",
                )
                visible = connection.execute(
                    """SELECT message.speaker_kind,message.message_text,
                              turn.turn_status
                       FROM camp_referee_message message
                       JOIN camp_referee_turn turn
                         USING(referee_turn_id,campaign_id)
                       WHERE turn.public_id=%s""",
                    (pending.turn_public_id,),
                ).fetchall()
                self.assertEqual(visible, [("player", "I look around.", "pending")])
                complete_external_referee_turn_command(
                    connection,
                    initiator_reference=owner,
                    idempotency_key="complete-" + str(uuid.uuid4()),
                    turn_public_id=pending.turn_public_id,
                    narration="The berth is quiet.",
                )
                messages = connection.execute(
                    """SELECT message.speaker_kind,message.message_text,
                              turn.turn_status
                       FROM camp_referee_message message
                       JOIN camp_referee_turn turn
                         USING(referee_turn_id,campaign_id)
                       WHERE turn.public_id=%s
                       ORDER BY message.message_order""",
                    (pending.turn_public_id,),
                ).fetchall()
                self.assertEqual(
                    messages,
                    [
                        ("player", "I look around.", "completed"),
                        ("referee", "The berth is quiet.", "completed"),
                    ],
                )


if __name__ == "__main__":
    unittest.main()
