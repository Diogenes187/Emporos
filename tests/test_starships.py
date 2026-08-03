import os
import unittest

import psycopg

from engine.starships import check_starship_encounter_command


class FixedRandom:
    def __init__(self, values):
        self.values = iter(values)

    def randint(self, minimum, maximum):
        return next(self.values)


@unittest.skipUnless(
    os.environ.get("BASE_CEPHEUS_DATABASE_URL"),
    "requires the project PostgreSQL database",
)
class StarshipEncounterIntegrationTests(unittest.TestCase):
    def _ship(self, connection, campaign_id, class_code, name):
        item_rule = connection.execute(
            "SELECT rule_id FROM inv_item_definition ORDER BY rule_id LIMIT 1"
        ).fetchone()[0]
        item = connection.execute(
            "INSERT INTO inv_item_instance(campaign_id,item_rule_id,instance_name) VALUES(%s,%s,%s) RETURNING item_instance_id",
            (campaign_id, item_rule, f"{name} hull"),
        ).fetchone()[0]
        ship_class = connection.execute(
            "SELECT ship_class_rule_id,hull_points,structure_points FROM ship_class WHERE class_code=%s",
            (class_code,),
        ).fetchone()
        return connection.execute(
            """INSERT INTO ship_ship(campaign_id,ship_class_rule_id,inventory_item_instance_id,name,hull_current,structure_current,armor_current)
               VALUES(%s,%s,%s,%s,%s,%s,0) RETURNING ship_id""",
            (campaign_id, ship_class[0], item, name, ship_class[1], ship_class[2]),
        ).fetchone()[0]

    def test_subtype_catalogue_is_paired_complete_and_terminal(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM rule_starship_encounter_subtable").fetchone()[0], 11)
            self.assertEqual(connection.execute("SELECT count(*) FROM rule_starship_encounter_subtype_roll").fetchone()[0], 66)
            self.assertEqual(connection.execute("SELECT count(*) FROM rule_starship_encounter_result").fetchone()[0], 60)
            self.assertEqual(connection.execute("SELECT count(*) FROM rule_starship_encounter_effect").fetchone()[0], 4)
            paired = connection.execute(
                """SELECT count(*) FROM(SELECT p.subtable_code,p.roll_total
                   FROM src_starship_encounter_subtype_roll_provenance p JOIN src_locator l USING(source_locator_id)
                   JOIN src_work w USING(source_work_id) GROUP BY p.subtable_code,p.roll_total
                   HAVING count(DISTINCT w.work_code)=2) q"""
            ).fetchone()[0]
            self.assertEqual(paired, 66)
            graph = {}
            for subtable, next_subtable in connection.execute(
                """SELECT roll.subtable_code,result.next_subtable_code
                   FROM rule_starship_encounter_subtype_roll roll JOIN rule_starship_encounter_result result USING(result_code)"""
            ):
                graph.setdefault(subtable, set()).add(next_subtable)

            def reaches_terminal(subtable, path=()):
                self.assertNotIn(subtable, path)
                targets = graph[subtable]
                self.assertLessEqual(len(path), 3)
                return all(target is None or reaches_terminal(target, path + (subtable,)) for target in targets)

            for (category,) in connection.execute("SELECT category_code FROM rule_starship_encounter_category"):
                self.assertTrue(reaches_terminal(category))

    def test_contact_is_not_combat_and_failed_comms_moves_range_closer(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                campaign_public = connection.execute(
                    """INSERT INTO camp_campaign (name,owner_reference)
                       VALUES ('Starship Test','referee') RETURNING public_id"""
                ).fetchone()[0]
                result = check_starship_encounter_command(
                    connection, initiator_reference="referee",
                    idempotency_key="starship-check",
                    campaign_public_id=str(campaign_public),
                    region_context="near_planet",
                    random_source=FixedRandom((6, 4, 3, 1, 1, 3)))
                replay = check_starship_encounter_command(
                    connection, initiator_reference="referee",
                    idempotency_key="starship-check",
                    campaign_public_id=str(campaign_public),
                    region_context="deep_space",
                    chosen_category_code="hostile_vessel",
                    random_source=FixedRandom((1,)))
                self.assertTrue(result.occurred)
                self.assertEqual(result.category_code, "merchant_vessel")
                self.assertFalse(result.comms_succeeded)
                self.assertEqual(result.initial_range, "short")
                self.assertEqual(result.subtype_dice, (3,))
                self.assertEqual(result.subtype_result_code, "merchant-freighter")
                self.assertEqual(result.subtype_result_kind, "ship-class")
                self.assertTrue(replay.replayed)
                self.assertEqual(result.command_public_id, replay.command_public_id)
                mode = connection.execute(
                    "SELECT current_mode FROM enc_encounter WHERE public_id=%s",
                    (result.encounter_public_id,),
                ).fetchone()[0]
                self.assertEqual(mode, "starship")

    def test_no_contact_consumes_only_occurrence_die(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                campaign_public = connection.execute(
                    """INSERT INTO camp_campaign (name,owner_reference)
                       VALUES ('Empty Space','referee') RETURNING public_id"""
                ).fetchone()[0]
                result = check_starship_encounter_command(
                    connection, initiator_reference="referee",
                    idempotency_key="no-contact",
                    campaign_public_id=str(campaign_public),
                    region_context="deep_space",
                    random_source=FixedRandom((5,)))
                self.assertFalse(result.occurred)
                self.assertEqual(result.occurrence_dice, (5,))
                self.assertEqual(result.category_dice, ())
                self.assertEqual(result.comms_dice, ())

    def test_recursive_derelict_military_warship_chain_is_preserved(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                campaign_public = connection.execute(
                    "INSERT INTO camp_campaign(name,owner_reference) VALUES('Derelict Chain','referee') RETURNING public_id"
                ).fetchone()[0]
                result = check_starship_encounter_command(
                    connection, initiator_reference="referee", idempotency_key="derelict-chain",
                    campaign_public_id=str(campaign_public), region_context="deep_space",
                    chosen_category_code="derelict",
                    random_source=FixedRandom((6, 6, 6, 3, 6, 2)),
                )
                self.assertEqual(result.comms_dice, (6, 6))
                self.assertEqual(result.subtype_dice, (3, 6, 2))
                self.assertEqual(result.subtype_result_code, "heavy-cruiser")
                chain = connection.execute(
                    "SELECT subtable_code,result_code FROM cmd_starship_subtype_draw ORDER BY draw_sequence"
                ).fetchall()
                self.assertEqual(chain, [
                    ("derelict", "military-vessel-subtable"),
                    ("military_vessel", "warship-subtable"),
                    ("warship", "heavy-cruiser"),
                ])
                with self.assertRaisesRegex(psycopg.Error, "immutable"):
                    with connection.transaction():
                        connection.execute(
                            "UPDATE cmd_starship_subtype_draw SET roll_result=3 WHERE command_id=(SELECT command_id FROM cmd_starship_subtype_resolution_receipt WHERE encounter_id=(SELECT encounter_id FROM enc_encounter WHERE public_id=%s)) AND draw_sequence=3",
                            (result.encounter_public_id,),
                        )

    def test_referee_choice_has_no_false_subtype_resolution(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                campaign_public = connection.execute(
                    "INSERT INTO camp_campaign(name,owner_reference) VALUES('Choice','referee') RETURNING public_id"
                ).fetchone()[0]
                result = check_starship_encounter_command(
                    connection, initiator_reference="referee", idempotency_key="choice",
                    campaign_public_id=str(campaign_public), region_context="deep_space",
                    random_source=FixedRandom((6, 6, 6, 6, 6)),
                )
                self.assertTrue(result.referee_choice_required)
                self.assertIsNone(result.subtype_result_code)
                self.assertEqual(result.subtype_dice, ())

    def test_environmental_result_exposes_normalized_effect_handoff(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                campaign_public = connection.execute(
                    "INSERT INTO camp_campaign(name,owner_reference) VALUES('Dust','referee') RETURNING public_id"
                ).fetchone()[0]
                result = check_starship_encounter_command(
                    connection, initiator_reference="referee", idempotency_key="dust",
                    campaign_public_id=str(campaign_public), region_context="deep_space",
                    chosen_category_code="astrogation", random_source=FixedRandom((6, 6, 6, 4)),
                )
                handoff = connection.execute(
                    """SELECT result_kind,effect_code,sensor_skill_code,sensor_modifier,may_trigger_second_encounter
                       FROM enc_starship_contact_resolution WHERE encounter_id=(SELECT encounter_id FROM enc_encounter WHERE public_id=%s)""",
                    (result.encounter_public_id,),
                ).fetchone()
                self.assertEqual(handoff, ("phenomenon", "dust-cloud-interference", "comms", -2, True))

    def test_concrete_contact_initializes_forming_combat_at_contact_range(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                campaign_id, campaign_public = connection.execute(
                    "INSERT INTO camp_campaign(name,owner_reference) VALUES('Handoff','referee') RETURNING campaign_id,public_id"
                ).fetchone()
                result = check_starship_encounter_command(
                    connection, initiator_reference="referee", idempotency_key="handoff-contact",
                    campaign_public_id=str(campaign_public), region_context="near_planet",
                    chosen_category_code="merchant_vessel", random_source=FixedRandom((6, 6, 6, 3)),
                )
                player = self._ship(connection, campaign_id, "courier", "Player Courier")
                contact = self._ship(connection, campaign_id, "merchant-freighter", "Encounter Freighter")
                encounter_id = connection.execute(
                    "SELECT encounter_id FROM enc_encounter WHERE public_id=%s", (result.encounter_public_id,)
                ).fetchone()[0]
                engagement = connection.execute(
                    "SELECT enc_initialize_starship_contact_combat(%s,%s,%s,NULL)",
                    (encounter_id, player, contact),
                ).fetchone()[0]
                state = connection.execute(
                    """SELECT e.engagement_status,r.range_band_code,count(DISTINCT f.force_id),count(DISTINCT v.senc_vessel_id)
                       FROM senc_engagement e JOIN senc_force f USING(engagement_id,campaign_id)
                       JOIN senc_vessel v USING(engagement_id,campaign_id,force_id)
                       JOIN senc_vessel_range r USING(engagement_id,campaign_id)
                       WHERE e.engagement_id=%s GROUP BY e.engagement_status,r.range_band_code""",
                    (engagement,),
                ).fetchone()
                self.assertEqual(state, ("forming", "medium", 2, 2))
                with self.assertRaisesRegex(psycopg.Error, "unique|duplicate"):
                    with connection.transaction():
                        connection.execute(
                            "SELECT enc_initialize_starship_contact_combat(%s,%s,%s,NULL)",
                            (encounter_id, player, contact),
                        )
