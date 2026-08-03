import os
import unittest

import psycopg
from psycopg.errors import CheckViolation, ForeignKeyViolation, UniqueViolation


@unittest.skipUnless(
    os.environ.get("BASE_CEPHEUS_DATABASE_URL"),
    "requires the project PostgreSQL database",
)
class SpacecraftRelationalIntegrationTests(unittest.TestCase):
    def rule(self, connection, code, name, category="ship"):
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

    def ship(self, connection, campaign_id, suffix):
        item_rule = self.rule(
            connection,
            f"item.ship.{suffix}",
            f"{suffix} Ship Item",
            "equipment",
        )
        connection.execute(
            """INSERT INTO inv_item_definition
               (rule_id,item_kind,minimum_tech_level,cost_credits,mass_grams)
               VALUES (%s,'equipment',9,1000000,NULL)""",
            (item_rule,),
        )
        item_instance = connection.execute(
            """INSERT INTO inv_item_instance
               (campaign_id,item_rule_id,instance_name)
               VALUES (%s,%s,%s) RETURNING item_instance_id""",
            (campaign_id, item_rule, f"{suffix} hull"),
        ).fetchone()[0]
        class_rule = self.rule(
            connection, f"ship.class.{suffix}", f"{suffix} Class")
        connection.execute(
            """INSERT INTO ship_class
               (ship_class_rule_id,class_code,hull_tons,hull_points,
                structure_points,minimum_tech_level,
                construction_cost_minor,jump_rating,maneuver_rating,
                power_rating,cargo_capacity_tons)
               VALUES (%s,%s,200,4,4,9,50000000,2,1,1,80)""",
            (class_rule, suffix),
        )
        ship_id = connection.execute(
            """INSERT INTO ship_ship
               (campaign_id,ship_class_rule_id,inventory_item_instance_id,
                name,hull_current,structure_current)
               VALUES (%s,%s,%s,%s,4,4) RETURNING ship_id""",
            (campaign_id, class_rule, item_instance, f"ISS {suffix.title()}"),
        ).fetchone()[0]
        return ship_id, class_rule

    def test_ship_state_is_bounded_and_nullable_registration_is_repeatable(self):
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            with connection.transaction(force_rollback=True):
                campaign_id = self.campaign(connection, "Ships")
                first, class_rule = self.ship(connection, campaign_id, "alpha")
                second, _ = self.ship(connection, campaign_id, "beta")
                self.assertNotEqual(first, second)

                with self.assertRaisesRegex(
                    CheckViolation, "class maxima",
                ):
                    with connection.transaction():
                        connection.execute(
                            """UPDATE ship_ship SET hull_current=5
                               WHERE ship_id=%s""",
                            (first,),
                        )

                connection.execute(
                    """UPDATE ship_ship SET registration_identifier='REG-1'
                       WHERE ship_id=%s""",
                    (first,),
                )
                with self.assertRaises(UniqueViolation):
                    with connection.transaction():
                        connection.execute(
                            """UPDATE ship_ship
                               SET registration_identifier='REG-1'
                               WHERE ship_id=%s""",
                            (second,),
                        )

                component_rule = self.rule(
                    connection, "ship.component.alpha-drive", "Alpha Drive")
                connection.execute(
                    """INSERT INTO ship_component_definition
                       (component_rule_id,component_code,component_kind,
                        minimum_tech_level,unit_tons,unit_cost_minor)
                       VALUES (%s,'alpha-drive','jump_drive',9,20,1000000)""",
                    (component_rule,),
                )
                class_component = connection.execute(
                    """INSERT INTO ship_class_component
                       (ship_class_rule_id,component_rule_id,quantity,rating,
                        allocated_tons,display_order)
                       VALUES (%s,%s,1,2,20,1)
                       RETURNING ship_class_component_id""",
                    (class_rule, component_rule),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO ship_component
                       (ship_id,campaign_id,class_component_id,
                        component_rule_id,component_identifier)
                       VALUES (%s,%s,%s,%s,'jump-drive-1')""",
                    (
                        first, campaign_id, class_component,
                        component_rule,
                    ),
                )

    def test_crew_positions_enforce_campaign_ship_and_active_duty(self):
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            with connection.transaction(force_rollback=True):
                campaign_id = self.campaign(connection, "Crew")
                other_campaign = self.campaign(connection, "Other Crew")
                ship_id, _ = self.ship(connection, campaign_id, "crew")
                actor_id = self.actor(connection, campaign_id, "Pilot")
                other_actor = self.actor(
                    connection, other_campaign, "Wrong Pilot")
                position_rule = self.rule(
                    connection, "ship.crew.pilot-test", "Test Pilot")
                connection.execute(
                    """INSERT INTO ship_crew_position_definition
                       (crew_position_rule_id,position_code,position_name)
                       VALUES (%s,'pilot-test','Test Pilot')""",
                    (position_rule,),
                )
                pilot = connection.execute(
                    """INSERT INTO ship_crew_position
                       (ship_id,campaign_id,crew_position_rule_id,
                        position_identifier)
                       VALUES (%s,%s,%s,'pilot')
                       RETURNING ship_crew_position_id""",
                    (ship_id, campaign_id, position_rule),
                ).fetchone()[0]
                navigator = connection.execute(
                    """INSERT INTO ship_crew_position
                       (ship_id,campaign_id,crew_position_rule_id,
                        position_identifier)
                       VALUES (%s,%s,%s,'navigator')
                       RETURNING ship_crew_position_id""",
                    (ship_id, campaign_id, position_rule),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO ship_crew_assignment
                       (ship_crew_position_id,ship_id,campaign_id,actor_id)
                       VALUES (%s,%s,%s,%s)""",
                    (pilot, ship_id, campaign_id, actor_id),
                )
                with self.assertRaises(UniqueViolation):
                    with connection.transaction():
                        connection.execute(
                            """INSERT INTO ship_crew_assignment
                               (ship_crew_position_id,ship_id,campaign_id,
                                actor_id)
                               VALUES (%s,%s,%s,%s)""",
                            (
                                navigator, ship_id, campaign_id,
                                actor_id,
                            ),
                        )
                with self.assertRaises(ForeignKeyViolation):
                    with connection.transaction():
                        connection.execute(
                            """INSERT INTO ship_crew_assignment
                               (ship_crew_position_id,ship_id,campaign_id,
                                actor_id)
                               VALUES (%s,%s,%s,%s)""",
                            (
                                navigator, ship_id, campaign_id,
                                other_actor,
                            ),
                        )

    def test_ownership_control_damage_and_restoration_are_distinct(self):
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            with connection.transaction(force_rollback=True):
                campaign_id = self.campaign(connection, "Ship State")
                ship_id, _ = self.ship(connection, campaign_id, "state")
                owner = self.actor(connection, campaign_id, "Owner")
                captain = self.actor(connection, campaign_id, "Captain")
                connection.execute(
                    """INSERT INTO ship_legal_interest
                       (ship_id,campaign_id,interest_kind,actor_id,
                        share_basis_points)
                       VALUES (%s,%s,'ownership',%s,7500)""",
                    (ship_id, campaign_id, owner),
                )
                with self.assertRaisesRegex(
                    CheckViolation, "exceeds 100 percent",
                ):
                    with connection.transaction():
                        connection.execute(
                            """INSERT INTO ship_legal_interest
                               (ship_id,campaign_id,interest_kind,actor_id,
                                share_basis_points)
                               VALUES (%s,%s,'ownership',%s,3000)""",
                            (ship_id, campaign_id, captain),
                        )
                connection.execute(
                    """INSERT INTO ship_operational_control
                       (ship_id,campaign_id,actor_id,control_basis)
                       VALUES (%s,%s,%s,'captaincy')""",
                    (ship_id, campaign_id, captain),
                )
                damage_id = connection.execute(
                    """INSERT INTO ship_damage
                       (ship_id,campaign_id,target_kind,damage_points,
                        description)
                       VALUES (%s,%s,'hull',2,'Meteor strike')
                       RETURNING ship_damage_id""",
                    (ship_id, campaign_id),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO ship_temporary_restoration
                       (ship_damage_id,ship_id,campaign_id,restored_points,
                        restoration_method)
                       VALUES (%s,%s,%s,1,'emergency_patch')""",
                    (damage_id, ship_id, campaign_id),
                )
                status = connection.execute(
                    """SELECT d.damage_status,r.restoration_status
                       FROM ship_damage d
                       JOIN ship_temporary_restoration r
                         ON r.ship_damage_id=d.ship_damage_id
                       WHERE d.ship_damage_id=%s""",
                    (damage_id,),
                ).fetchone()
                self.assertEqual(status, ("unrepaired", "active"))
