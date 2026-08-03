import os
import unittest

import psycopg
from psycopg.errors import RaiseException

from engine.combat_runtime import begin_personal_turn_command
from engine.misc_actions_runtime import perform_personal_miscellaneous_action_command
from tests import test_combat_runtime as combat_tests

DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "requires the project PostgreSQL database")
class PersonalMiscellaneousActionTests(unittest.TestCase):
    def test_paired_minor_and_significant_mechanics(self):
        with psycopg.connect(DSN) as connection:
            rows = connection.execute(
                """SELECT mechanic.action_tier,mechanic.action_cost,
                          mechanic.requires_full_attention,
                          mechanic.minimum_seconds,mechanic.maximum_seconds,
                          count(provenance.rule_id)
                   FROM rule_personal_miscellaneous_action mechanic
                   JOIN src_record_provenance provenance USING(rule_id)
                   GROUP BY mechanic.rule_id ORDER BY mechanic.action_tier""").fetchall()
        self.assertEqual(rows, [
            ("minor", 1, False, None, None, 2),
            ("significant", 1, True, 1, 6, 2),
        ])

    def test_minor_action_and_task_are_atomic_and_immutable(self):
        with psycopg.connect(DSN) as connection:
            with connection.transaction(force_rollback=True):
                encounter, actors = (
                    combat_tests.PersonalCombatRuntimeIntegrationTests()
                    ._initialized_combat(connection))
                begin_personal_turn_command(
                    connection, initiator_reference="player",
                    idempotency_key="misc-begin", encounter_public_id=encounter,
                    actor_public_id=actors[0])
                result = perform_personal_miscellaneous_action_command(
                    connection, initiator_reference="player",
                    referee_reference="referee", idempotency_key="misc-minor",
                    encounter_public_id=encounter, actor_public_id=actors[0],
                    action_tier="minor", action_description="Scan the doorway",
                    authorization_reason="A quick visual scan needs little attention.",
                    characteristic_rule_code="characteristic.dexterity",
                    skill_rule_code="skill.athletics",
                    difficulty_rule_code="difficulty.average",
                    random_source=combat_tests.FixedRandom((4, 4)))
                self.assertEqual((result.minor_after, result.significant_after), (0, 1))
                self.assertIsNotNone(result.task_command_public_id)
                replay = perform_personal_miscellaneous_action_command(
                    connection, initiator_reference="player",
                    referee_reference="referee", idempotency_key="misc-minor",
                    encounter_public_id=encounter, actor_public_id=actors[0],
                    action_tier="minor", action_description="Scan the doorway",
                    authorization_reason="A quick visual scan needs little attention.",
                    characteristic_rule_code="characteristic.dexterity",
                    skill_rule_code="skill.athletics",
                    difficulty_rule_code="difficulty.average",
                    random_source=combat_tests.FixedRandom(()))
                self.assertTrue(replay.replayed)
                command_id = connection.execute(
                    "SELECT command_id FROM cmd_command WHERE public_id=%s",
                    (result.command_public_id,)).fetchone()[0]
                with self.assertRaises(RaiseException):
                    with connection.transaction():
                        connection.execute(
                            """UPDATE cmd_personal_miscellaneous_action_receipt
                               SET authorization_reason='changed'
                               WHERE command_id=%s""", (command_id,))
                with self.assertRaises(RaiseException):
                    with connection.transaction():
                        connection.execute(
                            """UPDATE cmd_personal_action_receipt
                               SET minor_after=minor_before
                               WHERE command_id=%s""", (command_id,))

    def test_referee_authority_precedes_task_and_action_mutation(self):
        with psycopg.connect(DSN) as connection:
            with connection.transaction(force_rollback=True):
                encounter, actors = (
                    combat_tests.PersonalCombatRuntimeIntegrationTests()
                    ._initialized_combat(connection))
                begin_personal_turn_command(
                    connection, initiator_reference="player",
                    idempotency_key="misc-denied-begin",
                    encounter_public_id=encounter, actor_public_id=actors[0])
                with self.assertRaises(PermissionError):
                    perform_personal_miscellaneous_action_command(
                        connection, initiator_reference="player",
                        referee_reference="intruder", idempotency_key="misc-denied",
                        encounter_public_id=encounter, actor_public_id=actors[0],
                        action_tier="significant", action_description="Complex repair",
                        authorization_reason="Claimed authorization.")
                self.assertEqual(connection.execute(
                    "SELECT count(*) FROM cmd_command WHERE idempotency_key LIKE 'misc-denied%'"
                ).fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
