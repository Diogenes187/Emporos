from __future__ import annotations

import os
import unittest
from decimal import Decimal

import psycopg
from psycopg.errors import CheckViolation


@unittest.skipUnless(
    os.environ.get("BASE_CEPHEUS_DATABASE_URL"),
    "BASE_CEPHEUS_DATABASE_URL is not configured",
)
class VehicleEncounterStateTests(unittest.TestCase):
    def rule(self, connection, code, name, category):
        return connection.execute(
            """INSERT INTO rule_rule (
                   content_package_id,rule_code,name,
                   rule_category,rule_status
               )
               SELECT content_package_id,%s,%s,%s,'approved'
               FROM sys_content_package
               WHERE package_code='cepheus-engine'
               RETURNING rule_id""",
            (code, name, category),
        ).fetchone()[0]

    def fixture(self, connection, class_code="ground-car"):
        campaign = connection.execute(
            """INSERT INTO camp_campaign(name,owner_reference)
               VALUES ('Vehicle Encounter Test','referee')
               RETURNING campaign_id"""
        ).fetchone()[0]
        actor = connection.execute(
            """INSERT INTO actor_actor (
                   campaign_id,name,controller_reference
               )
               VALUES (%s,'Test Driver','player')
               RETURNING actor_id""",
            (campaign,),
        ).fetchone()[0]
        item_rule = self.rule(
            connection,
            f"item.vehicle.encounter-test-{class_code}",
            f"Vehicle Encounter Test {class_code} Item",
            "equipment",
        )
        connection.execute(
            """INSERT INTO inv_item_definition (
                   rule_id,item_kind,minimum_tech_level,
                   cost_credits
               )
               VALUES (%s,'equipment',5,10000)""",
            (item_rule,),
        )
        item = connection.execute(
            """INSERT INTO inv_item_instance (
                   campaign_id,item_rule_id,instance_name
               )
               VALUES (%s,%s,'Test Ground Car')
               RETURNING item_instance_id""",
            (campaign, item_rule),
        ).fetchone()[0]
        vehicle_class = connection.execute(
            """SELECT vehicle_class_rule_id,hull_points,
                      structure_points
               FROM vehicle_class
               WHERE class_code=%s""",
            (class_code,),
        ).fetchone()
        vehicle = connection.execute(
            """INSERT INTO vehicle_vehicle (
                   campaign_id,vehicle_class_rule_id,
                   inventory_item_instance_id,name,
                   hull_current,structure_current
               )
               VALUES (%s,%s,%s,'Test Car',%s,%s)
               RETURNING vehicle_id""",
            (
                campaign, vehicle_class[0], item,
                vehicle_class[1], vehicle_class[2],
            ),
        ).fetchone()[0]
        station = connection.execute(
            """INSERT INTO vehicle_crew_station (
                   vehicle_id,campaign_id,station_identifier,
                   station_kind
               )
               VALUES (%s,%s,'driver','driver')
               RETURNING crew_station_id""",
            (vehicle, campaign),
        ).fetchone()[0]
        assignment = connection.execute(
            """INSERT INTO vehicle_crew_assignment (
                   crew_station_id,vehicle_id,campaign_id,actor_id
               )
               VALUES (%s,%s,%s,%s)
               RETURNING crew_assignment_id""",
            (station, vehicle, campaign, actor),
        ).fetchone()[0]
        encounter_rule = connection.execute(
            """SELECT rule_id
               FROM rule_encounter_type
               WHERE encounter_type_code='routine'"""
        ).fetchone()[0]
        encounter = connection.execute(
            """INSERT INTO enc_encounter (
                   campaign_id,encounter_type_rule_id,current_mode
               )
               VALUES (%s,%s,'personal_combat')
               RETURNING encounter_id""",
            (campaign, encounter_rule),
        ).fetchone()[0]
        engagement = connection.execute(
            """INSERT INTO venc_engagement (
                   encounter_id,campaign_id
               )
               VALUES (%s,%s)
               RETURNING vehicle_engagement_id""",
            (encounter, campaign),
        ).fetchone()[0]
        force = connection.execute(
            """INSERT INTO venc_force (
                   vehicle_engagement_id,campaign_id,
                   side_code,force_name
               )
               VALUES (%s,%s,'blue','Blue Force')
               RETURNING vehicle_force_id""",
            (engagement, campaign),
        ).fetchone()[0]
        encounter_vehicle = connection.execute(
            """INSERT INTO venc_vehicle (
                   vehicle_engagement_id,campaign_id,
                   vehicle_force_id,vehicle_id,
                   initiative_current,joined_round
               )
               VALUES (%s,%s,%s,%s,9,1)
               RETURNING venc_vehicle_id""",
            (engagement, campaign, force, vehicle),
        ).fetchone()[0]
        connection.execute(
            """UPDATE venc_engagement
               SET engagement_status='active',current_round=1,
                   started_at=clock_timestamp()
               WHERE vehicle_engagement_id=%s""",
            (engagement,),
        )
        combat_round = connection.execute(
            """INSERT INTO venc_round (
                   vehicle_engagement_id,campaign_id,round_number
               )
               VALUES (%s,%s,1)
               RETURNING vehicle_combat_round_id""",
            (engagement, campaign),
        ).fetchone()[0]
        connection.execute(
            """INSERT INTO venc_vehicle_round_state (
                   vehicle_combat_round_id,
                   vehicle_engagement_id,campaign_id,
                   venc_vehicle_id,speed_kph,facing_degrees,
                   agility_dm,control_action_required
               )
               VALUES (%s,%s,%s,%s,45,90,3,'significant')""",
            (
                combat_round, engagement,
                campaign, encounter_vehicle,
            ),
        )
        crew_turn = connection.execute(
            """INSERT INTO venc_crew_turn (
                   vehicle_combat_round_id,
                   vehicle_engagement_id,campaign_id,
                   venc_vehicle_id,crew_assignment_id,
                   initiative_at_action,turn_status
               )
               VALUES (%s,%s,%s,%s,%s,9,'acting')
               RETURNING vehicle_crew_turn_id""",
            (
                combat_round, engagement, campaign,
                encounter_vehicle, assignment,
            ),
        ).fetchone()[0]
        return {
            "campaign": campaign,
            "actor": actor,
            "engagement": engagement,
            "round": combat_round,
            "vehicle": encounter_vehicle,
            "vehicle_instance": vehicle,
            "force": force,
            "turn": crew_turn,
        }

    def test_vehicle_encounter_aggregate_and_receipts(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            with connection.transaction(force_rollback=True):
                fixture = self.fixture(connection)
                weave_rule = connection.execute(
                    """SELECT action_rule_id
                       FROM rule_vehicle_combat_action
                       WHERE action_code='weave'"""
                ).fetchone()[0]
                with self.assertRaisesRegex(
                    CheckViolation,
                    "speed-based maximum",
                ):
                    with connection.transaction():
                        connection.execute(
                            """INSERT INTO venc_action (
                                   vehicle_crew_turn_id,
                                   vehicle_combat_round_id,
                                   vehicle_engagement_id,campaign_id,
                                   action_order,action_rule_id,
                                   declared_weave_number
                               )
                               VALUES (%s,%s,%s,%s,1,%s,4)""",
                            (
                                fixture["turn"], fixture["round"],
                                fixture["engagement"],
                                fixture["campaign"], weave_rule,
                            ),
                        )

                weave_action = connection.execute(
                    """INSERT INTO venc_action (
                           vehicle_crew_turn_id,
                           vehicle_combat_round_id,
                           vehicle_engagement_id,campaign_id,
                           action_order,action_rule_id,
                           declared_weave_number,action_status,
                           resolved_at
                       )
                       VALUES (
                           %s,%s,%s,%s,1,%s,3,
                           'resolved',clock_timestamp()
                       )
                       RETURNING vehicle_action_id""",
                    (
                        fixture["turn"], fixture["round"],
                        fixture["engagement"],
                        fixture["campaign"], weave_rule,
                    ),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO venc_action_resolution (
                           vehicle_action_id,action_rule_id,
                           check_required,check_total,
                           target_number,effect,succeeded
                       )
                       VALUES (%s,%s,true,10,8,2,true)""",
                    (weave_action, weave_rule),
                )
                with self.assertRaisesRegex(
                    CheckViolation, "immutable",
                ):
                    with connection.transaction():
                        connection.execute(
                            """UPDATE venc_action_resolution
                               SET effect=3
                               WHERE vehicle_action_id=%s""",
                            (weave_action,),
                        )

                ram_rule = connection.execute(
                    """SELECT action_rule_id
                       FROM rule_vehicle_combat_action
                       WHERE action_code='ram'"""
                ).fetchone()[0]
                ram_action = connection.execute(
                    """INSERT INTO venc_action (
                           vehicle_crew_turn_id,
                           vehicle_combat_round_id,
                           vehicle_engagement_id,campaign_id,
                           action_order,action_rule_id,
                           action_status,resolved_at
                       )
                       VALUES (
                           %s,%s,%s,%s,2,%s,
                           'resolved',clock_timestamp()
                       )
                       RETURNING vehicle_action_id""",
                    (
                        fixture["turn"], fixture["round"],
                        fixture["engagement"],
                        fixture["campaign"], ram_rule,
                    ),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO venc_action_resolution (
                           vehicle_action_id,action_rule_id,
                           check_required,check_total,target_number,
                           effect,succeeded,collision_generated
                       )
                       VALUES (%s,%s,true,9,8,1,true,true)""",
                    (ram_action, ram_rule),
                )
                collision = connection.execute(
                    """INSERT INTO venc_collision (
                           vehicle_engagement_id,campaign_id,
                           vehicle_combat_round_id,
                           action_resolution_id,
                           striking_vehicle_id,
                           obstacle_reference,impact_speed_kph,
                           collision_damage_dice,rolled_damage,
                           target_damage,striking_vehicle_damage
                       )
                       VALUES (
                           %s,%s,%s,%s,%s,
                           'concrete barrier',45,5,18,18,18
                       )
                       RETURNING vehicle_collision_id,
                                 speed_increment_count""",
                    (
                        fixture["engagement"], fixture["campaign"],
                        fixture["round"], ram_action,
                        fixture["vehicle"],
                    ),
                ).fetchone()
                self.assertEqual(collision[1], 5)
                connection.execute(
                    """INSERT INTO venc_collision_occupant_effect (
                           vehicle_collision_id,campaign_id,
                           actor_id,secured,damage_taken,
                           thrown_metres
                       )
                       VALUES (%s,%s,%s,true,4.5,0)""",
                    (
                        collision[0], fixture["campaign"],
                        fixture["actor"],
                    ),
                )
                effect = connection.execute(
                    """SELECT secured,damage_taken,thrown_metres
                       FROM venc_collision_occupant_effect
                       WHERE vehicle_collision_id=%s""",
                    (collision[0],),
                ).fetchone()
                self.assertEqual(
                    effect,
                    (True, Decimal("4.5"), Decimal("0")),
                )

    def test_runtime_tables_are_present(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            counts = connection.execute(
                """SELECT
                    (SELECT count(*) FROM venc_engagement),
                    (SELECT count(*) FROM venc_vehicle),
                    (SELECT count(*) FROM venc_action_resolution),
                    (SELECT count(*) FROM venc_collision)"""
            ).fetchone()
            self.assertEqual(counts, (0, 0, 0, 0))


if __name__ == "__main__":
    unittest.main()
