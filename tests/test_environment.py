import os
import unittest
from dataclasses import replace

import psycopg

from engine.characters import assign_actor_species_command
from engine.commands import apply_personal_damage_command
from engine.environment import (
    advance_species_environmental_exposure_command,
)


class FixedRandom:
    def __init__(self, values):
        self.values = iter(values)

    def randint(self, minimum, maximum):
        value = next(self.values)
        if not minimum <= value <= maximum:
            raise AssertionError("Fixed value is outside requested range")
        return value


@unittest.skipUnless(
    os.environ.get("BASE_CEPHEUS_DATABASE_URL"),
    "requires the project PostgreSQL database",
)
class SpeciesEnvironmentalExposureIntegrationTests(unittest.TestCase):
    def create_species_actor(self, connection, species_code, name):
        campaign = connection.execute(
            """INSERT INTO camp_campaign (name,owner_reference)
               VALUES ('Environment Test','player') RETURNING campaign_id"""
        ).fetchone()[0]
        actor_id, actor_public_id = connection.execute(
            """INSERT INTO actor_actor
               (campaign_id,name,controller_reference)
               VALUES (%s,%s,'player') RETURNING actor_id,public_id""",
            (campaign, name),
        ).fetchone()
        for code in (
            "characteristic.strength",
            "characteristic.dexterity",
            "characteristic.endurance",
        ):
            connection.execute(
                """INSERT INTO actor_characteristic
                   (actor_id,characteristic_rule_id,maximum_value,current_value)
                   SELECT %s,rule_id,1,1 FROM rule_rule WHERE rule_code=%s""",
                (actor_id, code),
            )
        assign_actor_species_command(
            connection, initiator_reference="player",
            idempotency_key=f"species-{name}",
            actor_public_id=str(actor_public_id),
            species_code=species_code, assignment_kind="import",
        )
        return str(actor_public_id)

    def test_cold_exposure_accumulates_intervals_and_creates_damage(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                actor_public_id = self.create_species_actor(
                    connection, "insectan", "Cold Insectan")
                first = advance_species_environmental_exposure_command(
                    connection, initiator_reference="player",
                    idempotency_key="cold-first",
                    actor_public_id=actor_public_id,
                    environment_kind="extreme_cold", elapsed_minutes=5,
                    random_source=FixedRandom(()),
                )
                second = advance_species_environmental_exposure_command(
                    connection, initiator_reference="player",
                    idempotency_key="cold-second",
                    actor_public_id=actor_public_id,
                    exposure_public_id=first.exposure_public_id,
                    environment_kind="extreme_cold", elapsed_minutes=7,
                    random_source=FixedRandom((6,)),
                )
                replay = advance_species_environmental_exposure_command(
                    connection, initiator_reference="player",
                    idempotency_key="cold-second",
                    actor_public_id=actor_public_id,
                    exposure_public_id=first.exposure_public_id,
                    environment_kind="extreme_cold", elapsed_minutes=100,
                    random_source=FixedRandom(()),
                )

                self.assertEqual(first.elapsed_minutes_after, 5)
                self.assertEqual(first.newly_processed_intervals, 0)
                self.assertEqual(first.initiative_modifier, -2)
                self.assertEqual(second.elapsed_minutes_after, 12)
                self.assertEqual(second.newly_processed_intervals, 1)
                self.assertEqual(second.damage_dice, (6,))
                self.assertEqual(second.raw_damage, 6)
                self.assertIsNotNone(second.damage_instance_public_id)
                self.assertTrue(replay.replayed)
                self.assertEqual(second, replace(replay, replayed=False))

                applied = apply_personal_damage_command(
                    connection, initiator_reference="player",
                    idempotency_key="cold-lethal-damage",
                    damage_instance_public_id=second.damage_instance_public_id,
                    allocations=(
                        ("characteristic.endurance", 1),
                        ("characteristic.strength", 1),
                        ("characteristic.dexterity", 1),
                    ),
                )
                self.assertEqual(applied.unapplied_lethal_overflow, 3)
                values = connection.execute(
                    """SELECT current_value FROM actor_characteristic
                       WHERE actor_id=(
                           SELECT actor_id FROM actor_actor WHERE public_id=%s
                       )""",
                    (actor_public_id,),
                ).fetchall()
                self.assertEqual({row[0] for row in values}, {0})

    def test_protection_prevents_cold_damage_but_not_elapsed_time(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                actor_public_id = self.create_species_actor(
                    connection, "insectan", "Protected Insectan")
                result = advance_species_environmental_exposure_command(
                    connection, initiator_reference="player",
                    idempotency_key="protected-cold",
                    actor_public_id=actor_public_id,
                    environment_kind="extreme_cold", elapsed_minutes=20,
                    protective_equipment_active=True, end_exposure=True,
                    random_source=FixedRandom(()),
                )
                self.assertEqual(result.newly_processed_intervals, 2)
                self.assertTrue(result.damage_prevented)
                self.assertEqual(result.raw_damage, 0)
                self.assertEqual(result.initiative_modifier, 0)
                self.assertEqual(result.exposure_status, "ended")

    def test_heat_endurance_prevents_each_completed_hour(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                actor_public_id = self.create_species_actor(
                    connection, "reptilian", "Hot Reptilian")
                first = advance_species_environmental_exposure_command(
                    connection, initiator_reference="player",
                    idempotency_key="heat-first",
                    actor_public_id=actor_public_id,
                    environment_kind="hot_weather", elapsed_minutes=59,
                )
                second = advance_species_environmental_exposure_command(
                    connection, initiator_reference="player",
                    idempotency_key="heat-second",
                    actor_public_id=actor_public_id,
                    exposure_public_id=first.exposure_public_id,
                    environment_kind="hot_weather", elapsed_minutes=61,
                    end_exposure=True,
                )
                self.assertEqual(first.newly_processed_intervals, 0)
                self.assertFalse(first.damage_prevented)
                self.assertEqual(second.newly_processed_intervals, 2)
                self.assertTrue(second.damage_prevented)
                self.assertEqual(second.damage_dice, ())
                self.assertEqual(second.exposure_status, "ended")

    def test_species_without_environmental_trait_is_rejected(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                actor_public_id = self.create_species_actor(
                    connection, "human", "Ordinary Human")
                with self.assertRaisesRegex(
                    ValueError, "does not have the cold-blooded trait",
                ):
                    advance_species_environmental_exposure_command(
                        connection, initiator_reference="player",
                        idempotency_key="human-cold",
                        actor_public_id=actor_public_id,
                        environment_kind="extreme_cold", elapsed_minutes=10,
                    )


if __name__ == "__main__":
    unittest.main()
