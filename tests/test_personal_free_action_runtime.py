import os
import unittest

import psycopg

from engine.combat_runtime import begin_personal_turn_command
from engine.free_actions_runtime import perform_personal_free_action_command
from tests import test_combat_runtime as combat_tests


DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class PersonalFreeActionRuntimeTests(unittest.TestCase):
    def test_unbounded_default_escalation_replay_and_immutability(self):
        with psycopg.connect(DSN) as connection:
            with connection.transaction(force_rollback=True):
                helper = combat_tests.PersonalCombatRuntimeIntegrationTests(
                    "runTest")
                encounter, actors = helper._initialized_combat(connection)
                begin_personal_turn_command(
                    connection, initiator_reference="player",
                    idempotency_key="free-action-begin",
                    encounter_public_id=encounter,
                    actor_public_id=actors[0])
                first = perform_personal_free_action_command(
                    connection, initiator_reference="player",
                    idempotency_key="free-action-one",
                    encounter_public_id=encounter,
                    actor_public_id=actors[0],
                    action_reference="shout-warning")
                second = perform_personal_free_action_command(
                    connection, initiator_reference="player",
                    idempotency_key="free-action-two",
                    encounter_public_id=encounter,
                    actor_public_id=actors[0],
                    action_reference="push-door-control")
                self.assertEqual((first.free_action_ordinal,
                                  second.free_action_ordinal), (1, 2))
                self.assertEqual((second.significant_actions_after,
                                  second.minor_actions_after), (1, 1))
                escalated = perform_personal_free_action_command(
                    connection, initiator_reference="player",
                    idempotency_key="free-action-three",
                    encounter_public_id=encounter,
                    actor_public_id=actors[0],
                    action_reference="coordinate-multiple-controls",
                    assessed_cost="minor",
                    referee_adjudicator_reference="referee")
                self.assertEqual((escalated.free_action_ordinal,
                                  escalated.minor_actions_after), (3, 0))
                replay = perform_personal_free_action_command(
                    connection, initiator_reference="player",
                    idempotency_key="free-action-three",
                    encounter_public_id=encounter,
                    actor_public_id=actors[0],
                    action_reference="ignored-on-replay")
                self.assertTrue(replay.replayed)
                self.assertEqual(replay.action_reference,
                                 "coordinate-multiple-controls")
                with self.assertRaises(PermissionError):
                    perform_personal_free_action_command(
                        connection, initiator_reference="player",
                        idempotency_key="free-action-no-referee",
                        encounter_public_id=encounter,
                        actor_public_id=actors[0],
                        action_reference="several-more-controls",
                        assessed_cost="significant")
                with self.assertRaises(psycopg.errors.RaiseException):
                    connection.execute(
                        """UPDATE cmd_personal_free_action_receipt
                           SET action_reference='rewritten'
                           WHERE command_id=(SELECT command_id FROM cmd_command
                             WHERE public_id=%s)""",
                        (first.command_public_id,))


if __name__ == "__main__":
    unittest.main()
