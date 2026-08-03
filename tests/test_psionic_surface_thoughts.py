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
class PsionicSurfaceThoughtTests(unittest.TestCase):
    def _actors(self, connection, target_is_telepath=False):
        campaign = connection.execute(
            """INSERT INTO camp_campaign(name,owner_reference)
               VALUES ('Surface Thoughts','player') RETURNING campaign_id"""
        ).fetchone()[0]
        source_id, source_public = connection.execute(
            """INSERT INTO actor_actor
               (campaign_id,name,controller_reference)
               VALUES (%s,'Reader','player') RETURNING actor_id,public_id""",
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
            idempotency_key="lower-reader-shield",
            actor_public_id=str(source_public),
            shield_raised=False,
        )
        if target_is_telepath:
            set_telepathic_shield_command(
                connection,
                initiator_reference="referee",
                idempotency_key="willingly-lower-subject-shield",
                actor_public_id=str(target_public),
                shield_raised=False,
            )
        return str(source_public), str(target_public)

    def test_nontelepath_is_unaware_and_only_current_thoughts_are_recorded(self):
        with psycopg.connect(DSN) as connection:
            with connection.transaction(force_rollback=True):
                source, target = self._actors(connection)
                result = activate_psionic_power_command(
                    connection,
                    initiator_reference="player",
                    idempotency_key="read-current-thoughts",
                    actor_public_id=source,
                    power_rule_code="psionics.power.read-surface-thoughts",
                    range_rule_code="psionics.range.personal",
                    target_actor_public_id=target,
                    surface_thoughts_active_current=(
                        "The subject is deciding whether to open the hatch."
                    ),
                    surface_thoughts_clarity_evidence=(
                        "The immediate decision is distinct; motives are not."
                    ),
                    random_source=FixedRandom((4, 4, 3)),
                )
                receipt = connection.execute(
                    """SELECT effect_snapshot,target_is_telepath,target_unaware,
                              telepath_consent_reference,
                              active_current_thoughts,clarity_evidence
                       FROM cmd_psi_surface_thought_receipt receipt
                       JOIN cmd_command command
                         ON command.command_id=activation_command_id
                       WHERE command.public_id=%s""",
                    (result.command_public_id,),
                ).fetchone()
                self.assertEqual(receipt, (
                    3, False, True, None,
                    "The subject is deciding whether to open the hatch.",
                    "The immediate decision is distinct; motives are not.",
                ))
                with self.assertRaises(RaiseException):
                    with connection.transaction():
                        connection.execute(
                            "DELETE FROM cmd_psi_surface_thought_receipt")

    def test_open_telepath_requires_willing_consent_evidence(self):
        with psycopg.connect(DSN) as connection:
            with connection.transaction(force_rollback=True):
                source, target = self._actors(connection, True)
                with self.assertRaisesRegex(ValueError, "willing"):
                    activate_psionic_power_command(
                        connection,
                        initiator_reference="player",
                        idempotency_key="missing-consent",
                        actor_public_id=source,
                        power_rule_code="psionics.power.read-surface-thoughts",
                        range_rule_code="psionics.range.personal",
                        target_actor_public_id=target,
                        surface_thoughts_active_current="A current thought.",
                        surface_thoughts_clarity_evidence="Clear.",
                        random_source=FixedRandom((6, 6, 2)),
                    )
                result = activate_psionic_power_command(
                    connection,
                    initiator_reference="player",
                    idempotency_key="with-consent",
                    actor_public_id=source,
                    power_rule_code="psionics.power.read-surface-thoughts",
                    range_rule_code="psionics.range.personal",
                    target_actor_public_id=target,
                    surface_thoughts_active_current="A current thought.",
                    surface_thoughts_clarity_evidence="Clear.",
                    surface_thoughts_telepath_consent_reference=(
                        "Subject deliberately lowered their natural shield."
                    ),
                    random_source=FixedRandom((6, 6, 2)),
                )
                receipt = connection.execute(
                    """SELECT target_is_telepath,target_unaware,
                              telepath_consent_reference
                       FROM cmd_psi_surface_thought_receipt receipt
                       JOIN cmd_command command
                         ON command.command_id=activation_command_id
                       WHERE command.public_id=%s""",
                    (result.command_public_id,),
                ).fetchone()
                self.assertEqual(receipt, (
                    True, False,
                    "Subject deliberately lowered their natural shield.",
                ))


if __name__ == "__main__":
    unittest.main()
