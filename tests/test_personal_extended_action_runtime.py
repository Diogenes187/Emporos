import os
import unittest

import psycopg

from engine.combat_runtime import (
    advance_personal_combat_round_command, begin_personal_turn_command,
    complete_personal_turn_command, declare_personal_attack_command,
    spend_personal_action_command,
)
from engine.commands import (
    apply_personal_damage_command, resolve_personal_attack_command,
)
from engine.extended_actions_runtime import (
    abandon_personal_extended_action_command,
    advance_personal_extended_action_command,
    resolve_personal_extended_action_interruption_command,
    start_personal_extended_action_command,
)
from tests import test_combat_runtime as combat_tests


DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class PersonalExtendedActionRuntimeTests(unittest.TestCase):
    def _started_task(self, connection, *, timing=3, key="extended-start"):
        helper = combat_tests.PersonalCombatRuntimeIntegrationTests("runTest")
        encounter, actors = helper._initialized_combat(connection)
        connection.execute(
            """UPDATE enc_personal_combatant combatant
               SET initiative_current=CASE WHEN actor.public_id=%s THEN 99
                                           ELSE initiative_current END,
                   turn_started_this_round=(actor.public_id=%s),
                   acted_this_round=false
               FROM actor_actor actor
               WHERE actor.actor_id=combatant.actor_id""",
            (actors[0], actors[0]),
        )
        result = start_personal_extended_action_command(
            connection, initiator_reference="player", idempotency_key=key,
            encounter_public_id=encounter, actor_public_id=actors[0],
            task_reference="repair-portable-reactor",
            characteristic_rule_code="characteristic.dexterity",
            skill_rule_code="skill.athletics",
            time_frame_rule_code="time-frame.rounds",
            random_source=combat_tests.FixedRandom((timing,)),
        )
        return encounter, actors, result

    def test_commitment_progresses_exclusively_and_replays(self):
        with psycopg.connect(DSN) as connection:
            with connection.transaction(force_rollback=True):
                encounter, actors, started = self._started_task(connection)
                self.assertEqual((started.status, started.completed_rounds,
                                  started.required_rounds),
                                 ("active", 1, 3))
                replay = start_personal_extended_action_command(
                    connection, initiator_reference="player",
                    idempotency_key="extended-start",
                    encounter_public_id=encounter,
                    actor_public_id=actors[0],
                    task_reference="ignored-on-replay",
                    characteristic_rule_code="characteristic.dexterity",
                    skill_rule_code="skill.athletics",
                    time_frame_rule_code="time-frame.rounds")
                self.assertTrue(replay.replayed)
                self.assertEqual(replay.extended_action_id,
                                 started.extended_action_id)

                connection.execute(
                    "UPDATE enc_personal_combatant SET acted_this_round=true")
                advance_personal_combat_round_command(
                    connection, initiator_reference="referee",
                    idempotency_key="extended-next-round",
                    encounter_public_id=encounter)
                budget = connection.execute(
                    """SELECT significant_actions_remaining,
                              minor_actions_remaining
                       FROM enc_personal_combatant combatant
                       JOIN actor_actor actor ON actor.actor_id=combatant.actor_id
                       WHERE actor.public_id=%s""", (actors[0],)).fetchone()
                self.assertEqual(budget, (0, 0))
                begin_personal_turn_command(
                    connection, initiator_reference="player",
                    idempotency_key="extended-begin-two",
                    encounter_public_id=encounter,
                    actor_public_id=actors[0])
                with self.assertRaisesRegex(ValueError, "advanced or abandoned"):
                    complete_personal_turn_command(
                        connection, initiator_reference="player",
                        idempotency_key="extended-invalid-complete",
                        encounter_public_id=encounter,
                        actor_public_id=actors[0])
                with self.assertRaises((ValueError, PermissionError)):
                    spend_personal_action_command(
                        connection, initiator_reference="player",
                        idempotency_key="extended-invalid-spend",
                        encounter_public_id=encounter,
                        actor_public_id=actors[0],
                        operation="spend_significant")
                progressed = advance_personal_extended_action_command(
                    connection, initiator_reference="player",
                    idempotency_key="extended-progress-two",
                    encounter_public_id=encounter,
                    actor_public_id=actors[0])
                self.assertEqual((progressed.status,
                                  progressed.completed_rounds),
                                 ("active", 2))
                with self.assertRaises(psycopg.errors.RaiseException):
                    connection.execute(
                        """UPDATE cmd_personal_extended_action_receipt
                           SET work_counted=false WHERE command_id=(
                             SELECT command_id
                             FROM cmd_personal_extended_action_receipt
                             WHERE extended_action_id=%s LIMIT 1)""",
                        (started.extended_action_id,))

    def test_active_task_may_be_abandoned(self):
        with psycopg.connect(DSN) as connection:
            with connection.transaction(force_rollback=True):
                encounter, actors, started = self._started_task(
                    connection, timing=4, key="extended-abandon-start")
                result = abandon_personal_extended_action_command(
                    connection, initiator_reference="player",
                    idempotency_key="extended-abandon",
                    encounter_public_id=encounter,
                    actor_public_id=actors[0])
                self.assertEqual(result.status, "abandoned")
                self.assertEqual(result.completed_rounds,
                                 started.completed_rounds)

    def test_hit_can_ruin_task_and_reset_progress(self):
        with psycopg.connect(DSN) as connection:
            with connection.transaction(force_rollback=True):
                encounter, actors, started = self._started_task(
                    connection, timing=5, key="extended-hit-start")
                connection.execute(
                    """INSERT INTO actor_characteristic
                       (actor_id,characteristic_rule_id,maximum_value,
                        current_value)
                       SELECT actor.actor_id,rule.rule_id,7,7
                       FROM actor_actor actor CROSS JOIN rule_rule rule
                       WHERE actor.public_id=%s
                         AND rule.rule_code='characteristic.strength'""",
                    (actors[0],))
                connection.execute(
                    """UPDATE enc_personal_combatant combatant
                       SET turn_started_this_round=(actor.public_id=%s),
                           acted_this_round=false,
                           significant_actions_remaining=1
                       FROM actor_actor actor
                       WHERE actor.actor_id=combatant.actor_id""",
                    (actors[1],))
                declared = declare_personal_attack_command(
                    connection, initiator_reference="referee",
                    idempotency_key="extended-hit-declare",
                    encounter_public_id=encounter,
                    attacker_actor_public_id=actors[1],
                    target_actor_public_id=actors[0],
                    item_rule_code="equipment.weapon.dagger",
                    attack_profile_code="close-quarters",
                    range_rule_code="combat.range.personal")
                attack = resolve_personal_attack_command(
                    connection, initiator_reference="referee",
                    idempotency_key="extended-hit-resolve",
                    item_rule_code="equipment.weapon.dagger",
                    attack_profile_code="close-quarters",
                    range_rule_code="combat.range.personal",
                    armor_rule_code="equipment.armor.jack",
                    target_actor_public_id=actors[0],
                    personal_attack_public_id=declared.personal_attack_public_id,
                    random_source=combat_tests.FixedRandom((6, 6, 4)))
                damage = apply_personal_damage_command(
                    connection, initiator_reference="player",
                    idempotency_key="extended-hit-apply",
                    damage_instance_public_id=attack.damage_instance_public_id,
                    allocations=(("characteristic.endurance",
                                  min(7, attack.receipt.penetrating_damage)),))
                damage_id = connection.execute(
                    """SELECT damage_instance_id FROM health_damage_instance
                       WHERE public_id=%s""",
                    (damage.damage_instance_public_id,)).fetchone()[0]
                interrupted = (
                    resolve_personal_extended_action_interruption_command(
                        connection, initiator_reference="referee",
                        idempotency_key="extended-hit-interrupt",
                        damage_instance_id=damage_id,
                        random_source=combat_tests.FixedRandom((1, 1))))
                self.assertEqual((interrupted.status,
                                  interrupted.completed_rounds),
                                 ("ruined", 0))
                row = connection.execute(
                    """SELECT post_armor_damage,damage_modifier,
                              exceptional_failure
                       FROM cmd_personal_extended_action_interruption
                       WHERE command_id=(
                         SELECT command_id
                         FROM cmd_personal_extended_action_receipt
                         WHERE extended_action_id=%s
                           AND operation='interrupt')""",
                    (started.extended_action_id,)).fetchone()
                self.assertEqual(row, (attack.receipt.penetrating_damage,
                                       -attack.receipt.penetrating_damage,
                                       True))


if __name__ == "__main__":
    unittest.main()
