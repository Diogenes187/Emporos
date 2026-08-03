import os
import unittest

import psycopg
from psycopg.errors import RaiseException

from engine.psionics import set_telepathic_shield_command


DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class PsionicShieldTests(unittest.TestCase):
    def _actor(self, connection):
        campaign = connection.execute(
            """INSERT INTO camp_campaign(name,owner_reference)
               VALUES ('Shield','player') RETURNING campaign_id"""
        ).fetchone()[0]
        actor_id, public_id = connection.execute(
            """INSERT INTO actor_actor
               (campaign_id,name,controller_reference)
               VALUES (%s,'Telepath','player') RETURNING actor_id,public_id""",
            (campaign,),
        ).fetchone()
        connection.execute(
            """INSERT INTO actor_skill(actor_id,skill_rule_id,skill_level)
               SELECT %s,rule_id,0 FROM rule_rule
               WHERE rule_code='skill.psionic-telepathy'""",
            (actor_id,),
        )
        return actor_id, str(public_id)

    def test_shield_receipts_are_versioned_immutable_and_guard_state(self):
        with psycopg.connect(DSN) as connection:
            with connection.transaction(force_rollback=True):
                actor_id, public_id = self._actor(connection)
                lowered = set_telepathic_shield_command(
                    connection,
                    initiator_reference="player",
                    idempotency_key="lower-shield",
                    actor_public_id=public_id,
                    shield_raised=False,
                )
                self.assertEqual(
                    (lowered.shield_before, lowered.shield_after),
                    (True, False),
                )
                receipt = connection.execute(
                    """SELECT state_changed,actor_version_before,
                              actor_version_after,
                              receipt.changed_at=state.changed_at
                       FROM cmd_telepathic_shield_receipt receipt
                       JOIN actor_telepathic_shield_state state USING (actor_id)
                       WHERE receipt.actor_id=%s""",
                    (actor_id,),
                ).fetchone()
                self.assertEqual(receipt, (True, 1, 2, True))
                set_telepathic_shield_command(
                    connection,
                    initiator_reference="player",
                    idempotency_key="lower-shield-again",
                    actor_public_id=public_id,
                    shield_raised=False,
                )
                unchanged = connection.execute(
                    """SELECT state_changed,actor_version_before,
                              actor_version_after
                       FROM cmd_telepathic_shield_receipt
                       ORDER BY command_id DESC LIMIT 1"""
                ).fetchone()
                self.assertEqual(unchanged, (False, 2, 2))
                with self.assertRaises(RaiseException):
                    with connection.transaction():
                        connection.execute(
                            "DELETE FROM cmd_telepathic_shield_receipt")
                with self.assertRaises(RaiseException):
                    with connection.transaction():
                        connection.execute(
                            """UPDATE actor_telepathic_shield_state
                               SET shield_raised=true WHERE actor_id=%s""",
                            (actor_id,),
                        )
                        connection.execute("SET CONSTRAINTS ALL IMMEDIATE")


if __name__ == "__main__":
    unittest.main()
