import os
import unittest

import psycopg
from psycopg.errors import RaiseException

from engine.health_runtime import resolve_personal_unconscious_recovery_command
from engine.psionics import (
    activate_psionic_power_command,
    set_telepathic_shield_command,
)


class FixedRandom:
    def __init__(self, values):
        self.values = iter(values)

    def randint(self, minimum, maximum):
        return next(self.values)


DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class PsionicAssaultRuntimeTests(unittest.TestCase):
    def _actors(self, connection, shielded_target=False):
        campaign = connection.execute(
            """INSERT INTO camp_campaign(name,owner_reference)
               VALUES ('Assault','player') RETURNING campaign_id"""
        ).fetchone()[0]
        source_id, source_public = connection.execute(
            """INSERT INTO actor_actor
               (campaign_id,name,controller_reference)
               VALUES (%s,'Attacker','player') RETURNING actor_id,public_id""",
            (campaign,),
        ).fetchone()
        target_id, target_public = connection.execute(
            """INSERT INTO actor_actor
               (campaign_id,name,controller_reference)
               VALUES (%s,'Target','referee') RETURNING actor_id,public_id""",
            (campaign,),
        ).fetchone()
        for actor_id, values in (
            (source_id, (
                ("characteristic.psionic-strength", 15),
                ("characteristic.endurance", 8),
            )),
            (target_id, (
                ("characteristic.intelligence", 7),
                ("characteristic.endurance", 8),
                *((("characteristic.psionic-strength", 15),)
                  if shielded_target else ()),
            )),
        ):
            for code, value in values:
                connection.execute(
                    """INSERT INTO actor_characteristic
                       (actor_id,characteristic_rule_id,
                        maximum_value,current_value)
                       SELECT %s,rule_id,%s,%s FROM rule_rule
                       WHERE rule_code=%s""",
                    (actor_id, value, value, code),
                )
        skill_id = connection.execute(
            """SELECT rule_id FROM rule_rule
               WHERE rule_code='skill.psionic-telepathy'"""
        ).fetchone()[0]
        connection.execute(
            """INSERT INTO actor_skill(actor_id,skill_rule_id,skill_level)
               VALUES (%s,%s,5)""",
            (source_id, skill_id),
        )
        if shielded_target:
            connection.execute(
                """INSERT INTO actor_skill(actor_id,skill_rule_id,skill_level)
                   VALUES (%s,%s,5)""",
                (target_id, skill_id),
            )
        set_telepathic_shield_command(
            connection,
            initiator_reference="player",
            idempotency_key="lower-attacker-shield",
            actor_public_id=str(source_public),
            shield_raised=False,
        )
        return str(source_public), str(target_public)

    def test_unshielded_assault_allocates_damage_and_recovers_consciousness(self):
        with psycopg.connect(DSN) as connection:
            with connection.transaction(force_rollback=True):
                source, target = self._actors(connection)
                result = activate_psionic_power_command(
                    connection,
                    initiator_reference="player",
                    idempotency_key="unshielded-assault",
                    actor_public_id=source,
                    power_rule_code="psionics.power.assault",
                    range_rule_code="psionics.range.personal",
                    target_actor_public_id=target,
                    random_source=FixedRandom((6, 6, 3, 4, 5)),
                )
                receipt = connection.execute(
                    """SELECT target_shielded,shield_penetrated,
                              raw_damage,psionic_strength_before,
                              psionic_strength_damage,
                              intelligence_before,intelligence_after,
                              intelligence_damage,endurance_before,
                              endurance_after,endurance_damage,
                              rendered_unconscious
                       FROM cmd_psi_assault_receipt receipt
                       JOIN cmd_command command
                         ON command.command_id=activation_command_id
                       WHERE command.public_id=%s""",
                    (result.command_public_id,),
                ).fetchone()
                self.assertEqual(receipt, (
                    False, True, 15, None, 0, 7, 0, 7, 8, 0, 8, True,
                ))
                condition = connection.execute(
                    """SELECT fatigued,unconscious,unconscious_cause
                       FROM actor_personal_condition condition
                       JOIN actor_actor actor USING (actor_id)
                       WHERE actor.public_id=%s""",
                    (target,),
                ).fetchone()
                self.assertEqual(
                    condition, (False, True, "telepathic_assault"))
                recovery = resolve_personal_unconscious_recovery_command(
                    connection,
                    initiator_reference="referee",
                    idempotency_key="wake-after-assault",
                    actor_public_id=target,
                    minutes_elapsed=1,
                    random_source=FixedRandom((6, 6)),
                )
                self.assertTrue(recovery.succeeded)
                self.assertFalse(recovery.remains_fatigued)
                with self.assertRaises(RaiseException):
                    with connection.transaction():
                        connection.execute(
                            "DELETE FROM cmd_psi_assault_receipt")

    def test_shielded_tie_blocks_damage(self):
        with psycopg.connect(DSN) as connection:
            with connection.transaction(force_rollback=True):
                source, target = self._actors(connection, True)
                result = activate_psionic_power_command(
                    connection,
                    initiator_reference="player",
                    idempotency_key="shielded-assault",
                    actor_public_id=source,
                    power_rule_code="psionics.power.assault",
                    range_rule_code="psionics.range.personal",
                    target_actor_public_id=target,
                    random_source=FixedRandom((6, 6, 2, 6, 6)),
                )
                receipt = connection.execute(
                    """SELECT target_shielded,attacker_opposed_total,
                              defender_opposed_total,shield_penetrated,
                              raw_damage,rendered_unconscious
                       FROM cmd_psi_assault_receipt receipt
                       JOIN cmd_command command
                         ON command.command_id=activation_command_id
                       WHERE command.public_id=%s""",
                    (result.command_public_id,),
                ).fetchone()
                self.assertEqual(receipt, (True, 20, 20, False, 0, False))
                values = connection.execute(
                    """SELECT rule.rule_code,state.current_value
                       FROM actor_characteristic state
                       JOIN actor_actor actor USING (actor_id)
                       JOIN rule_rule rule
                         ON rule.rule_id=state.characteristic_rule_id
                       WHERE actor.public_id=%s
                       ORDER BY rule.rule_code""",
                    (target,),
                ).fetchall()
                self.assertEqual(values, [
                    ("characteristic.endurance", 8),
                    ("characteristic.intelligence", 7),
                    ("characteristic.psionic-strength", 15),
                ])


if __name__ == "__main__":
    unittest.main()
