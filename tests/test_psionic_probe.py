import os
import unittest

import psycopg
from psycopg.errors import RaiseException

from engine.psionics import (
    ProbeQuestion,
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
class PsionicProbeTests(unittest.TestCase):
    def _actors(self, connection):
        campaign = connection.execute(
            """INSERT INTO camp_campaign(name,owner_reference)
               VALUES ('Probe','player') RETURNING campaign_id"""
        ).fetchone()[0]
        source_id, source_public = connection.execute(
            """INSERT INTO actor_actor
               (campaign_id,name,controller_reference)
               VALUES (%s,'Prober','player') RETURNING actor_id,public_id""",
            (campaign,),
        ).fetchone()
        _, target_public = connection.execute(
            """INSERT INTO actor_actor
               (campaign_id,name,controller_reference)
               VALUES (%s,'Subject','referee') RETURNING actor_id,public_id""",
            (campaign,),
        ).fetchone()
        for code, value in (
            ("characteristic.psionic-strength", 15),
            ("characteristic.endurance", 8),
        ):
            connection.execute(
                """INSERT INTO actor_characteristic
                   (actor_id,characteristic_rule_id,maximum_value,current_value)
                   SELECT %s,rule_id,%s,%s FROM rule_rule WHERE rule_code=%s""",
                (source_id, value, value, code),
            )
        connection.execute(
            """INSERT INTO actor_skill(actor_id,skill_rule_id,skill_level)
               SELECT %s,rule_id,5 FROM rule_rule
               WHERE rule_code='skill.psionic-telepathy'""",
            (source_id,),
        )
        set_telepathic_shield_command(
            connection,
            initiator_reference="player",
            idempotency_key="lower-prober-shield",
            actor_public_id=str(source_public),
            shield_raised=False,
        )
        return str(source_public), str(target_public)

    def _activate(self, connection, code, key, questions, timing):
        source, target = self._actors(connection)
        result = activate_psionic_power_command(
            connection,
            initiator_reference="player",
            idempotency_key=key,
            actor_public_id=source,
            power_rule_code=f"psionics.power.{code}",
            range_rule_code="psionics.range.personal",
            target_actor_public_id=target,
            probe_innermost_thoughts="The access code is seven.",
            probe_clarity_evidence="Effect reveals a sharp, coherent memory.",
            probe_questions=questions,
            random_source=FixedRandom((6, 6, timing)),
        )
        connection.execute("SET CONSTRAINTS ALL IMMEDIATE")
        return result

    def test_deliberate_probe_records_ordered_immutable_evidence(self):
        questions = (
            ProbeQuestion("What is the code?", "Seven."),
            ProbeQuestion("Did you warn them?", "No.", True),
        )
        with psycopg.connect(DSN) as connection:
            with connection.transaction(force_rollback=True):
                result = self._activate(
                    connection, "probe-deliberate", "deliberate", questions, 3
                )
                receipt = connection.execute(
                    """SELECT probe_mode,timing_total_snapshot,
                              timing_unit_snapshot,innermost_thoughts,
                              clarity_evidence,question_count
                       FROM cmd_psi_probe_receipt receipt
                       JOIN cmd_command command
                         ON command.command_id=activation_command_id
                       WHERE command.public_id=%s""",
                    (result.command_public_id,),
                ).fetchone()
                self.assertEqual(receipt, (
                    "deliberate", 3, "minutes",
                    "The access code is seven.",
                    "Effect reveals a sharp, coherent memory.", 2,
                ))
                rows = connection.execute(
                    """SELECT question_order,question_text,
                              divulged_information,deliberate_untruth_detected
                       FROM cmd_psi_probe_question
                       ORDER BY question_order"""
                ).fetchall()
                self.assertEqual(rows, [
                    (1, "What is the code?", "Seven.", False),
                    (2, "Did you warn them?", "No.", True),
                ])
                with self.assertRaises(RaiseException):
                    with connection.transaction():
                        connection.execute("DELETE FROM cmd_psi_probe_question")

    def test_rapid_probe_uses_seconds_and_allows_no_questions(self):
        with psycopg.connect(DSN) as connection:
            with connection.transaction(force_rollback=True):
                result = self._activate(
                    connection, "probe-rapid", "rapid", (), 4
                )
                receipt = connection.execute(
                    """SELECT probe_mode,timing_total_snapshot,
                              timing_unit_snapshot,question_count
                       FROM cmd_psi_probe_receipt receipt
                       JOIN cmd_command command
                         ON command.command_id=activation_command_id
                       WHERE command.public_id=%s""",
                    (result.command_public_id,),
                ).fetchone()
                self.assertEqual(receipt, ("rapid", 4, "seconds", 0))


if __name__ == "__main__":
    unittest.main()
