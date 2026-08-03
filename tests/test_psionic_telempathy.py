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
class PsionicTelempathyTests(unittest.TestCase):
    def _actors(self, connection, target_is_telepath):
        campaign = connection.execute(
            """INSERT INTO camp_campaign(name,owner_reference)
               VALUES ('Telempathy','player') RETURNING campaign_id"""
        ).fetchone()[0]
        source_id, source_public = connection.execute(
            """INSERT INTO actor_actor
               (campaign_id,name,controller_reference)
               VALUES (%s,'Empath','player') RETURNING actor_id,public_id""",
            (campaign,),
        ).fetchone()
        target_id, target_public = connection.execute(
            """INSERT INTO actor_actor
               (campaign_id,name,controller_reference)
               VALUES (%s,'Subject','referee') RETURNING actor_id,public_id""",
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
               VALUES (%s,%s,2)""",
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
            idempotency_key="lower-empath-shield",
            actor_public_id=str(source_public),
            shield_raised=False,
        )
        if target_is_telepath:
            set_telepathic_shield_command(
                connection,
                initiator_reference="referee",
                idempotency_key="lower-subject-shield",
                actor_public_id=str(target_public),
                shield_raised=False,
            )
        return str(source_public), str(target_public)

    def test_projection_does_not_guarantee_nontelepath_behavior(self):
        with psycopg.connect(DSN) as connection:
            with connection.transaction(force_rollback=True):
                source, target = self._actors(connection, False)
                result = activate_psionic_power_command(
                    connection,
                    initiator_reference="player",
                    idempotency_key="project-fear",
                    actor_public_id=source,
                    power_rule_code="psionics.power.telempathy",
                    range_rule_code="psionics.range.personal",
                    target_actor_public_id=target,
                    telempathy_operation="project",
                    telempathy_projected_emotion="fear",
                    telempathy_referee_outcome=(
                        "The subject grows wary but does not flee."
                    ),
                    random_source=FixedRandom((4, 4, 3)),
                )
                receipt = connection.execute(
                    """SELECT operation,effect_snapshot,projected_emotion,
                              perceived_emotions,
                              target_recognized_influence,
                              behavior_not_guaranteed,referee_outcome
                       FROM cmd_psi_telempathy_receipt receipt
                       JOIN cmd_command command
                         ON command.command_id=activation_command_id
                       WHERE command.public_id=%s""",
                    (result.command_public_id,),
                ).fetchone()
                self.assertEqual(receipt, (
                    "project", 5, "fear", None, False, True,
                    "The subject grows wary but does not flee.",
                ))
                with self.assertRaises(RaiseException):
                    with connection.transaction():
                        connection.execute(
                            "DELETE FROM cmd_psi_telempathy_receipt")

    def test_telepath_recognizes_projected_influence(self):
        with psycopg.connect(DSN) as connection:
            with connection.transaction(force_rollback=True):
                source, target = self._actors(connection, True)
                result = activate_psionic_power_command(
                    connection,
                    initiator_reference="player",
                    idempotency_key="read-and-project",
                    actor_public_id=source,
                    power_rule_code="psionics.power.telempathy",
                    range_rule_code="psionics.range.personal",
                    target_actor_public_id=target,
                    telempathy_operation="read_and_project",
                    telempathy_projected_emotion="trust",
                    telempathy_perceived_emotions="suspicion and curiosity",
                    telempathy_referee_outcome=(
                        "The subject recognizes the influence and resists."
                    ),
                    random_source=FixedRandom((5, 5, 2)),
                )
                receipt = connection.execute(
                    """SELECT target_recognized_influence,projected_emotion,
                              perceived_emotions
                       FROM cmd_psi_telempathy_receipt receipt
                       JOIN cmd_command command
                         ON command.command_id=activation_command_id
                       WHERE command.public_id=%s""",
                    (result.command_public_id,),
                ).fetchone()
                self.assertEqual(
                    receipt,
                    (True, "trust", "suspicion and curiosity"),
                )


if __name__ == "__main__":
    unittest.main()
