from __future__ import annotations

import os
import unittest
import uuid

import psycopg

from engine.encounters import create_encounter_command
from engine.social_content import (PatronObjective, PatronRequirement,
                                   create_patron_brief_command,
                                   select_social_content_command)


class FixedD66:
    def __init__(self, *values): self.values = iter(values)
    def randint(self, low, high): return next(self.values)


class SocialContentTests(unittest.TestCase):
    def test_published_catalogues_and_selection_receipts(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as c:
            self.assertEqual(c.execute("SELECT count(*) FROM rule_patron_role_roll").fetchone()[0], 36)
            self.assertEqual(c.execute("SELECT count(*) FROM rule_rumor_content_roll").fetchone()[0], 36)
            self.assertEqual(c.execute("SELECT count(*) FROM src_patron_role_roll_provenance").fetchone()[0], 72)
            self.assertEqual(c.execute("SELECT count(*) FROM src_rumor_content_roll_provenance").fetchone()[0], 72)
            _, campaign_public = c.execute(
                "INSERT INTO camp_campaign(name,owner_reference) VALUES(%s,'p') RETURNING campaign_id,public_id",
                (str(uuid.uuid4()),),
            ).fetchone()
            patron = create_encounter_command(c, initiator_reference="p", idempotency_key="patron-e", campaign_public_id=str(campaign_public), encounter_type_code="patron")
            selected = select_social_content_command(c, initiator_reference="p", idempotency_key="patron-roll", encounter_public_id=patron.encounter_public_id, random_source=FixedD66(6, 6))
            self.assertEqual((selected.d66_result, selected.content_code, selected.referee_choice), (66, "referee-choice", True))
            replay = select_social_content_command(c, initiator_reference="p", idempotency_key="patron-roll", encounter_public_id=patron.encounter_public_id, random_source=FixedD66(1, 1))
            self.assertTrue(replay.replayed)
            self.assertEqual(replay.d66_result, 66)
            rumor = create_encounter_command(c, initiator_reference="p", idempotency_key="rumor-e", campaign_public_id=str(campaign_public), encounter_type_code="rumor")
            rumor_result = select_social_content_command(c, initiator_reference="p", idempotency_key="rumor-roll", encounter_public_id=rumor.encounter_public_id, random_source=FixedD66(2, 6))
            self.assertEqual(rumor_result.content_code, "information-leading-to-trap")
            with self.assertRaises(psycopg.Error):
                c.execute("UPDATE cmd_social_content_selection_receipt SET d66_result=11 WHERE command_id=(SELECT command_id FROM cmd_command WHERE public_id=%s)", (selected.command_public_id,))

    def test_reusable_patron_brief_seals_normalized_requirements_truths_and_objectives(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as c:
            _, campaign_public = c.execute("INSERT INTO camp_campaign(name,owner_reference) VALUES(%s,'p') RETURNING campaign_id,public_id", (str(uuid.uuid4()),)).fetchone()
            result = create_patron_brief_command(
                c, initiator_reference="p", idempotency_key="brief", campaign_public_id=str(campaign_public), brief_code="missing-courier",
                patron_name_reference="Port Factor", role_reference="Broker", reward_summary="Cr2000 on delivery", player_mission_summary="Locate the overdue courier and recover its dispatch case.",
                requirements=(PatronRequirement("skill", "Trace the courier route", "skill.streetwise"), PatronRequirement("resource", "Interplanetary transport")),
                truth_variants=("The courier suffered a genuine drive failure.", "A rival broker diverted the courier."),
                objectives=(PatronObjective("courier", "deliver", "Keep the dispatch case from the patron", 4), PatronObjective("rival broker", "acquire", "Obtain the dispatch case first", 5)),
                patron_d66_result=15,
            )
            self.assertEqual((result.requirement_count, result.truth_variant_count, result.npc_objective_count), (2, 2, 2))
            replay = create_patron_brief_command(c, initiator_reference="p", idempotency_key="brief", campaign_public_id=str(campaign_public), brief_code="changed", patron_name_reference="x", role_reference="x", reward_summary="x", player_mission_summary="x", requirements=(PatronRequirement("resource", "x"),), truth_variants=("x", "y"), objectives=(PatronObjective("x", "other", "x"),))
            self.assertTrue(replay.replayed)
            with self.assertRaises(psycopg.Error):
                c.execute("UPDATE camp_patron_truth_variant SET referee_summary='changed' WHERE patron_brief_revision_id=(SELECT patron_brief_revision_id FROM cmd_patron_brief_receipt WHERE command_id=(SELECT command_id FROM cmd_command WHERE public_id=%s)) AND variant_order=1", (result.command_public_id,))


if __name__ == "__main__": unittest.main()
