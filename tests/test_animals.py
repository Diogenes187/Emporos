import os
import unittest

import psycopg

from engine.animals import (
    resolve_animal_reaction_command, set_animal_reaction_context_command,
)
from engine.encounters import (
    add_encounter_participant_command, create_encounter_command,
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
class AnimalReactionIntegrationTests(unittest.TestCase):
    def test_chaser_overlap_requires_referee_and_does_not_start_combat(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                campaign_id, campaign_public = connection.execute(
                    """INSERT INTO camp_campaign (name,owner_reference)
                       VALUES ('Animal Test','referee')
                       RETURNING campaign_id,public_id"""
                ).fetchone()
                player = connection.execute(
                    """INSERT INTO actor_actor
                       (campaign_id,name,controller_reference)
                       VALUES (%s,'Player','player') RETURNING public_id""",
                    (campaign_id,),
                ).fetchone()[0]
                animal_id, animal_public = connection.execute(
                    """INSERT INTO actor_actor
                       (campaign_id,name,controller_reference)
                       VALUES (%s,'Kharu','referee')
                       RETURNING actor_id,public_id""", (campaign_id,)
                ).fetchone()
                connection.execute(
                    """INSERT INTO actor_animal_profile
                       (actor_id,subtype_rule_id,creature_definition_code)
                       SELECT %s,rule_id,'creature.kharu'
                       FROM rule_rule
                       WHERE rule_code='encounter.animal-subtype.chaser'""",
                    (animal_id,))
                encounter = create_encounter_command(
                    connection, initiator_reference="referee",
                    idempotency_key="animal-create",
                    campaign_public_id=str(campaign_public),
                    encounter_type_code="animal")
                self.assertEqual(encounter.current_mode, "animal_reaction")
                for key, actor, role, side in (
                    ("animal-player", player, "player_character", "party"),
                    ("animal-kharu", animal_public, "animal", "wildlife"),
                ):
                    add_encounter_participant_command(
                        connection, initiator_reference="referee",
                        idempotency_key=key,
                        encounter_public_id=encounter.encounter_public_id,
                        actor_public_id=str(actor), participant_role=role,
                        side_code=side)
                set_animal_reaction_context_command(
                    connection, initiator_reference="referee",
                    idempotency_key="animal-context",
                    encounter_public_id=encounter.encounter_public_id,
                    animal_actor_public_id=str(animal_public),
                    animals_outnumber_characters=True,
                    animal_has_surprise=False, animal_is_surprised=False,
                    animal_bigger_than_character=False, attack_possible=True)
                result = resolve_animal_reaction_command(
                    connection, initiator_reference="referee",
                    idempotency_key="animal-react",
                    encounter_public_id=encounter.encounter_public_id,
                    animal_actor_public_id=str(animal_public),
                    provocation_number=1,
                    random_source=FixedRandom((2, 3)))
                replay = resolve_animal_reaction_command(
                    connection, initiator_reference="referee",
                    idempotency_key="animal-react",
                    encounter_public_id=encounter.encounter_public_id,
                    animal_actor_public_id=str(animal_public),
                    provocation_number=99,
                    random_source=FixedRandom((6, 6)))
                self.assertEqual(result.outcome, "requires_referee")
                self.assertTrue(result.attack_condition_met)
                self.assertTrue(result.flee_condition_met)
                self.assertTrue(replay.replayed)
                mode = connection.execute(
                    "SELECT current_mode FROM enc_encounter WHERE public_id=%s",
                    (encounter.encounter_public_id,),
                ).fetchone()[0]
                self.assertEqual(mode, "animal_reaction")
