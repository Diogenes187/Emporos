import os
import unittest

import psycopg
from psycopg.errors import RaiseException

from engine.combat_runtime import (
    begin_personal_turn_command, change_personal_stance_command,
)
from tests import test_combat_runtime as combat_tests


DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "requires the project PostgreSQL database")
class PersonalStanceChangeTests(unittest.TestCase):
    def test_paired_mechanic_is_normalized(self):
        with psycopg.connect(DSN) as connection:
            mechanic = connection.execute(
                """SELECT mechanic.minor_action_cost,
                          mechanic.may_choose_any_stance,
                          mechanic.must_change_stance,
                          count(provenance.rule_id)
                   FROM rule_personal_stance_change mechanic
                   JOIN rule_rule rule USING(rule_id)
                   JOIN src_record_provenance provenance USING(rule_id)
                   WHERE rule.rule_code='combat.stance-change'
                   GROUP BY mechanic.rule_id""").fetchone()
        self.assertEqual(mechanic, (1, True, True, 2))

    def test_runtime_receipt_uses_cost_and_is_immutable(self):
        with psycopg.connect(DSN) as connection:
            with connection.transaction(force_rollback=True):
                encounter, actors = (
                    combat_tests.PersonalCombatRuntimeIntegrationTests()
                    ._initialized_combat(connection))
                begin_personal_turn_command(
                    connection, initiator_reference="player",
                    idempotency_key="stance-rule-begin",
                    encounter_public_id=encounter,
                    actor_public_id=actors[0])
                result = change_personal_stance_command(
                    connection, initiator_reference="player",
                    idempotency_key="stance-rule-change",
                    encounter_public_id=encounter,
                    actor_public_id=actors[0], stance_code="prone")
                self.assertEqual(
                    (result.stance_before, result.stance_after,
                     result.minor_actions_after),
                    ("standing", "prone", 0))
                command_id = connection.execute(
                    """SELECT command_id FROM cmd_command
                       WHERE idempotency_key='stance-rule-change'""").fetchone()[0]
                with self.assertRaises(RaiseException):
                    with connection.transaction():
                        connection.execute(
                            """UPDATE cmd_personal_stance_receipt
                               SET minor_actions_after=minor_actions_before
                               WHERE command_id=%s""", (command_id,))


if __name__ == "__main__":
    unittest.main()
