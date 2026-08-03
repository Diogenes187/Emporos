import os
import unittest

import psycopg
from psycopg.errors import CheckViolation, ForeignKeyViolation, UniqueViolation


@unittest.skipUnless(
    os.environ.get("BASE_CEPHEUS_DATABASE_URL"),
    "requires the project PostgreSQL database",
)
class LocationsRelationshipsIntegrationTests(unittest.TestCase):
    def create_campaign(self, connection, name="Relational World"):
        return connection.execute(
            """INSERT INTO camp_campaign (name,owner_reference)
               VALUES (%s,'referee') RETURNING campaign_id""",
            (name,),
        ).fetchone()[0]

    def create_rule(self, connection, code, name, category="other"):
        return connection.execute(
            """INSERT INTO rule_rule
               (content_package_id,rule_code,name,rule_category,rule_status)
               SELECT content_package_id,%s,%s,%s,'approved'
               FROM sys_content_package
               WHERE package_code='cepheus-engine'
               ORDER BY content_package_id LIMIT 1
               RETURNING rule_id""",
            (code, name, category),
        ).fetchone()[0]

    def create_location_type(
        self,
        connection,
        code,
        permits_containment=True,
        permits_actor_position=True,
    ):
        rule_id = self.create_rule(
            connection, f"location.type.{code}", code.title(), "world")
        connection.execute(
            """INSERT INTO rule_location_type
               VALUES (%s,%s,%s,%s)""",
            (
                rule_id,
                code,
                permits_containment,
                permits_actor_position,
            ),
        )
        return rule_id

    def create_location(self, connection, campaign_id, type_id, name):
        return connection.execute(
            """INSERT INTO loc_location
               (campaign_id,location_type_rule_id,name)
               VALUES (%s,%s,%s) RETURNING location_id""",
            (campaign_id, type_id, name),
        ).fetchone()[0]

    def create_actor(self, connection, campaign_id, name):
        return connection.execute(
            """INSERT INTO actor_actor
               (campaign_id,name,controller_reference)
               VALUES (%s,%s,'player') RETURNING actor_id""",
            (campaign_id, name),
        ).fetchone()[0]

    def test_containment_is_acyclic_and_actor_has_one_current_position(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                campaign_id = self.create_campaign(connection)
                location_type = self.create_location_type(
                    connection, "generic")
                root = self.create_location(
                    connection, campaign_id, location_type, "Root")
                middle = self.create_location(
                    connection, campaign_id, location_type, "Middle")
                leaf = self.create_location(
                    connection, campaign_id, location_type, "Leaf")
                other = self.create_location(
                    connection, campaign_id, location_type, "Other")
                connection.execute(
                    """INSERT INTO loc_containment
                       (campaign_id,parent_location_id,child_location_id)
                       VALUES (%s,%s,%s),(%s,%s,%s)""",
                    (campaign_id, root, middle,
                     campaign_id, middle, leaf),
                )
                with self.assertRaisesRegex(
                    CheckViolation, "containment cycle",
                ):
                    with connection.transaction():
                        connection.execute(
                            """INSERT INTO loc_containment
                               (campaign_id,parent_location_id,
                                child_location_id)
                               VALUES (%s,%s,%s)""",
                            (campaign_id, leaf, root),
                        )
                with self.assertRaises(UniqueViolation):
                    with connection.transaction():
                        connection.execute(
                            """INSERT INTO loc_containment
                               (campaign_id,parent_location_id,
                                child_location_id)
                               VALUES (%s,%s,%s)""",
                            (campaign_id, other, leaf),
                        )

                actor = self.create_actor(connection, campaign_id, "Explorer")
                connection.execute(
                    """INSERT INTO loc_actor_position
                       (campaign_id,actor_id,location_id)
                       VALUES (%s,%s,%s)""",
                    (campaign_id, actor, leaf),
                )
                with self.assertRaises(UniqueViolation):
                    with connection.transaction():
                        connection.execute(
                            """INSERT INTO loc_actor_position
                               (campaign_id,actor_id,location_id)
                               VALUES (%s,%s,%s)""",
                            (campaign_id, actor, other),
                        )

                restricted_type = self.create_location_type(
                    connection,
                    "restricted",
                    permits_containment=False,
                    permits_actor_position=False,
                )
                restricted = self.create_location(
                    connection,
                    campaign_id,
                    restricted_type,
                    "Restricted",
                )
                with self.assertRaisesRegex(
                    CheckViolation, "cannot contain locations",
                ):
                    with connection.transaction():
                        connection.execute(
                            """INSERT INTO loc_containment
                               (campaign_id,parent_location_id,
                                child_location_id)
                               VALUES (%s,%s,%s)""",
                            (campaign_id, restricted, other),
                        )
                with self.assertRaisesRegex(
                    CheckViolation, "cannot contain actor positions",
                ):
                    with connection.transaction():
                        connection.execute(
                            """INSERT INTO loc_actor_position
                               (campaign_id,actor_id,location_id)
                               VALUES (%s,%s,%s)""",
                            (campaign_id, actor, restricted),
                        )

                passage_rule = self.create_rule(
                    connection,
                    "location.connection.passage",
                    "Passage",
                    "world",
                )
                connection.execute(
                    """INSERT INTO rule_location_connection_type
                       VALUES (%s,'passage')""",
                    (passage_rule,),
                )
                connection.execute(
                    """INSERT INTO loc_connection
                       (campaign_id,from_location_id,to_location_id,
                        connection_type_rule_id,bidirectional)
                       VALUES (%s,%s,%s,%s,true)""",
                    (campaign_id, root, middle, passage_rule),
                )
                with self.assertRaises(CheckViolation):
                    with connection.transaction():
                        connection.execute(
                            """INSERT INTO loc_connection
                               (campaign_id,from_location_id,to_location_id,
                                connection_type_rule_id,bidirectional)
                               VALUES (%s,%s,%s,%s,true)""",
                            (
                                campaign_id,
                                middle,
                                root,
                                passage_rule,
                            ),
                        )

    def test_relationships_factions_and_reputation_are_campaign_scoped(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                campaign_id = self.create_campaign(connection, "First")
                other_campaign = self.create_campaign(connection, "Second")
                ally_rule = self.create_rule(
                    connection, "relationship.ally", "Ally")
                connection.execute(
                    """INSERT INTO actor_relationship_type
                       VALUES (%s,'ally',true,%s)""",
                    (ally_rule, ally_rule),
                )
                first = self.create_actor(connection, campaign_id, "First")
                second = self.create_actor(connection, campaign_id, "Second")
                outsider = self.create_actor(
                    connection, other_campaign, "Outsider")
                connection.execute(
                    """INSERT INTO actor_relationship
                       (campaign_id,source_actor_id,target_actor_id,
                        relationship_type_rule_id,relationship_strength)
                       VALUES (%s,%s,%s,%s,4)""",
                    (campaign_id, first, second, ally_rule),
                )
                with self.assertRaisesRegex(
                    CheckViolation, "canonical actor order",
                ):
                    with connection.transaction():
                        connection.execute(
                            """INSERT INTO actor_relationship
                               (campaign_id,source_actor_id,target_actor_id,
                                relationship_type_rule_id)
                               VALUES (%s,%s,%s,%s)""",
                            (campaign_id, second, first, ally_rule),
                        )
                with self.assertRaises(ForeignKeyViolation):
                    with connection.transaction():
                        connection.execute(
                            """INSERT INTO actor_relationship
                               (campaign_id,source_actor_id,target_actor_id,
                                relationship_type_rule_id)
                               VALUES (%s,%s,%s,%s)""",
                            (campaign_id, first, outsider, ally_rule),
                        )

                faction = connection.execute(
                    """INSERT INTO actor_faction (campaign_id,name)
                       VALUES (%s,'Explorers Guild') RETURNING faction_id""",
                    (campaign_id,),
                ).fetchone()[0]
                rival_faction = connection.execute(
                    """INSERT INTO actor_faction (campaign_id,name)
                       VALUES (%s,'Rival Guild') RETURNING faction_id""",
                    (campaign_id,),
                ).fetchone()[0]
                with self.assertRaisesRegex(
                    CheckViolation, "canonical faction order",
                ):
                    with connection.transaction():
                        connection.execute(
                            """INSERT INTO actor_faction_relationship
                               (campaign_id,source_faction_id,
                                target_faction_id,
                                relationship_type_rule_id)
                               VALUES (%s,%s,%s,%s)""",
                            (
                                campaign_id,
                                rival_faction,
                                faction,
                                ally_rule,
                            ),
                        )
                connection.execute(
                    """INSERT INTO actor_faction_membership
                       (campaign_id,faction_id,actor_id,role_name,standing)
                       VALUES (%s,%s,%s,'Scout',3)""",
                    (campaign_id, faction, first),
                )
                connection.execute(
                    """INSERT INTO actor_reputation
                       (campaign_id,actor_id,faction_id,reputation_value)
                       VALUES (%s,%s,%s,6)""",
                    (campaign_id, second, faction),
                )
                state = connection.execute(
                    """SELECT membership.role_name,membership.standing,
                              reputation.reputation_value
                       FROM actor_faction_membership membership
                       JOIN actor_reputation reputation
                         ON reputation.faction_id=membership.faction_id
                       WHERE membership.actor_id=%s
                         AND reputation.actor_id=%s""",
                    (first, second),
                ).fetchone()
                self.assertEqual(state, ("Scout", 3, 6))

    def test_space_map_profiles_trade_codes_and_routes_are_relational(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                campaign_id = self.create_campaign(connection)
                types = {
                    code: self.create_location_type(connection, code)
                    for code in ("sector", "subsector", "system", "world")
                }
                sector = self.create_location(
                    connection, campaign_id, types["sector"], "Spinward")
                subsector = self.create_location(
                    connection, campaign_id, types["subsector"], "March")
                first_system = self.create_location(
                    connection, campaign_id, types["system"], "Alpha")
                second_system = self.create_location(
                    connection, campaign_id, types["system"], "Beta")
                world = self.create_location(
                    connection, campaign_id, types["world"], "Alpha Prime")
                connection.execute(
                    """INSERT INTO loc_sector VALUES (%s,%s,0,0)""",
                    (sector, campaign_id),
                )
                connection.execute(
                    """INSERT INTO loc_subsector
                       VALUES (%s,%s,%s,1,1)""",
                    (subsector, campaign_id, sector),
                )
                connection.execute(
                    """INSERT INTO loc_star_system
                       (location_id,campaign_id,sector_location_id,
                        subsector_location_id,hex_column,hex_row)
                       VALUES (%s,%s,%s,%s,1,1),(%s,%s,%s,%s,2,1)""",
                    (first_system, campaign_id, sector, subsector,
                     second_system, campaign_id, sector, subsector),
                )
                connection.execute(
                    """INSERT INTO loc_celestial_body
                       (location_id,campaign_id,system_location_id,
                        body_kind,orbit_order)
                       VALUES (%s,%s,%s,'planet',1)""",
                    (world, campaign_id, first_system),
                )
                profile = connection.execute(
                    """INSERT INTO loc_world_profile
                       (location_id,campaign_id,revision_number,starport_code,
                        size_code,atmosphere_code,hydrographics_code,
                        population_code,government_code,law_level_code,
                        technology_level)
                       VALUES (%s,%s,1,'A',8,6,7,8,5,4,10)
                       RETURNING world_profile_id""",
                    (world, campaign_id),
                ).fetchone()[0]
                garden = connection.execute(
                    """SELECT rule_id FROM rule_rule
                       WHERE rule_code='world.trade-code.garden'"""
                ).fetchone()[0]
                agricultural = connection.execute(
                    """SELECT rule_id FROM rule_rule
                       WHERE rule_code='world.trade-code.agricultural'"""
                ).fetchone()[0]
                with self.assertRaisesRegex(
                    CheckViolation, "does not qualify",
                ):
                    with connection.transaction():
                        connection.execute(
                            """INSERT INTO loc_world_trade_code
                               VALUES (%s,%s,NULL)""",
                            (profile, agricultural),
                        )
                connection.execute(
                    """INSERT INTO loc_world_trade_code
                       VALUES (%s,%s,NULL)""",
                    (profile, garden),
                )
                route = connection.execute(
                    """INSERT INTO loc_star_route
                       (campaign_id,from_system_location_id,
                        to_system_location_id,distance_parsecs)
                       VALUES (%s,%s,%s,1) RETURNING star_route_id""",
                    (campaign_id, first_system, second_system),
                ).fetchone()[0]
                with self.assertRaises(CheckViolation):
                    with connection.transaction():
                        connection.execute(
                            """INSERT INTO loc_star_route
                               (campaign_id,from_system_location_id,
                                to_system_location_id,distance_parsecs)
                               VALUES (%s,%s,%s,1)""",
                            (
                                campaign_id,
                                second_system,
                                first_system,
                            ),
                        )
                projection = connection.execute(
                    """SELECT profile.starport_code,profile.technology_level,
                              trade.trade_code,route.distance_parsecs
                       FROM loc_world_profile profile
                       JOIN loc_world_trade_code world_trade
                         ON world_trade.world_profile_id=
                            profile.world_profile_id
                       JOIN loc_trade_code trade
                         ON trade.trade_code_rule_id=
                            world_trade.trade_code_rule_id
                       JOIN loc_star_route route
                         ON route.star_route_id=%s
                       WHERE profile.world_profile_id=%s""",
                    (route, profile),
                ).fetchone()
                self.assertEqual(projection, ("A", 10, "Ga", 1))


if __name__ == "__main__":
    unittest.main()
