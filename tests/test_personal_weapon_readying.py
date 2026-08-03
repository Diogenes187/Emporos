import os
import unittest
import psycopg

from engine.combat_runtime import begin_personal_turn_command
from engine.weapon_ready_runtime import advance_personal_weapon_ready_command
from tests import test_combat_runtime as combat_tests


DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class PersonalWeaponReadyingTests(unittest.TestCase):
    def test_default_gap_and_provenance_are_relational(self):
        with psycopg.connect(DSN) as connection:
            row = connection.execute(
                """SELECT default_minor_actions,time_depends_on_size_and_ease,
                          weapon_description_governs_specific_time,
                          especially_fast_or_slow_exceptions_exist,
                          source_specific_profiles_absent,
                          referee_override_requires_reason
                   FROM rule_personal_weapon_readying""").fetchone()
            self.assertEqual(row, (1, True, True, True, True, True))
            self.assertEqual(connection.execute(
                "SELECT count(*) FROM inv_weapon_ready_profile").fetchone()[0], 0)
            provenance = connection.execute(
                """SELECT count(DISTINCT work.work_code),
                          count(*) FILTER (WHERE provenance.is_primary_citation)
                   FROM rule_personal_weapon_readying mechanic
                   JOIN src_record_provenance provenance
                     ON provenance.rule_id=mechanic.rule_id
                   JOIN src_locator locator USING (source_locator_id)
                   JOIN src_work work USING (source_work_id)""").fetchone()
            self.assertEqual(provenance, (2, 1))

    def test_default_and_referee_override_ready_weapon_deterministically(self):
        with psycopg.connect(DSN) as connection:
            with connection.transaction(force_rollback=True):
                helper = combat_tests.PersonalCombatRuntimeIntegrationTests(
                    "runTest")
                encounter, actors = helper._initialized_combat(connection)
                actor_id = connection.execute(
                    "SELECT actor_id FROM actor_actor WHERE public_id=%s",
                    (actors[0],)).fetchone()[0]
                connection.execute(
                    """INSERT INTO actor_weapon_state
                       (actor_id,weapon_rule_id,ready)
                       SELECT %s,rule_id,false FROM rule_rule
                       WHERE rule_code='equipment.weapon.dagger'""", (actor_id,))
                begin_personal_turn_command(
                    connection, initiator_reference="player",
                    idempotency_key="ready-begin",
                    encounter_public_id=encounter,
                    actor_public_id=actors[0])
                result = advance_personal_weapon_ready_command(
                    connection, initiator_reference="player",
                    idempotency_key="ready-default",
                    encounter_public_id=encounter,
                    actor_public_id=actors[0],
                    weapon_rule_code="equipment.weapon.dagger")
                self.assertEqual((result.ready_basis,
                                  result.required_minor_actions,
                                  result.completed,
                                  result.minor_actions_after),
                                 ("source_default", 1, True, 0))
                replay = advance_personal_weapon_ready_command(
                    connection, initiator_reference="player",
                    idempotency_key="ready-default",
                    encounter_public_id=encounter,
                    actor_public_id=actors[0],
                    weapon_rule_code="equipment.weapon.dagger")
                self.assertTrue(replay.replayed)
                connection.execute(
                    """UPDATE actor_weapon_state SET ready=false
                       WHERE actor_id=%s""", (actor_id,))
                connection.execute(
                    """UPDATE enc_personal_combatant
                       SET minor_actions_remaining=1 WHERE actor_id=%s""",
                    (actor_id,))
                first = advance_personal_weapon_ready_command(
                    connection, initiator_reference="player",
                    idempotency_key="ready-override-one",
                    encounter_public_id=encounter,
                    actor_public_id=actors[0],
                    weapon_rule_code="equipment.weapon.dagger",
                    referee_ready_minor_actions=2,
                    referee_adjudicator_reference="referee",
                    referee_override_reason="Dagger is secured in a locked boot sheath")
                self.assertEqual((first.ready_basis, first.progress_after,
                                  first.completed),
                                 ("referee_override", 1, False))
                connection.execute(
                    """UPDATE enc_personal_combatant
                       SET minor_actions_remaining=1 WHERE actor_id=%s""",
                    (actor_id,))
                second = advance_personal_weapon_ready_command(
                    connection, initiator_reference="player",
                    idempotency_key="ready-override-two",
                    encounter_public_id=encounter,
                    actor_public_id=actors[0],
                    weapon_rule_code="equipment.weapon.dagger")
                self.assertTrue(second.completed)
                self.assertEqual(second.progress_after, 2)
                with self.assertRaises(psycopg.errors.RaiseException):
                    connection.execute(
                        """UPDATE cmd_personal_weapon_ready_receipt
                           SET required_minor_actions=3""")


if __name__ == "__main__":
    unittest.main()
