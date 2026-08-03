from datetime import datetime, timedelta, timezone
import os
import unittest

import psycopg
from psycopg.errors import RaiseException

from engine.psionics import (
    activate_psionic_power_command,
    recover_psionic_strength_command,
)


DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


class FixedRandom:
    def __init__(self, values):
        self.values = iter(values)

    def randint(self, minimum, maximum):
        value = next(self.values)
        if not minimum <= value <= maximum:
            raise AssertionError("Fixed die lies outside requested range")
        return value


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class PsionicAwarenessRuntimeTests(unittest.TestCase):
    def _actor(self, connection, *, psi=10):
        campaign = connection.execute(
            """INSERT INTO camp_campaign(name,owner_reference)
               VALUES ('Awareness runtime','player')
               RETURNING campaign_id"""
        ).fetchone()[0]
        actor, public_id = connection.execute(
            """INSERT INTO actor_actor
               (campaign_id,name,controller_reference)
               VALUES (%s,'Aware','player') RETURNING actor_id,public_id""",
            (campaign,),
        ).fetchone()
        for code, maximum, current in (
            ("characteristic.psionic-strength", psi, psi),
            ("characteristic.strength", 8, 5),
            ("characteristic.dexterity", 8, 7),
            ("characteristic.endurance", 8, 8),
        ):
            connection.execute(
                """INSERT INTO actor_characteristic
                   (actor_id,characteristic_rule_id,maximum_value,current_value)
                   SELECT %s,rule_id,%s,%s FROM rule_rule
                   WHERE rule_code=%s""",
                (actor, maximum, current, code),
            )
        connection.execute(
            """INSERT INTO actor_skill(actor_id,skill_rule_id,skill_level)
               SELECT %s,rule_id,4 FROM rule_rule
               WHERE rule_code='skill.psionic-awareness'""",
            (actor,),
        )
        return actor, str(public_id)

    def test_suspension_and_enhancement_are_immutable_derived_state(self):
        with psycopg.connect(DSN) as connection:
            with connection.transaction(force_rollback=True):
                actor, public_id = self._actor(connection)
                used_at = datetime.now(timezone.utc)
                suspended = activate_psionic_power_command(
                    connection,
                    initiator_reference="player",
                    idempotency_key="awareness-suspend",
                    actor_public_id=public_id,
                    power_rule_code="psionics.power.suspended-animation",
                    used_at=used_at,
                    random_source=FixedRandom((6, 6, 2)),
                )
                self.assertTrue(suspended.succeeded)
                scheduled = connection.execute(
                    """SELECT suspension.scheduled_end_at
                       FROM cmd_psi_suspended_animation_receipt suspension
                       JOIN cmd_command command
                         ON command.command_id=suspension.activation_command_id
                       WHERE command.public_id=%s""",
                    (suspended.command_public_id,),
                ).fetchone()[0]
                self.assertEqual(scheduled, used_at + timedelta(days=7))

                enhanced = activate_psionic_power_command(
                    connection,
                    initiator_reference="player",
                    idempotency_key="awareness-enhance",
                    actor_public_id=public_id,
                    power_rule_code="psionics.power.enhanced-strength",
                    variable_points=2,
                    used_at=used_at,
                    random_source=FixedRandom((6, 6, 1)),
                )
                receipt = connection.execute(
                    """SELECT wounded_value_snapshot,racial_maximum_snapshot,
                              awareness_level_snapshot,points_gained
                       FROM cmd_psi_characteristic_enhancement_receipt
                       JOIN cmd_command command
                         ON command.command_id=activation_command_id
                       WHERE command.public_id=%s""",
                    (enhanced.command_public_id,),
                ).fetchone()
                base_strength = connection.execute(
                    """SELECT current_value FROM actor_characteristic
                       WHERE actor_id=%s AND characteristic_rule_id=(
                         SELECT rule_id FROM rule_rule
                         WHERE rule_code='characteristic.strength'
                       )""",
                    (actor,),
                ).fetchone()[0]
                self.assertEqual(receipt, (5, 15, 4, 2))
                self.assertEqual(base_strength, 5)
                with self.assertRaises(RaiseException):
                    with connection.transaction():
                        connection.execute(
                            """DELETE FROM
                               cmd_psi_characteristic_enhancement_receipt"""
                        )

    def test_regeneration_heals_and_unlocks_only_at_full_psi(self):
        with psycopg.connect(DSN) as connection:
            with connection.transaction(force_rollback=True):
                actor, public_id = self._actor(connection, psi=5)
                used_at = datetime(2030, 1, 1, tzinfo=timezone.utc)
                result = activate_psionic_power_command(
                    connection,
                    initiator_reference="player",
                    idempotency_key="awareness-regenerate",
                    actor_public_id=public_id,
                    power_rule_code="psionics.power.regeneration",
                    variable_points=3,
                    regeneration_allocations=(
                        ("characteristic.strength", 3),
                    ),
                    used_at=used_at,
                    random_source=FixedRandom((6, 6, 1)),
                )
                self.assertTrue(result.succeeded)
                strength, locks = connection.execute(
                    """SELECT characteristic.current_value,
                              (SELECT count(*) FROM
                                 camp_psi_regeneration_recovery_lock)
                       FROM actor_characteristic characteristic
                       JOIN rule_rule rule
                         ON rule.rule_id=characteristic.characteristic_rule_id
                       WHERE characteristic.actor_id=%s
                         AND rule.rule_code='characteristic.strength'""",
                    (actor,),
                ).fetchone()
                self.assertEqual((strength, locks), (8, 1))
                with self.assertRaisesRegex(ValueError, "remains unavailable"):
                    activate_psionic_power_command(
                        connection,
                        initiator_reference="player",
                        idempotency_key="awareness-regenerate-again",
                        actor_public_id=public_id,
                        power_rule_code="psionics.power.regeneration",
                        variable_points=1,
                        regeneration_allocations=(
                            ("characteristic.dexterity", 1),
                        ),
                    )
                recover_psionic_strength_command(
                    connection,
                    initiator_reference="player",
                    idempotency_key="awareness-regeneration-recovery",
                    actor_public_id=public_id,
                    recovered_at=used_at + timedelta(hours=5),
                )
                lock_count, releases = connection.execute(
                    """SELECT
                         (SELECT count(*) FROM
                            camp_psi_regeneration_recovery_lock),
                         (SELECT count(*) FROM
                            cmd_psi_regeneration_release_receipt)"""
                ).fetchone()
                self.assertEqual((lock_count, releases), (0, 1))


if __name__ == "__main__":
    unittest.main()
