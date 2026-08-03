import os
import unittest

import psycopg

from engine.characters import assign_actor_species_command
from engine.tasks import (
    evaluate_species_low_light_visibility_command,
    resolve_actor_task_command, resolve_species_hive_mentality_command,
    resolve_species_naturally_curious_command,
)


class FixedRandom:
    def __init__(self, values):
        self.values = iter(values)

    def randint(self, minimum, maximum):
        return next(self.values)


@unittest.skipUnless(
    os.environ.get("BASE_CEPHEUS_DATABASE_URL"),
    "requires the project PostgreSQL database",
)
class ActorTaskIntegrationTests(unittest.TestCase):
    def _actor(self, connection, name, species_code):
        campaign_id = connection.execute(
            """INSERT INTO camp_campaign (name,owner_reference)
               VALUES ('Species Tasks','player') RETURNING campaign_id"""
        ).fetchone()[0]
        actor_id, actor_public = connection.execute(
            """INSERT INTO actor_actor
               (campaign_id,name,controller_reference)
               VALUES (%s,%s,'player') RETURNING actor_id,public_id""",
            (campaign_id, name),
        ).fetchone()
        connection.execute(
            """INSERT INTO actor_characteristic
               (actor_id,characteristic_rule_id,maximum_value,current_value)
               SELECT %s,rule_id,9,9 FROM rule_rule
               WHERE rule_code IN (
                   'characteristic.dexterity','characteristic.education',
                   'characteristic.intelligence'
               )""",
            (actor_id,),
        )
        connection.execute(
            """INSERT INTO actor_skill (actor_id,skill_rule_id,skill_level)
               SELECT %s,rule_id,1 FROM rule_rule
               WHERE rule_code IN (
                   'skill.piloting','skill.navigation','skill.athletics'
               )""",
            (actor_id,),
        )
        assign_actor_species_command(
            connection, initiator_reference="player",
            idempotency_key=f"species-{name}",
            actor_public_id=str(actor_public), species_code=species_code,
            assignment_kind="import",
        )
        return str(actor_public)

    def test_natural_pilot_applies_to_piloting_and_is_idempotent(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                actor = self._actor(connection, "Avian Pilot", "avian")
                result = resolve_actor_task_command(
                    connection, initiator_reference="player",
                    idempotency_key="avian-piloting",
                    actor_public_id=actor,
                    characteristic_rule_code="characteristic.dexterity",
                    skill_rule_code="skill.piloting",
                    difficulty_rule_code="difficulty.average",
                    circumstance_modifier=-1,
                    random_source=FixedRandom((3, 3)),
                )
                self.assertEqual(result.species_modifier, 2)
                self.assertEqual(result.total, 9)
                self.assertTrue(result.succeeded)
                replay = resolve_actor_task_command(
                    connection, initiator_reference="player",
                    idempotency_key="avian-piloting",
                    actor_public_id=actor,
                    characteristic_rule_code="characteristic.education",
                    skill_rule_code="skill.athletics",
                    difficulty_rule_code="difficulty.formidable",
                    random_source=FixedRandom((1, 1)),
                )
                self.assertTrue(replay.replayed)
                self.assertEqual(replay.dice, (3, 3))
                self.assertEqual(replay.species_modifier, 2)

    def test_law_pace_simultaneous_actions_and_time_are_audited(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                actor = self._actor(connection, "Busy Administrator", "human")
                actor_id = connection.execute(
                    "SELECT actor_id FROM actor_actor WHERE public_id=%s",
                    (actor,),).fetchone()[0]
                connection.execute(
                    """INSERT INTO actor_skill(actor_id,skill_rule_id,skill_level)
                       SELECT %s,rule_id,1 FROM rule_rule
                       WHERE rule_code='skill.admin'""",(actor_id,))
                result = resolve_actor_task_command(
                    connection, initiator_reference="player",
                    idempotency_key="full-task-context", actor_public_id=actor,
                    characteristic_rule_code="characteristic.education",
                    skill_rule_code="skill.admin", law_level=8,
                    time_frame_rule_code="time-frame.hours",
                    time_frame_steps=-2, simultaneous_action_count=3,
                    random_source=FixedRandom((6, 6, 4)))
                self.assertEqual(result.difficulty_rule_code,
                                 "difficulty.very-difficult")
                self.assertEqual(result.difficulty_modifier, -4)
                self.assertEqual(result.pace_modifier, -2)
                self.assertEqual(result.simultaneous_action_modifier, -4)
                self.assertEqual(result.resolved_time_frame_rule_code,
                                 "time-frame.minutes")
                self.assertEqual((result.task_time_quantity,
                                  result.task_time_unit), (4, "minute"))
                self.assertEqual(result.total, 4)
                with self.assertRaises(psycopg.Error):
                    with connection.transaction():
                        connection.execute(
                            """UPDATE cmd_actor_task_receipt SET law_level=7
                               WHERE command_id=(SELECT command_id FROM cmd_command
                               WHERE initiator_reference='player'
                               AND idempotency_key='full-task-context')""")

    def test_task_context_rejects_conflicts_and_time_table_overflow(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                actor = self._actor(connection, "Boundary Tester", "human")
                with self.assertRaisesRegex(ValueError, "conflicts"):
                    resolve_actor_task_command(
                        connection, initiator_reference="player",
                        idempotency_key="law-conflict", actor_public_id=actor,
                        characteristic_rule_code="characteristic.education",
                        skill_rule_code="skill.athletics", law_level=8,
                        difficulty_rule_code="difficulty.average")
                with self.assertRaisesRegex(ValueError, "beyond"):
                    resolve_actor_task_command(
                        connection, initiator_reference="player",
                        idempotency_key="time-overflow", actor_public_id=actor,
                        characteristic_rule_code="characteristic.education",
                        skill_rule_code="skill.athletics",
                        difficulty_rule_code="difficulty.average",
                        time_frame_rule_code="time-frame.seconds",
                        time_frame_steps=-1)

    def test_characteristic_only_check_has_no_invented_skill_modifier(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                actor = self._actor(connection, "Social Standing", "human")
                actor_id = connection.execute(
                    "SELECT actor_id FROM actor_actor WHERE public_id=%s",
                    (actor,),).fetchone()[0]
                social = connection.execute(
                    """SELECT rule_id FROM rule_rule
                       WHERE rule_code='characteristic.social-standing'""").fetchone()[0]
                connection.execute(
                    """INSERT INTO actor_characteristic
                       (actor_id,characteristic_rule_id,maximum_value,current_value)
                       VALUES (%s,%s,9,9)""",(actor_id,social))
                result = resolve_actor_task_command(
                    connection,initiator_reference="player",
                    idempotency_key="social-only",actor_public_id=actor,
                    characteristic_rule_code="characteristic.social-standing",
                    law_level=4,random_source=FixedRandom((5,4)))
                self.assertIsNone(result.skill_rule_code)
                self.assertEqual(result.skill_modifier,0)
                self.assertEqual(result.difficulty_rule_code,
                                 "difficulty.difficult")
                self.assertEqual(result.total,8)
                self.assertTrue(result.succeeded)

    def test_jack_of_all_trades_reduces_untrained_penalty_but_never_adds_bonus(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                actor = self._actor(connection, "Versatile Amateur", "human")
                actor_id = connection.execute(
                    "SELECT actor_id FROM actor_actor WHERE public_id=%s",
                    (actor,),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO actor_skill(actor_id,skill_rule_id,skill_level)
                       SELECT %s,rule_id,2 FROM rule_rule
                       WHERE rule_code='skill.jack-of-all-trades'""",
                    (actor_id,),
                )
                reduced = resolve_actor_task_command(
                    connection, initiator_reference="player",
                    idempotency_key="jot-reduced", actor_public_id=actor,
                    characteristic_rule_code="characteristic.education",
                    skill_rule_code="skill.mechanics",
                    difficulty_rule_code="difficulty.average",
                    random_source=FixedRandom((4, 4)),
                )
                self.assertEqual(reduced.base_skill_modifier, -3)
                self.assertEqual(reduced.jack_of_all_trades_level, 2)
                self.assertEqual(reduced.jack_of_all_trades_reduction, 2)
                self.assertEqual(reduced.skill_modifier, -1)
                connection.execute(
                    """UPDATE actor_skill SET skill_level=4
                       WHERE actor_id=%s AND skill_rule_id=(SELECT rule_id
                       FROM rule_rule WHERE rule_code='skill.jack-of-all-trades')""",
                    (actor_id,),
                )
                capped = resolve_actor_task_command(
                    connection, initiator_reference="player",
                    idempotency_key="jot-capped", actor_public_id=actor,
                    characteristic_rule_code="characteristic.education",
                    skill_rule_code="skill.mechanics",
                    difficulty_rule_code="difficulty.average",
                    random_source=FixedRandom((4, 4)),
                )
                self.assertEqual(capped.jack_of_all_trades_reduction, 3)
                self.assertEqual(capped.skill_modifier, 0)
                connection.execute(
                    """INSERT INTO actor_skill(actor_id,skill_rule_id,skill_level)
                       SELECT %s,rule_id,1 FROM rule_rule
                       WHERE rule_code='skill.mechanics'""",
                    (actor_id,),
                )
                trained = resolve_actor_task_command(
                    connection, initiator_reference="player",
                    idempotency_key="jot-trained", actor_public_id=actor,
                    characteristic_rule_code="characteristic.education",
                    skill_rule_code="skill.mechanics",
                    difficulty_rule_code="difficulty.average",
                    random_source=FixedRandom((4, 4)),
                )
                self.assertEqual(trained.base_skill_modifier, 1)
                self.assertIsNone(trained.jack_of_all_trades_level)
                self.assertEqual(trained.jack_of_all_trades_reduction, 0)
                self.assertEqual(trained.skill_modifier, 1)

    def test_natural_pilot_excludes_unlisted_skills(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                actor = self._actor(connection, "Avian Athlete", "avian")
                result = resolve_actor_task_command(
                    connection, initiator_reference="player",
                    idempotency_key="avian-athletics",
                    actor_public_id=actor,
                    characteristic_rule_code="characteristic.dexterity",
                    skill_rule_code="skill.athletics",
                    difficulty_rule_code="difficulty.average",
                    random_source=FixedRandom((3, 3)),
                )
                self.assertEqual(result.species_modifier, 0)

    def test_natural_swimmer_requires_swimming_context(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                actor = self._actor(connection, "Merfolk Swimmer", "merfolk")
                swimming = resolve_actor_task_command(
                    connection, initiator_reference="player",
                    idempotency_key="merfolk-swimming",
                    actor_public_id=actor,
                    characteristic_rule_code="characteristic.dexterity",
                    skill_rule_code="skill.athletics",
                    difficulty_rule_code="difficulty.average",
                    task_context_code="swimming",
                    random_source=FixedRandom((3, 3)),
                )
                ordinary = resolve_actor_task_command(
                    connection, initiator_reference="player",
                    idempotency_key="merfolk-running",
                    actor_public_id=actor,
                    characteristic_rule_code="characteristic.dexterity",
                    skill_rule_code="skill.athletics",
                    difficulty_rule_code="difficulty.average",
                    random_source=FixedRandom((3, 3)),
                )
                self.assertEqual(swimming.species_modifier, 2)
                self.assertEqual(ordinary.species_modifier, 0)
                modifiers = connection.execute(
                    """SELECT modifier FROM cmd_actor_task_species_modifier
                       WHERE command_id=(
                           SELECT command_id FROM cmd_command
                           WHERE initiator_reference='player'
                             AND idempotency_key='merfolk-swimming'
                       )"""
                ).fetchall()
                self.assertEqual(modifiers, [(2,)])

    def test_hive_mentality_resolves_intelligence_check_and_replays(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                actor = self._actor(connection, "Insectan Worker", "insectan")
                result = resolve_species_hive_mentality_command(
                    connection, initiator_reference="player",
                    idempotency_key="hive-mentality-resist",
                    actor_public_id=actor,
                    family_group_reference="colony-seven",
                    perceived_benefit="Hold the door so the colony can escape.",
                    difficulty_rule_code="difficulty.difficult",
                    random_source=FixedRandom((5, 4)),
                )
                self.assertEqual(result.intelligence_modifier, 1)
                self.assertEqual(result.difficulty_modifier, -2)
                self.assertEqual(result.total, 8)
                self.assertTrue(result.avoided_risk)
                replay = resolve_species_hive_mentality_command(
                    connection, initiator_reference="player",
                    idempotency_key="hive-mentality-resist",
                    actor_public_id=actor,
                    family_group_reference="different-colony",
                    perceived_benefit="Different benefit.",
                    random_source=FixedRandom((1, 1)),
                )
                self.assertTrue(replay.replayed)
                self.assertEqual(replay.dice, (5, 4))
                self.assertEqual(
                    replay.family_group_reference, "colony-seven")

    def test_hive_mentality_failure_compels_risk_and_rejects_other_species(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                insectan = self._actor(
                    connection, "Insectan Soldier", "insectan")
                failed = resolve_species_hive_mentality_command(
                    connection, initiator_reference="player",
                    idempotency_key="hive-mentality-compelled",
                    actor_public_id=insectan,
                    family_group_reference="colony-seven",
                    perceived_benefit="Draw fire away from the queen.",
                    random_source=FixedRandom((2, 2)),
                )
                self.assertFalse(failed.avoided_risk)
                self.assertEqual(failed.effect, -3)
                human = self._actor(connection, "Human", "human")
                with self.assertRaisesRegex(ValueError, "not legal"):
                    resolve_species_hive_mentality_command(
                        connection, initiator_reference="player",
                        idempotency_key="human-hive-mentality",
                        actor_public_id=human,
                        family_group_reference="family",
                        perceived_benefit="Take a risk.",
                        random_source=FixedRandom((6, 6)),
                    )
                with self.assertRaisesRegex(ValueError, "not legal"):
                    resolve_species_hive_mentality_command(
                        connection, initiator_reference="player",
                        idempotency_key="hive-mentality-too-hard",
                        actor_public_id=insectan,
                        family_group_reference="colony-seven",
                        perceived_benefit="Risk everything.",
                        difficulty_rule_code="difficulty.formidable",
                        random_source=FixedRandom((6, 6)),
                    )

    def test_naturally_curious_uses_bounded_intelligence_check(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                connection.execute(
                    """INSERT INTO rule_species_trait_assignment
                       (species_rule_id,species_trait_rule_id,
                        assignment_order)
                       SELECT species.species_rule_id,
                              trait.species_trait_rule_id,1
                       FROM rule_species species
                       CROSS JOIN rule_species_trait trait
                       WHERE species.species_code='human'
                         AND trait.trait_code='naturally-curious'""")
                actor = self._actor(
                    connection, "Curious Explorer", "human")
                compelled = resolve_species_naturally_curious_command(
                    connection, initiator_reference="player",
                    idempotency_key="curiosity-compelled",
                    actor_public_id=actor,
                    mystery_reference="sealed-vault",
                    perceived_mystery="A sealed door hums behind the wall.",
                    difficulty_rule_code="difficulty.routine",
                    random_source=FixedRandom((2, 2)),
                )
                self.assertEqual(compelled.difficulty_modifier, 2)
                self.assertFalse(compelled.avoided_impulse)
                self.assertEqual(compelled.effect, -1)
                replay = resolve_species_naturally_curious_command(
                    connection, initiator_reference="player",
                    idempotency_key="curiosity-compelled",
                    actor_public_id=actor,
                    mystery_reference="other",
                    perceived_mystery="Changed.",
                    random_source=FixedRandom((6, 6)),
                )
                self.assertTrue(replay.replayed)
                self.assertEqual(replay.mystery_reference, "sealed-vault")
                with self.assertRaisesRegex(ValueError, "not legal"):
                    resolve_species_naturally_curious_command(
                        connection, initiator_reference="player",
                        idempotency_key="curiosity-too-hard",
                        actor_public_id=actor,
                        mystery_reference="impossible-vault",
                        perceived_mystery="An impossible mystery.",
                        difficulty_rule_code="difficulty.formidable",
                        random_source=FixedRandom((6, 6)),
                    )

    def test_low_light_vision_doubles_only_source_poor_light_contexts(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                reptilian = self._actor(
                    connection, "Reptilian Scout", "reptilian")
                result = evaluate_species_low_light_visibility_command(
                    connection, initiator_reference="player",
                    idempotency_key="low-light-moonlight",
                    actor_public_id=reptilian,
                    illumination_context="moonlight",
                    human_visibility_metres=30,
                )
                self.assertEqual(result.distance_multiplier, 2)
                self.assertEqual(result.actor_visibility_metres, 60)
                self.assertTrue(result.retains_color)
                self.assertTrue(result.retains_detail)
                replay = evaluate_species_low_light_visibility_command(
                    connection, initiator_reference="player",
                    idempotency_key="low-light-moonlight",
                    actor_public_id=reptilian,
                    illumination_context="torchlight",
                    human_visibility_metres=1,
                )
                self.assertTrue(replay.replayed)
                self.assertEqual(replay.actor_visibility_metres, 60)
                with self.assertRaisesRegex(ValueError, "not legal"):
                    evaluate_species_low_light_visibility_command(
                        connection, initiator_reference="player",
                        idempotency_key="low-light-total-dark",
                        actor_public_id=reptilian,
                        illumination_context="total-darkness",
                        human_visibility_metres=30,
                    )
                human = self._actor(
                    connection, "Human Observer", "human")
                with self.assertRaisesRegex(ValueError, "not legal"):
                    evaluate_species_low_light_visibility_command(
                        connection, initiator_reference="player",
                        idempotency_key="human-low-light",
                        actor_public_id=human,
                        illumination_context="starlight",
                        human_visibility_metres=30,
                    )
