import os
import unittest

import psycopg
from psycopg.errors import CheckViolation


@unittest.skipUnless(
    os.environ.get("BASE_CEPHEUS_DATABASE_URL"),
    "requires the project PostgreSQL database",
)
class SpaceCombatRelationalIntegrationTests(unittest.TestCase):
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

    def campaign(self, connection):
        return connection.execute(
            """INSERT INTO camp_campaign(name,owner_reference)
               VALUES ('Space Combat Test','referee')
               RETURNING campaign_id"""
        ).fetchone()[0]

    def ship(self, connection, campaign_id, suffix):
        item_rule = self.rule(
            connection,
            f"item.ship.space-combat-{suffix}",
            f"Space Combat {suffix} Item",
            "equipment",
        )
        connection.execute(
            """INSERT INTO inv_item_definition
               (rule_id,item_kind,minimum_tech_level,cost_credits)
               VALUES (%s,'equipment',9,1000000)""",
            (item_rule,),
        )
        item_id = connection.execute(
            """INSERT INTO inv_item_instance
               (campaign_id,item_rule_id,instance_name)
               VALUES (%s,%s,%s)
               RETURNING item_instance_id""",
            (campaign_id, item_rule, f"{suffix} hull"),
        ).fetchone()[0]
        class_rule = self.rule(
            connection,
            f"ship.class.space-combat-{suffix}",
            f"Space Combat {suffix} Class",
            "ship",
        )
        connection.execute(
            """INSERT INTO ship_class
               (ship_class_rule_id,class_code,hull_tons,hull_points,
                structure_points,minimum_tech_level,
                construction_cost_minor,maneuver_rating)
               VALUES (%s,%s,200,4,4,9,50000000,2)""",
            (class_rule, f"space-combat-{suffix}"),
        )
        return connection.execute(
            """INSERT INTO ship_ship
               (campaign_id,ship_class_rule_id,inventory_item_instance_id,
                name,hull_current,structure_current)
               VALUES (%s,%s,%s,%s,4,4)
               RETURNING ship_id""",
            (campaign_id, class_rule, item_id, f"ISS {suffix.title()}"),
        ).fetchone()[0]

    def crew_assignment(self, connection, campaign_id, ship_id, suffix):
        actor_id = connection.execute(
            """INSERT INTO actor_actor
               (campaign_id,name,controller_reference)
               VALUES (%s,%s,'player') RETURNING actor_id""",
            (campaign_id, f"Gunner {suffix}"),
        ).fetchone()[0]
        position_rule = connection.execute(
            """SELECT crew_position_rule_id
               FROM ship_crew_position_definition
               WHERE position_code='gunner'"""
        ).fetchone()[0]
        position_id = connection.execute(
            """INSERT INTO ship_crew_position
               (ship_id,campaign_id,crew_position_rule_id,
                position_identifier)
               VALUES (%s,%s,%s,%s)
               RETURNING ship_crew_position_id""",
            (ship_id, campaign_id, position_rule, f"gunner-{suffix}"),
        ).fetchone()[0]
        return connection.execute(
            """INSERT INTO ship_crew_assignment
               (ship_crew_position_id,ship_id,campaign_id,actor_id)
               VALUES (%s,%s,%s,%s)
               RETURNING crew_assignment_id""",
            (position_id, ship_id, campaign_id, actor_id),
        ).fetchone()[0]

    def test_catalogues_and_combat_receipts_are_relational(self):
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            counts = connection.execute(
                """SELECT
                   (SELECT count(*) FROM rule_space_range_band),
                   (SELECT count(*) FROM rule_space_combat_action),
                   (SELECT count(*) FROM rule_space_combat_procedure)"""
            ).fetchone()
            self.assertEqual(counts, (8, 30, 1))

            with connection.transaction(force_rollback=True):
                campaign_id = self.campaign(connection)
                encounter_rule = connection.execute(
                    """SELECT rule_id FROM rule_encounter_type
                       WHERE encounter_type_code='starship'"""
                ).fetchone()[0]
                encounter_id = connection.execute(
                    """INSERT INTO enc_encounter
                       (campaign_id,encounter_type_rule_id,current_mode)
                       VALUES (%s,%s,'starship')
                       RETURNING encounter_id""",
                    (campaign_id, encounter_rule),
                ).fetchone()[0]
                engagement_id = connection.execute(
                    """INSERT INTO senc_engagement
                       (encounter_id,campaign_id,procedure_code)
                       VALUES (%s,%s,'cepheus-standard')
                       RETURNING engagement_id""",
                    (encounter_id, campaign_id),
                ).fetchone()[0]

                with self.assertRaisesRegex(
                    CheckViolation, "requires two forces and vessels",
                ):
                    with connection.transaction():
                        connection.execute(
                            """UPDATE senc_engagement
                               SET engagement_status='active',
                                   started_at=clock_timestamp()
                               WHERE engagement_id=%s""",
                            (engagement_id,),
                        )

                attacker_ship = self.ship(
                    connection, campaign_id, "attacker")
                target_ship = self.ship(connection, campaign_id, "target")
                attacker_crew = self.crew_assignment(
                    connection, campaign_id, attacker_ship, "attacker")
                target_crew = self.crew_assignment(
                    connection, campaign_id, target_ship, "target")

                forces = connection.execute(
                    """INSERT INTO senc_force
                       (engagement_id,campaign_id,side_code,force_name)
                       VALUES (%s,%s,'red','Red Force'),
                              (%s,%s,'blue','Blue Force')
                       RETURNING force_id""",
                    (
                        engagement_id, campaign_id,
                        engagement_id, campaign_id,
                    ),
                ).fetchall()
                attacker_vessel = connection.execute(
                    """INSERT INTO senc_vessel
                       (engagement_id,campaign_id,force_id,ship_id,
                        initiative_current,thrust_current,joined_round)
                       VALUES (%s,%s,%s,%s,9,2,1)
                       RETURNING senc_vessel_id""",
                    (
                        engagement_id, campaign_id,
                        forces[0][0], attacker_ship,
                    ),
                ).fetchone()[0]
                target_vessel = connection.execute(
                    """INSERT INTO senc_vessel
                       (engagement_id,campaign_id,force_id,ship_id,
                        initiative_current,thrust_current,joined_round)
                       VALUES (%s,%s,%s,%s,7,1,1)
                       RETURNING senc_vessel_id""",
                    (
                        engagement_id, campaign_id,
                        forces[1][0], target_ship,
                    ),
                ).fetchone()[0]
                connection.execute(
                    """UPDATE senc_engagement
                       SET engagement_status='active',
                           started_at=clock_timestamp()
                       WHERE engagement_id=%s""",
                    (engagement_id,),
                )
                round_id = connection.execute(
                    "SELECT senc_open_next_round(%s)",
                    (engagement_id,),
                ).fetchone()[0]

                with self.assertRaisesRegex(
                    CheckViolation, "active crew aboard vessel",
                ):
                    with connection.transaction():
                        connection.execute(
                            """INSERT INTO senc_crew_turn
                               (space_combat_round_id,engagement_id,
                                campaign_id,senc_vessel_id,
                                crew_assignment_id,initiative_at_action)
                               VALUES (%s,%s,%s,%s,%s,9)""",
                            (
                                round_id, engagement_id, campaign_id,
                                attacker_vessel, target_crew,
                            ),
                        )

                crew_turn = connection.execute(
                    """INSERT INTO senc_crew_turn
                       (space_combat_round_id,engagement_id,campaign_id,
                        senc_vessel_id,crew_assignment_id,
                        initiative_at_action,turn_status)
                       VALUES (%s,%s,%s,%s,%s,9,'acting')
                       RETURNING crew_turn_id""",
                    (
                        round_id, engagement_id, campaign_id,
                        attacker_vessel, attacker_crew,
                    ),
                ).fetchone()[0]
                action_id = connection.execute(
                    """INSERT INTO senc_action
                       (crew_turn_id,space_combat_round_id,engagement_id,
                        campaign_id,action_order,action_code,
                        target_vessel_id)
                       VALUES (%s,%s,%s,%s,1,'attack',%s)
                       RETURNING space_combat_action_id""",
                    (
                        crew_turn, round_id, engagement_id,
                        campaign_id, target_vessel,
                    ),
                ).fetchone()[0]
                with self.assertRaisesRegex(
                    CheckViolation, "significant action budget spent",
                ):
                    with connection.transaction():
                        connection.execute(
                            """INSERT INTO senc_action
                               (crew_turn_id,space_combat_round_id,
                                engagement_id,campaign_id,action_order,
                                action_code,target_vessel_id)
                               VALUES (%s,%s,%s,%s,2,'attack',%s)""",
                            (
                                crew_turn, round_id, engagement_id,
                                campaign_id, target_vessel,
                            ),
                        )

                weapon_rule = self.rule(
                    connection,
                    "ship.weapon.space-combat-test",
                    "Space Combat Test Laser",
                    "ship",
                )
                connection.execute(
                    """INSERT INTO ship_weapon_definition
                       (weapon_rule_id,weapon_code,weapon_kind,
                        damage_dice_count,damage_die_sides)
                       VALUES (%s,'space-combat-test','laser',1,6)""",
                    (weapon_rule,),
                )
                attack_id = connection.execute(
                    """INSERT INTO senc_attack
                       (space_combat_action_id,engagement_id,campaign_id,
                        attacker_vessel_id,target_vessel_id,weapon_rule_id,
                        attack_total,target_number,effect,hit,
                        rolled_damage,net_damage)
                       VALUES (%s,%s,%s,%s,%s,%s,10,8,2,true,4,3)
                       RETURNING attack_id""",
                    (
                        action_id, engagement_id, campaign_id,
                        attacker_vessel, target_vessel, weapon_rule,
                    ),
                ).fetchone()[0]
                first_damage = connection.execute(
                    """INSERT INTO ship_damage
                       (ship_id,campaign_id,target_kind,damage_points,
                        description)
                       VALUES (%s,%s,'hull',2,'Laser damage')
                       RETURNING ship_damage_id""",
                    (target_ship, campaign_id),
                ).fetchone()[0]
                with self.assertRaisesRegex(
                    CheckViolation, "damage allocation is inconsistent",
                ):
                    with connection.transaction():
                        connection.execute(
                            """INSERT INTO senc_attack_damage
                               (attack_id,engagement_id,campaign_id,
                                ship_damage_id,allocation_order,
                                allocated_damage,target_ship_id)
                               VALUES (%s,%s,%s,%s,1,1,%s)""",
                            (
                                attack_id, engagement_id, campaign_id,
                                first_damage, target_ship,
                            ),
                        )
                connection.execute(
                    """INSERT INTO senc_attack_damage
                       (attack_id,engagement_id,campaign_id,ship_damage_id,
                        allocation_order,allocated_damage,target_ship_id)
                       VALUES (%s,%s,%s,%s,1,2,%s)""",
                    (
                        attack_id, engagement_id, campaign_id,
                        first_damage, target_ship,
                    ),
                )
                second_damage = connection.execute(
                    """INSERT INTO ship_damage
                       (ship_id,campaign_id,target_kind,damage_points,
                        description)
                       VALUES (%s,%s,'structure',2,'Excess laser damage')
                       RETURNING ship_damage_id""",
                    (target_ship, campaign_id),
                ).fetchone()[0]
                with self.assertRaisesRegex(
                    CheckViolation, "damage allocation is inconsistent",
                ):
                    with connection.transaction():
                        connection.execute(
                            """INSERT INTO senc_attack_damage
                               (attack_id,engagement_id,campaign_id,
                                ship_damage_id,allocation_order,
                                allocated_damage,target_ship_id)
                               VALUES (%s,%s,%s,%s,2,2,%s)""",
                            (
                                attack_id, engagement_id, campaign_id,
                                second_damage, target_ship,
                            ),
                        )
