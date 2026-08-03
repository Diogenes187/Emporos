import os
import unittest

import psycopg
from psycopg.errors import RaiseException

from engine.combat_runtime import begin_personal_turn_command
from engine.coup_de_grace_runtime import resolve_personal_coup_de_grace_command
from tests import test_combat_runtime as combat_tests


DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class PersonalCoupDeGraceRuntimeTests(unittest.TestCase):
    def test_adjacent_ranged_execution_is_atomic_and_immutable(self):
        with psycopg.connect(DSN) as connection:
            with connection.transaction(force_rollback=True):
                helper = combat_tests.PersonalCombatRuntimeIntegrationTests("runTest")
                encounter_public, actors = helper._initialized_combat(connection)
                connection.execute(
                    """INSERT INTO actor_characteristic
                       (actor_id,characteristic_rule_id,maximum_value,current_value)
                       SELECT actor.actor_id,rule.rule_id,7,7
                       FROM actor_actor actor CROSS JOIN rule_rule rule
                       WHERE actor.public_id=ANY(%s)
                         AND rule.rule_code='characteristic.strength'""",
                    (actors,),
                )
                connection.execute(
                    """INSERT INTO actor_personal_condition
                       (actor_id,unconscious,unconscious_cause)
                       SELECT actor_id,true,'telepathic_assault'
                       FROM actor_actor WHERE public_id=%s""",
                    (actors[1],),
                )
                begin_personal_turn_command(
                    connection, initiator_reference="player",
                    idempotency_key="coup-begin",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0],
                )
                result = resolve_personal_coup_de_grace_command(
                    connection, initiator_reference="player",
                    idempotency_key="coup-resolve",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0],
                    target_actor_public_id=actors[1],
                    weapon_rule_code="equipment.weapon.auto-pistol",
                    delivery_kind="ranged", range_relationship="adjacent",
                    helpless_basis="unconscious",
                    helpless_evidence=(
                        "Authoritative condition state records unconsciousness."),
                )
                self.assertEqual(result.delivery_kind, "ranged")
                physical = connection.execute(
                    """SELECT array_agg(state.current_value ORDER BY rule.rule_code)
                       FROM actor_characteristic state
                       JOIN actor_actor actor ON actor.actor_id=state.actor_id
                       JOIN rule_rule rule
                         ON rule.rule_id=state.characteristic_rule_id
                       WHERE actor.public_id=%s
                         AND rule.rule_code IN (
                           'characteristic.strength',
                           'characteristic.dexterity',
                           'characteristic.endurance')""",
                    (actors[1],),
                ).fetchone()[0]
                self.assertEqual(physical, [0, 0, 0])
                receipt = connection.execute(
                    """SELECT significant_actions_before,
                              significant_actions_after,
                              strength_before,strength_after,
                              dexterity_before,dexterity_after,
                              endurance_before,endurance_after,
                              actor_version_before,actor_version_after,
                              target_version_before,target_version_after
                       FROM cmd_personal_coup_de_grace_receipt"""
                ).fetchone()
                self.assertEqual(receipt, (1, 0, 7, 0, 7, 0, 7, 0, 1, 2, 1, 2))
                replay = resolve_personal_coup_de_grace_command(
                    connection, initiator_reference="player",
                    idempotency_key="coup-resolve",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0],
                    target_actor_public_id=actors[1],
                    weapon_rule_code="equipment.weapon.auto-pistol",
                    delivery_kind="ranged", range_relationship="adjacent",
                    helpless_basis="unconscious",
                    helpless_evidence="same command",
                )
                self.assertTrue(replay.replayed)
                with self.assertRaises(RaiseException):
                    connection.execute(
                        """UPDATE cmd_personal_coup_de_grace_receipt
                           SET helpless_evidence='altered'"""
                    )


if __name__ == "__main__":
    unittest.main()
