import os
import unittest

import psycopg
from psycopg.errors import RaiseException

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
class PsionicSendThoughtsTests(unittest.TestCase):
    def _actors(self, connection, target_is_telepath=False):
        campaign = connection.execute(
            """INSERT INTO camp_campaign(name,owner_reference)
               VALUES ('Send Thoughts','player') RETURNING campaign_id"""
        ).fetchone()[0]
        source_id, source_public = connection.execute(
            """INSERT INTO actor_actor
               (campaign_id,name,controller_reference)
               VALUES (%s,'Sender','player') RETURNING actor_id,public_id""",
            (campaign,),
        ).fetchone()
        target_id, target_public = connection.execute(
            """INSERT INTO actor_actor
               (campaign_id,name,controller_reference)
               VALUES (%s,'Recipient','referee') RETURNING actor_id,public_id""",
            (campaign,),
        ).fetchone()
        for code, value in (
            ("characteristic.psionic-strength", 10),
            ("characteristic.endurance", 8),
        ):
            connection.execute(
                """INSERT INTO actor_characteristic
                   (actor_id,characteristic_rule_id,maximum_value,current_value)
                   SELECT %s,rule_id,%s,%s FROM rule_rule WHERE rule_code=%s""",
                (source_id, value, value, code),
            )
        skill_id = connection.execute(
            """SELECT rule_id FROM rule_rule
               WHERE rule_code='skill.psionic-telepathy'"""
        ).fetchone()[0]
        connection.execute(
            """INSERT INTO actor_skill(actor_id,skill_rule_id,skill_level)
               VALUES (%s,%s,3)""",
            (source_id, skill_id),
        )
        if target_is_telepath:
            connection.execute(
                """INSERT INTO actor_skill(actor_id,skill_rule_id,skill_level)
                   VALUES (%s,%s,0)""",
                (target_id, skill_id),
            )
        set_telepathic_shield_command(
            connection,
            initiator_reference="player",
            idempotency_key="lower-sender-shield",
            actor_public_id=str(source_public),
            shield_raised=False,
        )
        return str(source_public), str(target_public)

    def test_nontelepath_receives_exact_immutable_thought(self):
        with psycopg.connect(DSN) as connection:
            with connection.transaction(force_rollback=True):
                source, target = self._actors(connection)
                result = activate_psionic_power_command(
                    connection,
                    initiator_reference="player",
                    idempotency_key="send-warning",
                    actor_public_id=source,
                    power_rule_code="psionics.power.send-thoughts",
                    range_rule_code="psionics.range.personal",
                    target_actor_public_id=target,
                    sent_thought_content="Do not open the airlock.",
                    random_source=FixedRandom((4, 4, 3)),
                )
                receipt = connection.execute(
                    """SELECT timing_rounds_snapshot,target_is_telepath,
                              transmitted_thought,delivered
                       FROM cmd_psi_sent_thought_receipt receipt
                       JOIN cmd_command command
                         ON command.command_id=activation_command_id
                       WHERE command.public_id=%s""",
                    (result.command_public_id,),
                ).fetchone()
                self.assertEqual(
                    receipt, (3, False, "Do not open the airlock.", True))
                with self.assertRaises(RaiseException):
                    with connection.transaction():
                        connection.execute(
                            "DELETE FROM cmd_psi_sent_thought_receipt")

    def test_telepath_must_open_shield_to_receive(self):
        with psycopg.connect(DSN) as connection:
            with connection.transaction(force_rollback=True):
                source, target = self._actors(connection, True)
                with self.assertRaisesRegex(ValueError, "Target's"):
                    activate_psionic_power_command(
                        connection,
                        initiator_reference="player",
                        idempotency_key="blocked-message",
                        actor_public_id=source,
                        power_rule_code="psionics.power.send-thoughts",
                        range_rule_code="psionics.range.personal",
                        target_actor_public_id=target,
                        sent_thought_content="Can you hear me?",
                        random_source=FixedRandom((6, 6, 2)),
                    )
                set_telepathic_shield_command(
                    connection,
                    initiator_reference="referee",
                    idempotency_key="open-recipient-shield",
                    actor_public_id=target,
                    shield_raised=False,
                )
                result = activate_psionic_power_command(
                    connection,
                    initiator_reference="player",
                    idempotency_key="delivered-message",
                    actor_public_id=source,
                    power_rule_code="psionics.power.send-thoughts",
                    range_rule_code="psionics.range.personal",
                    target_actor_public_id=target,
                    sent_thought_content="Can you hear me?",
                    random_source=FixedRandom((6, 6, 2)),
                )
                receipt = connection.execute(
                    """SELECT target_is_telepath,delivered
                       FROM cmd_psi_sent_thought_receipt receipt
                       JOIN cmd_command command
                         ON command.command_id=activation_command_id
                       WHERE command.public_id=%s""",
                    (result.command_public_id,),
                ).fetchone()
                self.assertEqual(receipt, (True, True))


if __name__ == "__main__":
    unittest.main()
