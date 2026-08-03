import os
import unittest
import uuid

import psycopg


@unittest.skipUnless(os.environ.get("BASE_CEPHEUS_DATABASE_URL"), "requires PostgreSQL")
class OffworldPassageTests(unittest.TestCase):
    def _ship_journey(self, connection):
        campaign = connection.execute(
            "INSERT INTO camp_campaign(name) VALUES(%s) RETURNING campaign_id",
            (f"Passage {uuid.uuid4().hex}",),
        ).fetchone()[0]
        package = connection.execute(
            "SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine'"
        ).fetchone()[0]
        item_rule = connection.execute(
            """INSERT INTO rule_rule(content_package_id,rule_code,name,rule_category,rule_status)
               VALUES(%s,%s,'Passage Hull','equipment','approved') RETURNING rule_id""",
            (package, f"item.passage-{uuid.uuid4().hex}"),
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO inv_item_definition(rule_id,item_kind,minimum_tech_level,cost_credits) VALUES(%s,'equipment',9,1)",
            (item_rule,),
        )
        item = connection.execute(
            "INSERT INTO inv_item_instance(campaign_id,item_rule_id,instance_name) VALUES(%s,%s,'Passage Hull') RETURNING item_instance_id",
            (campaign, item_rule),
        ).fetchone()[0]
        class_rule = connection.execute(
            """INSERT INTO rule_rule(content_package_id,rule_code,name,rule_category,rule_status)
               VALUES(%s,%s,'Passage Ship','ship','approved') RETURNING rule_id""",
            (package, f"ship.passage-{uuid.uuid4().hex}"),
        ).fetchone()[0]
        connection.execute(
            """INSERT INTO ship_class(ship_class_rule_id,class_code,hull_tons,hull_points,
                       structure_points,minimum_tech_level,construction_cost_minor,cargo_capacity_tons)
               VALUES(%s,%s,100,2,2,9,1,10)""",
            (class_rule, f"passage-{uuid.uuid4().hex}"),
        )
        connection.execute(
            "INSERT INTO ship_class_characteristic VALUES(%s,'staterooms',1),(%s,'low_berths',1)",
            (class_rule, class_rule),
        )
        ship = connection.execute(
            """INSERT INTO ship_ship(campaign_id,ship_class_rule_id,inventory_item_instance_id,
                       name,hull_current,structure_current)
               VALUES(%s,%s,%s,'Passage Ship',2,2) RETURNING ship_id""",
            (campaign, class_rule, item),
        ).fetchone()[0]
        journey = connection.execute(
            "INSERT INTO journey_journey(campaign_id,journey_kind,name,ship_id) VALUES(%s,'commercial','Passage Run',%s) RETURNING journey_id",
            (campaign, ship),
        ).fetchone()[0]
        return campaign, ship, journey

    def _actor(self, connection, campaign, name):
        return connection.execute(
            "INSERT INTO actor_actor(campaign_id,name,controller_reference) VALUES(%s,%s,'test') RETURNING actor_id",
            (campaign, name),
        ).fetchone()[0]

    def _task(self, connection, actor, characteristic_code, skill_code, difficulty_code,
              die_one, die_two, circumstance=0):
        command = connection.execute(
            """INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key,
                       command_status,completed_at)
               VALUES('resolve_actor_task','test',%s,'completed',clock_timestamp()) RETURNING command_id""",
            (uuid.uuid4().hex,),
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO cmd_random_draw(command_id,draw_group,draw_order,die_sides,result) VALUES(%s,'task',1,6,%s),(%s,'task',2,6,%s)",
            (command, die_one, command, die_two),
        )
        characteristic = connection.execute(
            "SELECT rule_id FROM rule_rule WHERE rule_code=%s", (characteristic_code,)
        ).fetchone()[0]
        difficulty, difficulty_modifier = connection.execute(
            """SELECT difficulty.rule_id,difficulty.modifier FROM rule_difficulty difficulty
               JOIN rule_rule rule USING(rule_id) WHERE rule.rule_code=%s""",
            (difficulty_code,),
        ).fetchone()
        skill = None if skill_code is None else connection.execute(
            "SELECT rule_id FROM rule_rule WHERE rule_code=%s", (skill_code,)
        ).fetchone()[0]
        total = die_one + die_two + difficulty_modifier + circumstance
        connection.execute(
            """INSERT INTO cmd_actor_task_receipt(command_id,actor_id,characteristic_rule_id,
                       skill_rule_id,difficulty_rule_id,skill_modifier,characteristic_modifier,
                       difficulty_modifier,circumstance_modifier,species_modifier,check_total,
                       target_number,effect,succeeded)
               VALUES(%s,%s,%s,%s,%s,0,0,%s,%s,0,%s,8,%s,%s)""",
            (command, actor, characteristic, skill, difficulty, difficulty_modifier,
             circumstance, total, total - 8, total >= 8),
        )
        return command, total - 8

    def test_published_passage_and_assistance_catalogue(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            self.assertEqual(
                connection.execute(
                    "SELECT passage_class,single_fare_credits FROM rule_passage_operation ORDER BY passage_class"
                ).fetchall(),
                [("high", 10000), ("low", 1000), ("middle", 8000),
                 ("stowaway", 0), ("working", None)],
            )
            self.assertEqual(
                connection.execute(
                    "SELECT assistance_modifier FROM rule_task_assistance_effect ORDER BY effect_minimum NULLS FIRST"
                ).fetchall(),
                [(-2,), (-1,), (1,), (2,)],
            )
            self.assertEqual(
                connection.execute(
                    """SELECT rule.rule_code,count(DISTINCT work.work_code)
                       FROM src_record_provenance provenance JOIN rule_rule rule USING(rule_id)
                       JOIN src_locator locator USING(source_locator_id)
                       JOIN src_work work ON work.source_work_id=locator.source_work_id
                       WHERE rule.rule_code IN('task.aiding-another','travel.ship-passage-operations')
                       GROUP BY rule.rule_code ORDER BY rule.rule_code"""
                ).fetchall(),
                [("task.aiding-another", 2), ("travel.ship-passage-operations", 2)],
            )

    def test_accommodation_capacity_manifest_and_immutability(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                campaign, ship, journey = self._ship_journey(connection)
                steward = self._actor(connection, campaign, "Steward")
                high_one = self._actor(connection, campaign, "High One")
                high_two = self._actor(connection, campaign, "High Two")
                low = self._actor(connection, campaign, "Low")
                for actor in (high_one, high_two, low):
                    connection.execute(
                        "INSERT INTO journey_participant(journey_id,campaign_id,actor_id,participant_role) VALUES(%s,%s,%s,'passenger')",
                        (journey, campaign, actor),
                    )
                excess_baggage = self._actor(connection, campaign, "Excess Baggage")
                connection.execute(
                    "INSERT INTO journey_participant(journey_id,campaign_id,actor_id,participant_role) VALUES(%s,%s,%s,'passenger')",
                    (journey, campaign, excess_baggage),
                )
                with self.assertRaisesRegex(psycopg.errors.CheckViolation, "baggage"):
                    with connection.transaction():
                        connection.execute(
                            """INSERT INTO journey_passage(journey_id,campaign_id,actor_id,
                                       passage_class,fare_minor,fare_basis,baggage_mass_kg)
                               VALUES(%s,%s,%s,'high',10000,'paid-single',1001)""",
                            (journey, campaign, excess_baggage),
                        )
                steward_skill = connection.execute(
                    "SELECT rule_id FROM rule_rule WHERE rule_code='skill.steward'"
                ).fetchone()[0]
                connection.execute("INSERT INTO actor_skill VALUES(%s,%s,0)", (steward, steward_skill))
                steward_rule = connection.execute(
                    "SELECT crew_position_rule_id FROM ship_crew_position_definition WHERE position_code='steward'"
                ).fetchone()[0]
                position = connection.execute(
                    """INSERT INTO ship_crew_position(ship_id,campaign_id,crew_position_rule_id,position_identifier)
                       VALUES(%s,%s,%s,'Steward 1') RETURNING ship_crew_position_id""",
                    (ship, campaign, steward_rule),
                ).fetchone()[0]
                connection.execute(
                    "INSERT INTO ship_crew_assignment(ship_crew_position_id,ship_id,campaign_id,actor_id) VALUES(%s,%s,%s,%s)",
                    (position, ship, campaign, steward),
                )
                passages = []
                for actor, passage_class, fare, basis, status in (
                    (high_one, "high", 8000, "paid-double", "booked"),
                    (high_two, "high", 8000, "paid-double", "booked"),
                    (low, "low", 1000, "paid-single", "boarded"),
                ):
                    passages.append(connection.execute(
                        """INSERT INTO journey_passage(journey_id,campaign_id,actor_id,passage_class,
                                   fare_minor,fare_basis,passage_status)
                           VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING journey_passage_id""",
                        (journey, campaign, actor, passage_class, fare, basis, status),
                    ).fetchone()[0])
                for passage, kind, unit, occupancy in (
                    (passages[0], "stateroom", "S1", "double"),
                    (passages[1], "stateroom", "S1", "double"),
                    (passages[2], "low-berth", "L1", "single"),
                ):
                    connection.execute(
                        """INSERT INTO journey_passage_accommodation_assignment
                           (journey_passage_id,campaign_id,journey_id,ship_id,accommodation_kind,
                            unit_identifier,occupancy_mode) VALUES(%s,%s,%s,%s,%s,%s,%s)""",
                        (passage, campaign, journey, ship, kind, unit, occupancy),
                    )
                connection.execute(
                    """INSERT INTO journey_passage_manifest_receipt
                       (journey_id,campaign_id,ship_id,high_passengers,middle_passengers,low_passengers,
                        stateroom_units_used,low_berths_used,steward_level_quanta,steward_quanta_required)
                       VALUES(%s,%s,%s,2,0,1,1,1,1,1)""",
                    (journey, campaign, ship),
                )
                with self.assertRaisesRegex(psycopg.Error, "immutable"):
                    with connection.transaction():
                        connection.execute(
                            "UPDATE journey_passage_manifest_receipt SET low_passengers=0 WHERE journey_id=%s",
                            (journey,),
                        )

    def test_low_passage_revival_applies_aid_and_death_state(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                campaign, _, journey = self._ship_journey(connection)
                passenger = self._actor(connection, campaign, "Low Passenger")
                medic = self._actor(connection, campaign, "Medic")
                connection.execute(
                    """INSERT INTO actor_skill(actor_id,skill_rule_id,skill_level)
                       SELECT %s,rule_id,0 FROM rule_rule WHERE rule_code='skill.medicine'""",
                    (medic,),
                )
                connection.execute(
                    "INSERT INTO journey_participant(journey_id,campaign_id,actor_id,participant_role) VALUES(%s,%s,%s,'passenger')",
                    (journey, campaign, passenger),
                )
                passage = connection.execute(
                    """INSERT INTO journey_passage(journey_id,campaign_id,actor_id,passage_class,
                               fare_minor,fare_basis,passage_status)
                       VALUES(%s,%s,%s,'low',1000,'paid-single','boarded') RETURNING journey_passage_id""",
                    (journey, campaign, passenger),
                ).fetchone()[0]
                helper, helper_effect = self._task(
                    connection, medic, "characteristic.education", "skill.medicine",
                    "difficulty.routine", 3, 3,
                )
                leader, _ = self._task(
                    connection, passenger, "characteristic.endurance", None,
                    "difficulty.easy", 1, 2, circumstance=1,
                )
                aid = connection.execute(
                    """INSERT INTO cmd_task_assistance_receipt
                       (leader_task_command_id,helper_task_command_id,assistance_context,
                        assistance_mode,helper_effect,assistance_effect_code,assistance_modifier,
                        referee_authorized)
                       VALUES(%s,%s,'low-passage-revival','source-prescribed-check',%s,
                              'success',1,true) RETURNING task_assistance_receipt_id""",
                    (leader, helper, helper_effect),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO journey_low_passage_revival_receipt
                       (journey_passage_id,campaign_id,passenger_actor_id,passenger_task_command_id,
                        task_assistance_receipt_id,assistance_modifier,passenger_succeeded,
                        passage_status_before,passage_status_after,passage_version_before,passage_version_after)
                       VALUES(%s,%s,%s,%s,%s,1,true,'boarded','completed',1,2)""",
                    (passage, campaign, passenger, leader, aid),
                )
                self.assertEqual(connection.execute(
                    "SELECT passage_status,concurrency_version FROM journey_passage WHERE journey_passage_id=%s",
                    (passage,),
                ).fetchone(), ("completed", 2))
                self.assertEqual(connection.execute(
                    "SELECT count(*) FROM actor_low_passage_death_state WHERE actor_id=%s", (passenger,)
                ).fetchone()[0], 0)

                doomed = self._actor(connection, campaign, "Doomed Passenger")
                connection.execute(
                    "INSERT INTO journey_participant(journey_id,campaign_id,actor_id,participant_role) VALUES(%s,%s,%s,'passenger')",
                    (journey, campaign, doomed),
                )
                doomed_passage = connection.execute(
                    """INSERT INTO journey_passage(journey_id,campaign_id,actor_id,passage_class,
                               fare_minor,fare_basis,passage_status)
                       VALUES(%s,%s,%s,'low',1000,'paid-single','boarded') RETURNING journey_passage_id""",
                    (journey, campaign, doomed),
                ).fetchone()[0]
                failed, _ = self._task(
                    connection, doomed, "characteristic.endurance", None,
                    "difficulty.easy", 1, 1,
                )
                connection.execute(
                    """INSERT INTO journey_low_passage_revival_receipt
                       (journey_passage_id,campaign_id,passenger_actor_id,passenger_task_command_id,
                        assistance_modifier,passenger_succeeded,passage_status_before,
                        passage_status_after,passage_version_before,passage_version_after)
                       VALUES(%s,%s,%s,%s,0,false,'boarded','failed_revival',1,2)""",
                    (doomed_passage, campaign, doomed, failed),
                )
                self.assertEqual(connection.execute(
                    "SELECT journey_passage_id FROM actor_low_passage_death_state WHERE actor_id=%s",
                    (doomed,),
                ).fetchone()[0], doomed_passage)
