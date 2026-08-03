import os
import unittest

import psycopg

from engine.combat_runtime import initialize_personal_combat_command
from engine.encounters import (
    add_encounter_participant_command, create_encounter_command,
    transition_encounter_mode_command,
)
from tests import test_combat_runtime as combat_tests


DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class PersonalStartingRangeTests(unittest.TestCase):
    def test_relational_mechanics_are_paired(self):
        with psycopg.connect(DSN) as connection:
            contexts = connection.execute(
                """SELECT context_code,rule.rule_code,
                          referee_decides_between_options
                   FROM rule_personal_starting_range_context context
                   LEFT JOIN rule_rule rule
                     ON rule.rule_id=context.source_default_range_rule_id
                   ORDER BY context_order""").fetchall()
            self.assertEqual(contexts, [
                ("tight_quarters", "combat.range.short", False),
                ("outdoors", "combat.range.medium", False),
                ("open_area", None, True)])
            provenance = connection.execute(
                """SELECT count(DISTINCT work.work_code),
                          count(*) FILTER (WHERE provenance.is_primary_citation)
                   FROM rule_rule rule
                   JOIN src_record_provenance provenance USING (rule_id)
                   JOIN src_locator locator USING (source_locator_id)
                   JOIN src_work work USING (source_work_id)
                   WHERE rule.rule_code='combat.starting-range'""").fetchone()
            self.assertEqual(provenance, (2, 1))

    def test_default_outdoor_range_is_stored_with_initialization(self):
        with psycopg.connect(DSN) as connection:
            with connection.transaction(force_rollback=True):
                helper = combat_tests.PersonalCombatRuntimeIntegrationTests(
                    "runTest")
                _, _, result = self._setup_for_custom_initialization(
                    connection, helper)
                self.assertEqual(
                    (result.starting_context_code, result.light_condition,
                     result.starting_range_rule_code,
                     result.starting_range_selection_basis),
                    ("outdoors", "normal", "combat.range.medium",
                     "source_default"))
                with self.assertRaises(psycopg.errors.RaiseException):
                    connection.execute(
                        "UPDATE enc_personal_combat_starting_range "
                        "SET light_condition='total_darkness'")

    def _setup_for_custom_initialization(self, connection, helper):
        campaign_id, campaign_public = connection.execute(
            """INSERT INTO camp_campaign (name,owner_reference)
               VALUES ('Starting Range','referee')
               RETURNING campaign_id,public_id""").fetchone()
        actors = []
        for index in range(2):
            actor = connection.execute(
                """INSERT INTO actor_actor
                   (campaign_id,name,controller_reference)
                   VALUES (%s,%s,'referee') RETURNING public_id""",
                (campaign_id, f"Range Actor {index}" )).fetchone()[0]
            connection.execute(
                """INSERT INTO actor_characteristic
                   (actor_id,characteristic_rule_id,maximum_value,current_value)
                   SELECT actor_id,rule_id,7,7 FROM actor_actor CROSS JOIN rule_rule
                   WHERE actor_actor.public_id=%s
                     AND rule_rule.rule_code=
                         'characteristic.dexterity'""", (actor,))
            actors.append(str(actor))
        encounter = create_encounter_command(
            connection, initiator_reference="referee",
            idempotency_key="range-create",
            campaign_public_id=str(campaign_public),
            encounter_type_code="routine")
        for index, actor in enumerate(actors):
            add_encounter_participant_command(
                connection, initiator_reference="referee",
                idempotency_key=f"range-add-{index}",
                encounter_public_id=encounter.encounter_public_id,
                actor_public_id=actor,
                participant_role="non_player_character",
                side_code="party" if index == 0 else "opposition")
        transition_encounter_mode_command(
            connection, initiator_reference="referee",
            idempotency_key="range-transition",
            encounter_public_id=encounter.encounter_public_id,
            to_mode="personal_combat", reason="Range test")
        result = initialize_personal_combat_command(
            connection, initiator_reference="referee",
            idempotency_key="range-initialize",
            encounter_public_id=encounter.encounter_public_id,
            aware_actor_public_ids=(),
            random_source=combat_tests.FixedRandom((3, 3, 4, 4)))
        return encounter.encounter_public_id, actors, result


if __name__ == "__main__":
    unittest.main()
