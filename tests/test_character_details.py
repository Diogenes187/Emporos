import os
import unittest

import psycopg

from engine.characters import (
    assign_actor_species_command, update_character_final_details_command,
)
from engine.careers import attempt_career_entry_command


@unittest.skipUnless(
    os.environ.get("BASE_CEPHEUS_DATABASE_URL"),
    "requires the project PostgreSQL database",
)
class CharacterFinalDetailsIntegrationTests(unittest.TestCase):
    def _actor(self, connection, *, creation_finished=False):
        campaign_id = connection.execute(
            """INSERT INTO camp_campaign (name,owner_reference)
               VALUES ('Final Details','player') RETURNING campaign_id"""
        ).fetchone()[0]
        actor_id, actor_public_id = connection.execute(
            """INSERT INTO actor_actor
               (campaign_id,name,controller_reference)
               VALUES (%s,'Unnamed Traveller','player')
               RETURNING actor_id,public_id""",
            (campaign_id,),
        ).fetchone()
        if creation_finished:
            connection.execute(
                """INSERT INTO actor_lifepath_state
                   (actor_id,age_years,lifepath_status)
                   VALUES (%s,18,'completed')""",
                (actor_id,),
            )
        return str(actor_public_id)

    def test_name_is_rejected_until_lifepath_creation_is_finished(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                actor_public = self._actor(connection, creation_finished=True)
                connection.execute(
                    """UPDATE actor_lifepath_state SET lifepath_status='active'
                       WHERE actor_id=(SELECT actor_id FROM actor_actor
                                       WHERE public_id=%s)""",
                    (actor_public,),
                )
                with self.assertRaisesRegex(ValueError, "finish lifepath"):
                    update_character_final_details_command(
                        connection, initiator_reference="player",
                        idempotency_key="details-too-early",
                        actor_public_id=actor_public,
                        character_name="Premature Name",
                    )

    def test_player_revisions_preserve_prior_profile_and_ordered_goals(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                actor_public = self._actor(connection, creation_finished=True)
                first = update_character_final_details_command(
                    connection, initiator_reference="player",
                    idempotency_key="details-one",
                    actor_public_id=actor_public,
                    character_name="  Sera Venn  ",
                    gender_identity="woman",
                    appearance="Close-cropped hair and a weathered flight coat.",
                    personal_goals=(
                        "Find the lost survey vessel.",
                        "Earn command of her own ship.",
                    ),
                )
                self.assertEqual(first.revision_number, 1)
                self.assertEqual(first.character_name, "Sera Venn")
                self.assertEqual(
                    first.personal_goals,
                    ("Find the lost survey vessel.",
                     "Earn command of her own ship."),
                )
                second = update_character_final_details_command(
                    connection, initiator_reference="player",
                    idempotency_key="details-two",
                    actor_public_id=actor_public,
                    character_name="Captain Sera Venn",
                    gender_identity=None,
                    appearance=None,
                    personal_goals=("Establish an independent trade route.",),
                )
                self.assertEqual(second.revision_number, 2)
                self.assertIsNone(second.gender_identity)
                self.assertIsNone(second.appearance)
                rows = connection.execute(
                    """SELECT revision_number,character_name
                       FROM actor_character_profile_revision
                       ORDER BY revision_number"""
                ).fetchall()
                self.assertEqual(
                    rows,
                    [(1, "Sera Venn"), (2, "Captain Sera Venn")],
                )
                current = connection.execute(
                    """SELECT character_name FROM actor_current_character_profile"""
                ).fetchone()[0]
                actor_name = connection.execute(
                    """SELECT name FROM actor_actor WHERE public_id=%s""",
                    (actor_public,),
                ).fetchone()[0]
                self.assertEqual(current, "Captain Sera Venn")
                self.assertEqual(actor_name, "Captain Sera Venn")

    def test_retry_returns_same_revision_and_wrong_controller_is_rejected(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                actor_public = self._actor(connection, creation_finished=True)
                arguments = dict(
                    initiator_reference="player",
                    idempotency_key="details-retry",
                    actor_public_id=actor_public,
                    character_name="Mara",
                    personal_goals=("Map the frontier.",),
                )
                first = update_character_final_details_command(
                    connection, **arguments)
                replay = update_character_final_details_command(
                    connection, **arguments)
                self.assertFalse(first.replayed)
                self.assertTrue(replay.replayed)
                self.assertEqual(first.revision_number, replay.revision_number)
                count = connection.execute(
                    """SELECT COUNT(*) FROM actor_character_profile_revision"""
                ).fetchone()[0]
                self.assertEqual(count, 1)
                with self.assertRaisesRegex(ValueError, "not controlled"):
                    update_character_final_details_command(
                        connection, initiator_reference="intruder",
                        idempotency_key="details-intruder",
                        actor_public_id=actor_public,
                        character_name="Stolen Name",
                    )

    def test_blank_prose_is_rejected_but_fields_may_be_explicitly_cleared(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                actor_public = self._actor(connection, creation_finished=True)
                with self.assertRaisesRegex(ValueError, "Appearance"):
                    update_character_final_details_command(
                        connection, initiator_reference="player",
                        idempotency_key="blank-appearance",
                        actor_public_id=actor_public,
                        character_name="Rook", appearance="   ",
                    )

    def test_species_catalogue_is_relational_and_assignment_is_revisioned(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                actor_public = self._actor(connection)
                catalogue = connection.execute(
                    """SELECT species.species_code,COUNT(trait.species_trait_rule_id)
                       FROM rule_species species
                       LEFT JOIN rule_species_trait_assignment trait
                         ON trait.species_rule_id=species.species_rule_id
                       GROUP BY species.species_code
                       ORDER BY species.species_code"""
                ).fetchall()
                self.assertEqual(len(catalogue), 6)
                self.assertIn(("reptilian", 6), catalogue)
                reptilian = assign_actor_species_command(
                    connection, initiator_reference="player",
                    idempotency_key="species-reptilian",
                    actor_public_id=actor_public,
                    species_code="reptilian",
                    assignment_kind="import",
                )
                self.assertEqual(reptilian.assignment_revision, 1)
                self.assertEqual(reptilian.aging_start_age_years, 42)
                self.assertIn("natural-weapon", reptilian.trait_codes)
                self.assertEqual(reptilian.skill_grants, ())
                human = assign_actor_species_command(
                    connection, initiator_reference="player",
                    idempotency_key="species-human",
                    actor_public_id=actor_public,
                    species_code="human",
                    assignment_kind="player_edit",
                )
                self.assertEqual(human.assignment_revision, 2)
                self.assertEqual(human.trait_codes, ())
                current = connection.execute(
                    """SELECT species.species_code
                       FROM actor_current_species current_species
                       JOIN rule_species species
                         ON species.species_rule_id=
                            current_species.species_rule_id"""
                ).fetchone()[0]
                self.assertEqual(current, "human")
                history = connection.execute(
                    """SELECT COUNT(*) FROM actor_species_assignment"""
                ).fetchone()[0]
                self.assertEqual(history, 2)

    def test_species_characteristic_and_physical_formulas_are_queryable(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            rows = connection.execute(
                """SELECT characteristic.rule_code,generation.dice_count,
                          generation.roll_modifier,
                          generation.racial_maximum_modifier
                   FROM rule_species species
                   JOIN rule_species_characteristic_generation generation
                     ON generation.species_rule_id=species.species_rule_id
                   JOIN rule_rule characteristic
                     ON characteristic.rule_id=
                        generation.characteristic_rule_id
                   WHERE species.species_code='reptilian'
                   ORDER BY characteristic.rule_code"""
            ).fetchall()
            self.assertEqual(
                rows,
                [
                    ("characteristic.dexterity", 2, 1, 1),
                    ("characteristic.endurance", 2, -2, -2),
                    ("characteristic.strength", 2, 1, 1),
                ],
            )
            physical = connection.execute(
                """SELECT height_base_cm,height_dice_count,
                          height_multiplier_cm,mass_base_kg,
                          mass_dice_count,mass_multiplier_kg
                   FROM rule_species_physical_generation physical
                   JOIN rule_species species
                     ON species.species_rule_id=physical.species_rule_id
                   WHERE species.species_code='avian'"""
            ).fetchone()
            self.assertEqual(physical, (105, 2, 2, 20, 2, 2))

    def test_species_maturity_sets_prior_experience_starting_age(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                actor_public = self._actor(connection)
                assign_actor_species_command(
                    connection, initiator_reference="player",
                    idempotency_key="avian-before-career",
                    actor_public_id=actor_public,
                    species_code="avian",
                    assignment_kind="character_creation",
                )
                entry = attempt_career_entry_command(
                    connection, initiator_reference="player",
                    idempotency_key="avian-drifter",
                    actor_public_id=actor_public,
                    career_code="drifter",
                )
                self.assertTrue(entry.qualified)
                age = connection.execute(
                    """SELECT lifepath.age_years
                       FROM actor_lifepath_state lifepath
                       JOIN actor_actor actor ON actor.actor_id=lifepath.actor_id
                       WHERE actor.public_id=%s""",
                    (actor_public,),
                ).fetchone()[0]
                self.assertEqual(age, 22)
                skill = connection.execute(
                    """SELECT state.skill_level
                       FROM actor_skill state
                       JOIN rule_rule rule ON rule.rule_id=state.skill_rule_id
                       JOIN actor_actor actor ON actor.actor_id=state.actor_id
                       WHERE actor.public_id=%s
                         AND rule.rule_code='skill.athletics'""",
                    (actor_public,),
                ).fetchone()
                self.assertEqual(skill, (0,))

    def test_character_creation_species_grants_do_not_reduce_existing_skill(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                actor_public = self._actor(connection)
                connection.execute(
                    """INSERT INTO actor_skill
                       (actor_id,skill_rule_id,skill_level)
                       SELECT actor.actor_id,rule.rule_id,2
                       FROM actor_actor actor CROSS JOIN rule_rule rule
                       WHERE actor.public_id=%s
                         AND rule.rule_code='skill.natural-weapons'""",
                    (actor_public,),
                )
                result = assign_actor_species_command(
                    connection, initiator_reference="player",
                    idempotency_key="reptilian-skill-grant",
                    actor_public_id=actor_public,
                    species_code="reptilian",
                    assignment_kind="character_creation",
                )
                self.assertEqual(
                    result.skill_grants,
                    (("skill.natural-weapons", 2, 2),),
                )
