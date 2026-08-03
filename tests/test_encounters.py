import os
import unittest

import psycopg

from engine.characters import assign_actor_species_command
from engine.encounters import (
    add_encounter_participant_command, attempt_attitude_influence_command,
    create_encounter_command, set_encounter_attitude_command,
    transition_encounter_mode_command,
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
class EncounterCommandIntegrationTests(unittest.TestCase):
    def create_actor(self, connection, campaign_id, name, controller):
        return connection.execute(
            """INSERT INTO actor_actor
               (campaign_id,name,controller_reference)
               VALUES (%s,%s,%s) RETURNING public_id""",
            (campaign_id, name, controller),
        ).fetchone()[0]

    def assign_species(
        self, connection, actor_public_id, controller, species_code, key,
    ):
        assign_actor_species_command(
            connection, initiator_reference=controller,
            idempotency_key=key, actor_public_id=str(actor_public_id),
            species_code=species_code, assignment_kind="import",
        )

    def test_bad_first_impression_sets_cross_species_npc_starting_attitude(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                campaign_id, campaign_public = connection.execute(
                    """INSERT INTO camp_campaign (name,owner_reference)
                       VALUES ('Bad Impression','referee')
                       RETURNING campaign_id,public_id"""
                ).fetchone()
                insectan = self.create_actor(
                    connection, campaign_id, "Insectan", "player")
                human_npc = self.create_actor(
                    connection, campaign_id, "Human NPC", "referee")
                self.assign_species(
                    connection, insectan, "player", "insectan",
                    "bad-impression-insectan-species")
                self.assign_species(
                    connection, human_npc, "referee", "human",
                    "bad-impression-human-species")
                encounter = create_encounter_command(
                    connection, initiator_reference="referee",
                    idempotency_key="bad-impression-create",
                    campaign_public_id=str(campaign_public),
                    encounter_type_code="routine",
                )
                add_encounter_participant_command(
                    connection, initiator_reference="referee",
                    idempotency_key="bad-impression-add-npc",
                    encounter_public_id=encounter.encounter_public_id,
                    actor_public_id=str(human_npc),
                    participant_role="non_player_character",
                    side_code="locals",
                )
                added = add_encounter_participant_command(
                    connection, initiator_reference="referee",
                    idempotency_key="bad-impression-add-insectan",
                    encounter_public_id=encounter.encounter_public_id,
                    actor_public_id=str(insectan),
                    participant_role="player_character",
                    side_code="party",
                )
                replay = add_encounter_participant_command(
                    connection, initiator_reference="referee",
                    idempotency_key="bad-impression-add-insectan",
                    encounter_public_id=encounter.encounter_public_id,
                    actor_public_id=str(human_npc),
                    participant_role="animal", side_code="changed",
                )
                self.assertTrue(replay.replayed)
                self.assertEqual(
                    replay.command_public_id, added.command_public_id)
                attitude = connection.execute(
                    """SELECT rule.attitude_code,state.set_by
                       FROM enc_attitude_state state
                       JOIN rule_attitude rule
                         ON rule.rule_id=state.attitude_rule_id
                       JOIN actor_actor actor
                         ON actor.actor_id=state.actor_id
                       WHERE state.encounter_id=(
                           SELECT encounter_id FROM enc_encounter
                           WHERE public_id=%s
                       ) AND actor.public_id=%s""",
                    (encounter.encounter_public_id, human_npc),
                ).fetchone()
                self.assertEqual(attitude, ("unfriendly", "source_rule"))
                audit = connection.execute(
                    """SELECT prior_attitude_rule_id IS NULL,
                              reacting.name,bad_actor.name
                       FROM cmd_species_bad_first_impression_receipt receipt
                       JOIN actor_actor reacting
                         ON reacting.actor_id=receipt.reacting_actor_id
                       JOIN actor_actor bad_actor
                         ON bad_actor.actor_id=
                            receipt.bad_impression_actor_id"""
                ).fetchone()
                self.assertEqual(
                    audit, (True, "Human NPC", "Insectan"))
                override = set_encounter_attitude_command(
                    connection, initiator_reference="referee",
                    idempotency_key="bad-impression-override",
                    encounter_public_id=encounter.encounter_public_id,
                    actor_public_id=str(human_npc),
                    attitude_code="friendly",
                )
                self.assertEqual(override.attitude_code, "friendly")
                reverse = create_encounter_command(
                    connection, initiator_reference="referee",
                    idempotency_key="bad-impression-reverse-create",
                    campaign_public_id=str(campaign_public),
                    encounter_type_code="routine",
                )
                add_encounter_participant_command(
                    connection, initiator_reference="referee",
                    idempotency_key="bad-impression-reverse-insectan",
                    encounter_public_id=reverse.encounter_public_id,
                    actor_public_id=str(insectan),
                    participant_role="player_character",
                    side_code="party",
                )
                add_encounter_participant_command(
                    connection, initiator_reference="referee",
                    idempotency_key="bad-impression-reverse-npc",
                    encounter_public_id=reverse.encounter_public_id,
                    actor_public_id=str(human_npc),
                    participant_role="non_player_character",
                    side_code="locals",
                )
                reverse_attitude = connection.execute(
                    """SELECT rule.attitude_code
                       FROM enc_attitude_state state
                       JOIN rule_attitude rule
                         ON rule.rule_id=state.attitude_rule_id
                       WHERE state.encounter_id=(
                           SELECT encounter_id FROM enc_encounter
                           WHERE public_id=%s
                       )""",
                    (reverse.encounter_public_id,),
                ).fetchone()[0]
                self.assertEqual(reverse_attitude, "unfriendly")

    def test_bad_first_impression_excludes_same_species_and_player_attitudes(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                campaign_id, campaign_public = connection.execute(
                    """INSERT INTO camp_campaign (name,owner_reference)
                       VALUES ('Bad Impression Limits','referee')
                       RETURNING campaign_id,public_id"""
                ).fetchone()
                insectan_pc = self.create_actor(
                    connection, campaign_id, "Insectan PC", "player")
                insectan_npc = self.create_actor(
                    connection, campaign_id, "Insectan NPC", "referee")
                human_pc = self.create_actor(
                    connection, campaign_id, "Human PC", "player")
                human_animal = self.create_actor(
                    connection, campaign_id, "Human Animal", "referee")
                for actor, controller, species, key in (
                    (insectan_pc, "player", "insectan", "limit-insectan-pc"),
                    (insectan_npc, "referee", "insectan", "limit-insectan-npc"),
                    (human_pc, "player", "human", "limit-human-pc"),
                    (human_animal, "referee", "human", "limit-human-animal"),
                ):
                    self.assign_species(
                        connection, actor, controller, species, key)
                encounter = create_encounter_command(
                    connection, initiator_reference="referee",
                    idempotency_key="bad-impression-limits-create",
                    campaign_public_id=str(campaign_public),
                    encounter_type_code="routine",
                )
                for index, (actor, role, side) in enumerate((
                    (insectan_pc, "player_character", "party"),
                    (insectan_npc, "non_player_character", "locals"),
                    (human_pc, "player_character", "party"),
                    (human_animal, "animal", "wildlife"),
                )):
                    add_encounter_participant_command(
                        connection, initiator_reference="referee",
                        idempotency_key=f"bad-impression-limits-add-{index}",
                        encounter_public_id=encounter.encounter_public_id,
                        actor_public_id=str(actor),
                        participant_role=role, side_code=side,
                    )
                attitudes = connection.execute(
                    """SELECT actor.name,rule.attitude_code
                       FROM enc_attitude_state state
                       JOIN actor_actor actor ON actor.actor_id=state.actor_id
                       JOIN rule_attitude rule
                         ON rule.rule_id=state.attitude_rule_id
                       WHERE state.encounter_id=(
                           SELECT encounter_id FROM enc_encounter
                           WHERE public_id=%s
                       ) ORDER BY actor.name""",
                    (encounter.encounter_public_id,),
                ).fetchall()
                self.assertEqual(attitudes, [])

    def test_social_encounter_requires_explicit_idempotent_combat_transition(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                campaign_public = connection.execute(
                    """INSERT INTO camp_campaign (name,owner_reference)
                       VALUES ('Encounter Test','referee')
                       RETURNING public_id"""
                ).fetchone()[0]
                created = create_encounter_command(
                    connection, initiator_reference="referee",
                    idempotency_key="create-encounter",
                    campaign_public_id=str(campaign_public),
                    encounter_type_code="routine",
                )
                self.assertEqual(created.current_mode, "social")
                transition = transition_encounter_mode_command(
                    connection, initiator_reference="referee",
                    idempotency_key="escalate-encounter",
                    encounter_public_id=created.encounter_public_id,
                    to_mode="personal_combat",
                    reason="The NPC attacks after negotiations fail.",
                )
                replay = transition_encounter_mode_command(
                    connection, initiator_reference="referee",
                    idempotency_key="escalate-encounter",
                    encounter_public_id=created.encounter_public_id,
                    to_mode="social",
                    reason="This retry must not alter the committed transition.",
                )
                self.assertEqual(transition.from_mode, "social")
                self.assertEqual(transition.to_mode, "personal_combat")
                self.assertTrue(replay.replayed)
                self.assertEqual(
                    transition.command_public_id, replay.command_public_id)
                mode = connection.execute(
                    "SELECT current_mode FROM enc_encounter WHERE public_id=%s",
                    (created.encounter_public_id,),
                ).fetchone()[0]
                self.assertEqual(mode, "personal_combat")

    def test_social_influence_changes_npc_attitude_but_not_by_prose(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                campaign_id, campaign_public = connection.execute(
                    """INSERT INTO camp_campaign (name,owner_reference)
                       VALUES ('Social Test','referee')
                       RETURNING campaign_id,public_id"""
                ).fetchone()
                player = self.create_actor(
                    connection, campaign_id, "Player", "player")
                npc = self.create_actor(
                    connection, campaign_id, "NPC", "referee")
                encounter = create_encounter_command(
                    connection, initiator_reference="referee",
                    idempotency_key="social-create",
                    campaign_public_id=str(campaign_public),
                    encounter_type_code="routine",
                )
                add_encounter_participant_command(
                    connection, initiator_reference="referee",
                    idempotency_key="social-add-player",
                    encounter_public_id=encounter.encounter_public_id,
                    actor_public_id=str(player),
                    participant_role="player_character", side_code="party")
                add_encounter_participant_command(
                    connection, initiator_reference="referee",
                    idempotency_key="social-add-npc",
                    encounter_public_id=encounter.encounter_public_id,
                    actor_public_id=str(npc),
                    participant_role="non_player_character", side_code="locals")
                set_encounter_attitude_command(
                    connection, initiator_reference="referee",
                    idempotency_key="social-set-attitude",
                    encounter_public_id=encounter.encounter_public_id,
                    actor_public_id=str(npc), attitude_code="unfriendly")
                result = attempt_attitude_influence_command(
                    connection, initiator_reference="referee",
                    idempotency_key="social-influence",
                    encounter_public_id=encounter.encounter_public_id,
                    acting_actor_public_id=str(player),
                    target_actor_public_id=str(npc),
                    skill_modifier=4, characteristic_modifier=0,
                    random_source=FixedRandom((6, 6)))
                replay = attempt_attitude_influence_command(
                    connection, initiator_reference="referee",
                    idempotency_key="social-influence",
                    encounter_public_id=encounter.encounter_public_id,
                    acting_actor_public_id=str(player),
                    target_actor_public_id=str(npc),
                    skill_modifier=-99, characteristic_modifier=-99,
                    random_source=FixedRandom((1, 1)))
                self.assertEqual(result.initial_attitude, "unfriendly")
                self.assertEqual(result.final_attitude, "friendly")
                self.assertEqual(result.shift, 2)
                self.assertTrue(replay.replayed)
                self.assertEqual(result.command_public_id, replay.command_public_id)
