import os
import unittest

import psycopg
from psycopg.errors import CheckViolation, ForeignKeyViolation


@unittest.skipUnless(
    os.environ.get("BASE_CEPHEUS_DATABASE_URL"),
    "requires the project PostgreSQL database",
)
class SpacecraftOperationsVehicleIntegrationTests(unittest.TestCase):
    def rule(self, connection, code, name, category):
        return connection.execute(
            """INSERT INTO rule_rule
               (content_package_id,rule_code,name,rule_category,rule_status)
               SELECT content_package_id,%s,%s,%s,'approved'
               FROM sys_content_package
               WHERE package_code='cepheus-engine'
               RETURNING rule_id""",
            (code, name, category),
        ).fetchone()[0]

    def campaign(self, connection, name):
        return connection.execute(
            """INSERT INTO camp_campaign(name,owner_reference)
               VALUES (%s,'referee') RETURNING campaign_id""",
            (name,),
        ).fetchone()[0]

    def actor(self, connection, campaign_id, name):
        return connection.execute(
            """INSERT INTO actor_actor
               (campaign_id,name,controller_reference)
               VALUES (%s,%s,'player') RETURNING actor_id""",
            (campaign_id, name),
        ).fetchone()[0]

    def location(self, connection, campaign_id, suffix):
        location_rule = self.rule(
            connection,
            f"location.type.operations-{suffix}",
            f"Operations {suffix}",
            "world",
        )
        connection.execute(
            """INSERT INTO rule_location_type
               VALUES (%s,%s,true,true)""",
            (location_rule, f"operations-{suffix}"),
        )
        return connection.execute(
            """INSERT INTO loc_location
               (campaign_id,location_type_rule_id,name)
               VALUES (%s,%s,%s) RETURNING location_id""",
            (campaign_id, location_rule, f"Port {suffix}"),
        ).fetchone()[0]

    def item_instance(self, connection, campaign_id, suffix):
        item_rule = self.rule(
            connection,
            f"item.conveyance.{suffix}",
            f"{suffix} Conveyance",
            "equipment",
        )
        connection.execute(
            """INSERT INTO inv_item_definition
               (rule_id,item_kind,minimum_tech_level,cost_credits,mass_grams)
               VALUES (%s,'equipment',9,100000,NULL)""",
            (item_rule,),
        )
        return connection.execute(
            """INSERT INTO inv_item_instance
               (campaign_id,item_rule_id,instance_name,serial_identifier)
               VALUES (%s,%s,%s,%s) RETURNING item_instance_id""",
            (campaign_id, item_rule, suffix, f"SER-{suffix}"),
        ).fetchone()[0]

    def ship(self, connection, campaign_id, location_id, suffix):
        item_instance = self.item_instance(
            connection, campaign_id, f"ship-{suffix}")
        class_rule = self.rule(
            connection, f"ship.class.ops-{suffix}",
            f"Operations {suffix} Class", "ship")
        connection.execute(
            """INSERT INTO ship_class
               (ship_class_rule_id,class_code,hull_tons,hull_points,
                structure_points,minimum_tech_level,
                construction_cost_minor,jump_rating,maneuver_rating,
                power_rating,cargo_capacity_tons)
               VALUES (%s,%s,200,4,4,9,100000000,2,1,2,80)""",
            (class_rule, f"ops-{suffix}"),
        )
        ship_id = connection.execute(
            """INSERT INTO ship_ship
               (campaign_id,ship_class_rule_id,inventory_item_instance_id,
                name,current_location_id,hull_current,structure_current)
               VALUES (%s,%s,%s,%s,%s,4,4) RETURNING ship_id""",
            (
                campaign_id, class_rule, item_instance,
                f"ISS {suffix}", location_id,
            ),
        ).fetchone()[0]
        return ship_id, item_instance

    def test_operating_catalogues_are_relational_and_provenanced(self):
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            counts = connection.execute(
                """SELECT
                   (SELECT count(*) FROM ship_crew_position_definition),
                   (SELECT count(*) FROM rule_ship_operating_cost),
                   (SELECT count(*) FROM rule_ship_maintenance_degradation),
                   (SELECT count(*) FROM rule_vehicle_chassis),
                   (SELECT count(*) FROM rule_vehicle_armor),
                   (SELECT count(*) FROM rule_vehicle_power_plant_type),
                   (SELECT count(*) FROM rule_vehicle_chassis
                    WHERE source_locator_id IS NOT NULL),
                   (SELECT count(*) FROM rule_vehicle_propulsion_type),
                   (SELECT count(*) FROM rule_vehicle_drive),
                   (SELECT count(*) FROM rule_vehicle_drive_performance),
                   (SELECT count(*) FROM rule_vehicle_propulsion_speed),
                   (SELECT count(*) FROM rule_vehicle_drive_fuel_requirement),
                   (SELECT count(*) FROM rule_vehicle_power_plant_fuel),
                   (SELECT count(*) FROM vehicle_class
                    WHERE class_code IN (
                        'air-raft','g-carrier','grav-bike','grav-floater',
                        'grav-tank','speeder','afv-tracked','atv-tracked',
                        'ground-car','stagecoach','van',
                        'tunnel-boring-machine'
                    ))"""
            ).fetchone()
            self.assertEqual(
                counts,
                (9, 9, 3, 24, 7, 10, 24, 16, 24, 292, 90, 24, 11, 12),
            )

            ground_car = connection.execute(
                """SELECT drive_code,performance,reported_top_speed,
                          reported_cruise_speed,reported_speed_unit,
                          calculation_status
                   FROM vehicle_class_propulsion propulsion
                   JOIN vehicle_class class
                     ON class.vehicle_class_rule_id=
                        propulsion.vehicle_class_rule_id
                   WHERE class.class_code='ground-car'"""
            ).fetchone()
            self.assertEqual(
                ground_car,
                (
                    "C", 1, 100, 75, "kilometre_per_hour",
                    "published_override",
                ),
            )

    def test_resource_movements_and_journey_use_share_one_ledger(self):
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            with connection.transaction(force_rollback=True):
                campaign_id = self.campaign(connection, "Ship Journey")
                origin = self.location(connection, campaign_id, "origin")
                destination = self.location(
                    connection, campaign_id, "destination")
                ship_id, item_instance = self.ship(
                    connection, campaign_id, origin, "journey")
                connection.execute(
                    """INSERT INTO ship_resource
                       (ship_id,campaign_id,resource_type_code,
                        current_quantity,capacity_quantity)
                       VALUES (%s,%s,'refined_fuel',10,20)""",
                    (ship_id, campaign_id),
                )
                first_movement = connection.execute(
                    """INSERT INTO ship_resource_movement
                       (ship_id,campaign_id,resource_type_code,
                        quantity_delta,balance_after,movement_kind)
                       VALUES (%s,%s,'refined_fuel',-4,999,'consume')
                       RETURNING resource_movement_id,balance_after""",
                    (ship_id, campaign_id),
                ).fetchone()
                self.assertEqual(first_movement[1], 6)

                journey_id = connection.execute(
                    """INSERT INTO journey_journey
                       (campaign_id,journey_kind,name,ship_id)
                       VALUES (%s,'jump','Bound Journey',%s)
                       RETURNING journey_id,conveyance_item_instance_id""",
                    (campaign_id, ship_id),
                ).fetchone()
                self.assertEqual(journey_id[1], item_instance)
                leg_id = connection.execute(
                    """INSERT INTO journey_leg
                       (journey_id,campaign_id,leg_order,
                        origin_location_id,destination_location_id,
                        travel_mode)
                       VALUES (%s,%s,1,%s,%s,'jump')
                       RETURNING journey_leg_id""",
                    (journey_id[0], campaign_id, origin, destination),
                ).fetchone()[0]
                connection.execute(
                    """UPDATE journey_journey SET journey_status='ready'
                       WHERE journey_id=%s""",
                    (journey_id[0],),
                )
                plan_id = connection.execute(
                    """INSERT INTO journey_ship_resource_plan
                       (journey_leg_id,campaign_id,ship_id,
                        resource_type_code,planned_quantity,
                        reserve_quantity,plan_status)
                       VALUES (%s,%s,%s,'refined_fuel',5,1,'reserved')
                       RETURNING journey_ship_resource_plan_id""",
                    (leg_id, campaign_id, ship_id),
                ).fetchone()[0]
                movement_id = connection.execute(
                    """INSERT INTO ship_resource_movement
                       (ship_id,campaign_id,resource_type_code,
                        quantity_delta,balance_after,movement_kind)
                       VALUES (%s,%s,'refined_fuel',-5,0,'consume')
                       RETURNING resource_movement_id""",
                    (ship_id, campaign_id),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO journey_ship_resource_use
                       VALUES (%s,%s,%s,%s,5)""",
                    (plan_id, movement_id, ship_id, campaign_id),
                )
                balance = connection.execute(
                    """SELECT current_quantity FROM ship_resource
                       WHERE ship_id=%s
                         AND resource_type_code='refined_fuel'""",
                    (ship_id,),
                ).fetchone()[0]
                self.assertEqual(balance, 1)
                with self.assertRaisesRegex(
                    CheckViolation, "capacity or balance",
                ):
                    with connection.transaction():
                        connection.execute(
                            """INSERT INTO ship_resource_movement
                               (ship_id,campaign_id,resource_type_code,
                                quantity_delta,balance_after,movement_kind)
                               VALUES (
                                   %s,%s,'refined_fuel',-2,0,'consume'
                               )""",
                            (ship_id, campaign_id),
                        )

    def test_mortgage_requires_matching_interest_and_obligation(self):
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            with connection.transaction(force_rollback=True):
                campaign_id = self.campaign(connection, "Mortgage")
                location_id = self.location(
                    connection, campaign_id, "mortgage")
                ship_id, _ = self.ship(
                    connection, campaign_id, location_id, "mortgage")
                debtor = connection.execute(
                    """INSERT INTO fin_account
                       (campaign_id,currency_code,account_code,name,
                        account_kind)
                       VALUES (%s,'CR','ship-debtor','Ship Debtor','asset')
                       RETURNING account_id""",
                    (campaign_id,),
                ).fetchone()[0]
                creditor = connection.execute(
                    """INSERT INTO fin_account
                       (campaign_id,currency_code,account_code,name,
                        account_kind)
                       VALUES (%s,'CR','bank-creditor','Bank','asset')
                       RETURNING account_id""",
                    (campaign_id,),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO fin_campaign_account
                       VALUES (%s,%s),(%s,%s)""",
                    (debtor, campaign_id, creditor, campaign_id),
                )
                interest_id = connection.execute(
                    """INSERT INTO ship_legal_interest
                       (ship_id,campaign_id,interest_kind,account_id)
                       VALUES (%s,%s,'mortgage',%s)
                       RETURNING legal_interest_id""",
                    (ship_id, campaign_id, creditor),
                ).fetchone()[0]
                obligation_id = connection.execute(
                    """INSERT INTO fin_obligation
                       (campaign_id,currency_code,debtor_account_id,
                        creditor_account_id,principal_minor,
                        obligation_kind,description)
                       VALUES (%s,'CR',%s,%s,220000,'mortgage',
                               'Ship mortgage')
                       RETURNING obligation_id""",
                    (campaign_id, debtor, creditor),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO ship_mortgage
                       (ship_id,campaign_id,legal_interest_id,
                        obligation_id,operating_cost_code,
                        cash_price_minor,financed_principal_minor,
                        total_financed_minor,payment_amount_minor,
                        term_months,opened_day)
                       VALUES (%s,%s,%s,%s,'mortgage-standard',
                               100000,100000,220000,417,480,0)""",
                    (
                        ship_id, campaign_id, interest_id,
                        obligation_id,
                    ),
                )

    def test_completed_repairs_preserve_jobs_and_close_damage(self):
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            with connection.transaction(force_rollback=True):
                campaign_id = self.campaign(connection, "Repair")
                location_id = self.location(
                    connection, campaign_id, "repair")
                ship_id, _ = self.ship(
                    connection, campaign_id, location_id, "repair")
                damage_id = connection.execute(
                    """INSERT INTO ship_damage
                       (ship_id,campaign_id,target_kind,damage_points,
                        description)
                       VALUES (%s,%s,'hull',2,'Collision damage')
                       RETURNING ship_damage_id""",
                    (ship_id, campaign_id),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO ship_repair_job
                       (ship_id,campaign_id,ship_damage_id,location_id,
                        repair_kind,repair_status,repair_points,
                        supply_tons,labor_hours,estimated_cost_minor,
                        started_at,completed_at)
                       VALUES (%s,%s,%s,%s,'self_repair','completed',
                               2,0,4,0,clock_timestamp(),
                               clock_timestamp())""",
                    (
                        ship_id, campaign_id, damage_id,
                        location_id,
                    ),
                )
                damage = connection.execute(
                    """SELECT damage_status,repaired_at IS NOT NULL
                       FROM ship_damage WHERE ship_damage_id=%s""",
                    (damage_id,),
                ).fetchone()
                self.assertEqual(damage, ("repaired", True))
                with self.assertRaisesRegex(
                    CheckViolation, "exceed recorded damage",
                ):
                    with connection.transaction():
                        connection.execute(
                            """INSERT INTO ship_repair_job
                               (ship_id,campaign_id,ship_damage_id,
                                location_id,repair_kind,repair_status,
                                repair_points,supply_tons,labor_hours,
                                estimated_cost_minor,started_at,
                                completed_at)
                               VALUES (
                                   %s,%s,%s,%s,'self_repair','completed',
                                   1,0,1,0,clock_timestamp(),
                                   clock_timestamp()
                               )""",
                            (
                                ship_id, campaign_id, damage_id,
                                location_id,
                            ),
                        )

    def test_vehicle_capacity_state_and_campaign_crew_are_enforced(self):
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            with connection.transaction(force_rollback=True):
                campaign_id = self.campaign(connection, "Vehicles")
                other_campaign = self.campaign(connection, "Other Vehicles")
                location_id = self.location(
                    connection, campaign_id, "vehicles")
                class_rule = self.rule(
                    connection, "vehicle.class.test-atv",
                    "Test ATV", "vehicle")
                connection.execute(
                    """INSERT INTO vehicle_class
                       (vehicle_class_rule_id,class_code,chassis_code,
                        minimum_tech_level,configuration,armor_code,
                        armor_rating,hull_points,structure_points,
                        allocated_spaces,cargo_spaces,
                        construction_cost_minor,construction_hours)
                       VALUES (%s,'test-atv','E',9,'closed',
                               'titanium-steel',6,2,2,100,20,
                               50000,180)""",
                    (class_rule,),
                )
                with self.assertRaisesRegex(
                    CheckViolation, "chassis spaces",
                ):
                    with connection.transaction():
                        connection.execute(
                            """UPDATE vehicle_class
                               SET cargo_spaces=21
                               WHERE vehicle_class_rule_id=%s""",
                            (class_rule,),
                        )
                item_instance = self.item_instance(
                    connection, campaign_id, "vehicle-atv")
                vehicle_id = connection.execute(
                    """INSERT INTO vehicle_vehicle
                       (campaign_id,vehicle_class_rule_id,
                        inventory_item_instance_id,name,
                        current_location_id,hull_current,
                        structure_current)
                       VALUES (%s,%s,%s,'ATV-1',%s,2,2)
                       RETURNING vehicle_id""",
                    (
                        campaign_id, class_rule, item_instance,
                        location_id,
                    ),
                ).fetchone()[0]
                with self.assertRaisesRegex(
                    CheckViolation, "class maxima",
                ):
                    with connection.transaction():
                        connection.execute(
                            """UPDATE vehicle_vehicle SET hull_current=3
                               WHERE vehicle_id=%s""",
                            (vehicle_id,),
                        )
                station_id = connection.execute(
                    """INSERT INTO vehicle_crew_station
                       (vehicle_id,campaign_id,station_identifier,
                        station_kind)
                       VALUES (%s,%s,'driver','driver')
                       RETURNING crew_station_id""",
                    (vehicle_id, campaign_id),
                ).fetchone()[0]
                wrong_actor = self.actor(
                    connection, other_campaign, "Wrong Driver")
                with self.assertRaises(ForeignKeyViolation):
                    with connection.transaction():
                        connection.execute(
                            """INSERT INTO vehicle_crew_assignment
                               (crew_station_id,vehicle_id,campaign_id,
                                actor_id)
                               VALUES (%s,%s,%s,%s)""",
                            (
                                station_id, vehicle_id,
                                campaign_id, wrong_actor,
                            ),
                        )
