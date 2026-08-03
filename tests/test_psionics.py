from datetime import datetime, timedelta, timezone
import os
import unittest

import psycopg

from engine.characters import assign_actor_species_command
from engine.psionics import (
    activate_psionic_power_command, recover_psionic_strength_command,
    set_telepathic_shield_command,
)


class FixedRandom:
    def __init__(self, values):
        self.values = iter(values)

    def randint(self, minimum, maximum):
        value = next(self.values)
        if not minimum <= value <= maximum:
            raise AssertionError("Fixed die lies outside requested range")
        return value


@unittest.skipUnless(
    os.environ.get("BASE_CEPHEUS_DATABASE_URL"),
    "requires the project PostgreSQL database",
)
class PsionicRuntimeIntegrationTests(unittest.TestCase):
    def _actor(self, connection, *, psi=5, endurance=7, skill=1):
        campaign_id = connection.execute(
            """INSERT INTO camp_campaign (name,owner_reference)
               VALUES ('Psionic Test','player') RETURNING campaign_id"""
        ).fetchone()[0]
        actor_id, actor_public = connection.execute(
            """INSERT INTO actor_actor
               (campaign_id,name,controller_reference)
               VALUES (%s,'Psion','player') RETURNING actor_id,public_id""",
            (campaign_id,),
        ).fetchone()
        for code, maximum, current in (
            ("characteristic.psionic-strength", psi, psi),
            ("characteristic.endurance", endurance, endurance),
        ):
            connection.execute(
                """INSERT INTO actor_characteristic
                   (actor_id,characteristic_rule_id,maximum_value,current_value)
                   SELECT %s,rule_id,%s,%s FROM rule_rule WHERE rule_code=%s""",
                (actor_id, maximum, current, code),
            )
        connection.execute(
            """INSERT INTO actor_skill (actor_id,skill_rule_id,skill_level)
               SELECT %s,rule_id,%s FROM rule_rule
               WHERE rule_code='skill.psionic-clairvoyance'""",
            (actor_id, skill),
        )
        return actor_id, str(actor_public)

    def _location(self, connection, actor_id):
        type_id = connection.execute(
            """INSERT INTO rule_rule
               (content_package_id,rule_code,name,rule_category,rule_status)
               SELECT content_package_id,%s,'Remote Test Location',
                      'world','approved'
                 FROM sys_content_package
                WHERE package_code='cepheus-engine'
                ORDER BY content_package_id LIMIT 1
               RETURNING rule_id""",
            (f"location.type.psi-test-{actor_id}",),
        ).fetchone()[0]
        connection.execute(
            """INSERT INTO rule_location_type VALUES (%s,%s,true,true)""",
            (type_id, f"psi-test-{actor_id}"),
        )
        return str(connection.execute(
            """INSERT INTO loc_location
               (campaign_id,location_type_rule_id,name)
               SELECT actor.campaign_id,type.location_type_rule_id,
                      'Remote chamber'
                 FROM actor_actor actor
                 JOIN rule_location_type type
                   ON type.location_type_rule_id=%s
                WHERE actor.actor_id=%s
               RETURNING public_id""",
            (type_id, actor_id),
        ).fetchone()[0])

    def test_anti_psionic_species_cannot_activate_a_power(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                _, actor_public = self._actor(connection)
                assign_actor_species_command(
                    connection, initiator_reference="player",
                    idempotency_key="anti-psi-species",
                    actor_public_id=actor_public,
                    species_code="reptilian",
                    assignment_kind="import",
                )
                with self.assertRaisesRegex(ValueError, "Anti-Psionic"):
                    activate_psionic_power_command(
                        connection, initiator_reference="player",
                        idempotency_key="anti-psi-use",
                        actor_public_id=actor_public,
                        power_rule_code="psionics.power.sense",
                        range_rule_code="psionics.range.short",
                        random_source=FixedRandom((6, 6, 1)),
                    )

    def test_success_spends_base_and_range_and_recovers_hourly(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                actor_id, actor_public = self._actor(connection)
                location_public = self._location(connection, actor_id)
                used_at = datetime(2030, 1, 1, tzinfo=timezone.utc)
                result = activate_psionic_power_command(
                    connection, initiator_reference="player",
                    idempotency_key="psi-success",
                    actor_public_id=actor_public,
                    power_rule_code="psionics.power.sense",
                    range_rule_code="psionics.range.short",
                    random_source=FixedRandom((6, 6, 3)),
                    used_at=used_at,
                    target_location_public_id=location_public,
                    clairvoyant_observation="A quiet remote chamber.",
                )
                self.assertTrue(result.succeeded)
                self.assertEqual(result.psionic_cost, 2)
                self.assertEqual(
                    (result.psionic_strength_before,
                     result.psionic_strength_after),
                    (5, 3),
                )
                replay = activate_psionic_power_command(
                    connection, initiator_reference="player",
                    idempotency_key="psi-success",
                    actor_public_id=actor_public,
                    power_rule_code="psionics.power.sense",
                    range_rule_code="psionics.range.short",
                )
                self.assertTrue(replay.replayed)
                recovered = recover_psionic_strength_command(
                    connection, initiator_reference="player",
                    idempotency_key="psi-recover",
                    actor_public_id=actor_public,
                    recovered_at=used_at + timedelta(hours=3),
                )
                self.assertEqual(
                    (recovered.points_available, recovered.points_recovered,
                     recovered.psionic_strength_after),
                    (1, 1, 4),
                )
                current = connection.execute(
                    """SELECT current_value FROM actor_characteristic
                       WHERE actor_id=%s AND characteristic_rule_id=(
                           SELECT characteristic_rule_id FROM psi_system
                       )""",
                    (actor_id,),
                ).fetchone()[0]
                self.assertEqual(current, 4)

    def test_failure_costs_one_and_success_may_overexert_endurance(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                actor_id, actor_public = self._actor(
                    connection, psi=1, endurance=3)
                location_public = self._location(connection, actor_id)
                failed = activate_psionic_power_command(
                    connection, initiator_reference="player",
                    idempotency_key="psi-failure",
                    actor_public_id=actor_public,
                    power_rule_code="psionics.power.sense",
                    range_rule_code="psionics.range.personal",
                    random_source=FixedRandom((1, 1, 2)),
                    target_location_public_id=location_public,
                    clairvoyant_observation="No clear impression.",
                )
                self.assertFalse(failed.succeeded)
                self.assertEqual(failed.psionic_cost, 1)
                self.assertEqual(failed.psionic_strength_after, 0)
                with self.assertRaises(ValueError):
                    activate_psionic_power_command(
                        connection, initiator_reference="player",
                        idempotency_key="psi-no-strength",
                        actor_public_id=actor_public,
                        power_rule_code="psionics.power.sense",
                        range_rule_code="psionics.range.personal",
                    )

                second_id, second_public = self._actor(
                    connection, psi=1, endurance=3, skill=10)
                second_location_public = self._location(
                    connection, second_id)
                connection.execute(
                    """INSERT INTO loc_actor_position
                       (campaign_id,actor_id,location_id)
                       SELECT campaign_id,%s,location_id FROM loc_location
                       WHERE public_id=%s""",
                    (second_id, second_location_public),
                )
                connection.execute(
                    """INSERT INTO actor_skill
                       (actor_id,skill_rule_id,skill_level)
                       SELECT actor_id,rule_id,10
                       FROM actor_actor CROSS JOIN rule_rule
                       WHERE actor_actor.public_id=%s
                         AND rule_code='skill.psionic-teleportation'""",
                    (second_public,),
                )
                over = activate_psionic_power_command(
                    connection, initiator_reference="player",
                    idempotency_key="psi-overexert",
                    actor_public_id=second_public,
                    power_rule_code="psionics.power.teleport-heavy-load",
                    range_rule_code="psionics.range.personal",
                    random_source=FixedRandom((6, 6, 2)),
                    teleport_destination_location_public_id=
                        second_location_public,
                    teleport_destination_knowledge_kind="personal_visit",
                    teleport_destination_knowledge_evidence=
                        "The actor is standing at this familiar location.",
                )
                self.assertTrue(over.succeeded)
                self.assertEqual(over.psionic_cost, 5)
                self.assertEqual(over.overexertion_damage, 4)
                self.assertEqual(over.endurance_after, 0)

    def test_nonactivation_powers_are_rejected(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                actor_id, actor_public = self._actor(connection)
                connection.execute(
                    """INSERT INTO actor_skill
                       (actor_id,skill_rule_id,skill_level)
                       SELECT %s,rule_id,1 FROM rule_rule
                       WHERE rule_code='skill.psionic-telepathy'""",
                    (actor_id,),
                )
                with self.assertRaisesRegex(ValueError, "activation procedure"):
                    activate_psionic_power_command(
                        connection, initiator_reference="player",
                        idempotency_key="psi-shield",
                        actor_public_id=actor_public,
                        power_rule_code="psionics.power.shield",
                    )

    def test_natural_shields_are_raised_and_control_targeted_telepathy(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                source_id, source_public = self._actor(connection)
                campaign_id = connection.execute(
                    "SELECT campaign_id FROM actor_actor WHERE actor_id=%s",
                    (source_id,),
                ).fetchone()[0]
                target_id, target_public = connection.execute(
                    """INSERT INTO actor_actor
                       (campaign_id,name,controller_reference)
                       VALUES (%s,'Target Telepath','player')
                       RETURNING actor_id,public_id""",
                    (campaign_id,),
                ).fetchone()
                telepathy_skill = connection.execute(
                    """SELECT rule_id FROM rule_rule
                       WHERE rule_code='skill.psionic-telepathy'"""
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO actor_skill
                       (actor_id,skill_rule_id,skill_level)
                       VALUES (%s,%s,1),(%s,%s,0)""",
                    (source_id, telepathy_skill, target_id, telepathy_skill),
                )
                with self.assertRaisesRegex(ValueError, "must lower"):
                    activate_psionic_power_command(
                        connection, initiator_reference="player",
                        idempotency_key="shield-own-block",
                        actor_public_id=source_public,
                        power_rule_code="psionics.power.telempathy",
                        range_rule_code="psionics.range.personal",
                        target_actor_public_id=str(target_public),
                    )
                lowered = set_telepathic_shield_command(
                    connection, initiator_reference="player",
                    idempotency_key="shield-source-lower",
                    actor_public_id=source_public,
                    shield_raised=False,
                )
                self.assertEqual(
                    (lowered.shield_before, lowered.shield_after),
                    (True, False),
                )
                with self.assertRaisesRegex(ValueError, "Target's"):
                    activate_psionic_power_command(
                        connection, initiator_reference="player",
                        idempotency_key="shield-target-block",
                        actor_public_id=source_public,
                        power_rule_code="psionics.power.telempathy",
                        range_rule_code="psionics.range.personal",
                        target_actor_public_id=str(target_public),
                    )
                set_telepathic_shield_command(
                    connection, initiator_reference="player",
                    idempotency_key="shield-target-lower",
                    actor_public_id=str(target_public),
                    shield_raised=False,
                )
                result = activate_psionic_power_command(
                    connection, initiator_reference="player",
                    idempotency_key="shield-target-open",
                    actor_public_id=source_public,
                    power_rule_code="psionics.power.telempathy",
                    range_rule_code="psionics.range.personal",
                    target_actor_public_id=str(target_public),
                    telempathy_operation="read",
                    telempathy_perceived_emotions="calm and attentive",
                    telempathy_referee_outcome=(
                        "The target's present mood is perceived."
                    ),
                    random_source=FixedRandom((6, 6, 2)),
                )
                self.assertTrue(result.succeeded)
                self.assertEqual(
                    result.target_actor_public_id, str(target_public))
