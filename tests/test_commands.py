import os
import unittest

import psycopg

from engine.characters import assign_actor_species_command
from engine.commands import (
    apply_personal_damage_command, resolve_personal_attack_command,
)


class FixedRandom:
    def __init__(self, values):
        self.values = iter(values)

    def randint(self, minimum, maximum):
        value = next(self.values)
        if not minimum <= value <= maximum:
            raise AssertionError("Fixed test value is outside requested range")
        return value


@unittest.skipUnless(
    os.environ.get("BASE_CEPHEUS_DATABASE_URL"),
    "requires the project PostgreSQL database",
)
class AttackCommandIntegrationTests(unittest.TestCase):
    def create_target(self, connection):
        campaign = connection.execute(
            "INSERT INTO camp_campaign (name) VALUES ('Test') RETURNING campaign_id"
        ).fetchone()[0]
        actor, public_id = connection.execute(
            """INSERT INTO actor_actor
               (campaign_id,name,controller_reference)
               VALUES (%s,'Target','integration-player')
               RETURNING actor_id,public_id""", (campaign,)
        ).fetchone()
        for code, value in (
            ("characteristic.strength", 7),
            ("characteristic.dexterity", 7),
            ("characteristic.endurance", 1),
        ):
            connection.execute(
                """INSERT INTO actor_characteristic
                   (actor_id,characteristic_rule_id,maximum_value,current_value)
                   SELECT %s,rule_id,%s,%s FROM rule_rule WHERE rule_code=%s""",
                (actor, value, value, code))
        return str(public_id)

    def test_armored_species_adds_natural_armor_to_worn_armor(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                target_public = self.create_target(connection)
                assign_actor_species_command(
                    connection, initiator_reference="integration-player",
                    idempotency_key="insectan-armor-species",
                    actor_public_id=target_public,
                    species_code="insectan",
                    assignment_kind="import",
                )
                result = resolve_personal_attack_command(
                    connection,
                    initiator_reference="integration-player",
                    idempotency_key="insectan-armor-attack",
                    item_rule_code="equipment.weapon.dagger",
                    attack_profile_code="thrown",
                    range_rule_code="combat.range.short",
                    armor_rule_code="equipment.armor.jack",
                    skill_modifier=1,
                    characteristic_modifier=1,
                    target_actor_public_id=target_public,
                    random_source=FixedRandom((5, 4, 4)),
                )
                self.assertEqual(result.receipt.natural_armor_rating, 1)
                stored = connection.execute(
                    """SELECT natural_armor_rating,armor_rating
                       FROM cmd_attack_receipt
                       WHERE command_id=(
                           SELECT command_id FROM cmd_command
                           WHERE idempotency_key='insectan-armor-attack'
                       )"""
                ).fetchone()
                self.assertEqual(stored[0], 1)
                self.assertEqual(
                    stored[1], result.receipt.armor_rating)

    def test_idempotent_retry_replays_dice_modifiers_and_receipt(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                arguments = dict(
                    initiator_reference="integration-player",
                    idempotency_key="fixed-attack",
                    item_rule_code="equipment.weapon.dagger",
                    attack_profile_code="thrown",
                    range_rule_code="combat.range.short",
                    armor_rule_code="equipment.armor.jack",
                    skill_modifier=1,
                    characteristic_modifier=1,
                    circumstance_modifiers=(1, -1),
                    target_actor_public_id=self.create_target(connection),
                )
                first = resolve_personal_attack_command(
                    connection, random_source=FixedRandom((5, 4, 4)),
                    **arguments,
                )
                replay = resolve_personal_attack_command(
                    connection, random_source=FixedRandom((1, 1)),
                    **arguments,
                )
                self.assertFalse(first.replayed)
                self.assertTrue(replay.replayed)
                self.assertEqual(first.command_public_id, replay.command_public_id)
                self.assertEqual(first.receipt, replay.receipt)
                self.assertEqual(first.receipt.attack_dice, (5, 4))
                self.assertEqual(first.receipt.damage_dice, (4,))
                self.assertEqual(
                    first.receipt.circumstance_modifiers, (1, -1)
                )
                damage = apply_personal_damage_command(
                    connection,
                    initiator_reference="integration-player",
                    idempotency_key="fixed-damage",
                    damage_instance_public_id=first.damage_instance_public_id,
                    allocations=(
                        ("characteristic.endurance", 1),
                        ("characteristic.strength", 1),
                    ),
                )
                damage_replay = apply_personal_damage_command(
                    connection,
                    initiator_reference="integration-player",
                    idempotency_key="fixed-damage",
                    damage_instance_public_id=first.damage_instance_public_id,
                    allocations=(),
                )
                self.assertFalse(damage.replayed)
                self.assertTrue(damage_replay.replayed)
                self.assertEqual(
                    damage.command_public_id, damage_replay.command_public_id)
                self.assertEqual(
                    damage.damage_instance_public_id,
                    damage_replay.damage_instance_public_id)
                self.assertEqual(damage.allocations, damage_replay.allocations)
                self.assertEqual(
                    (damage.actor_version_before, damage.actor_version_after),
                    (damage_replay.actor_version_before,
                     damage_replay.actor_version_after))
                self.assertEqual(
                    damage.allocations,
                    (("characteristic.endurance", 1, 0),
                     ("characteristic.strength", 1, 6)),
                )
