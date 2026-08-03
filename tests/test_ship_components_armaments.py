import os
import unittest

import psycopg
from psycopg.errors import CheckViolation


@unittest.skipUnless(
    os.environ.get("BASE_CEPHEUS_DATABASE_URL"),
    "requires the project PostgreSQL database",
)
class ShipComponentArmamentIntegrationTests(unittest.TestCase):
    def ship_class(self, connection, suffix, tech_level=12):
        class_rule = connection.execute(
            """INSERT INTO rule_rule
               (content_package_id,rule_code,name,rule_category,rule_status)
               SELECT content_package_id,%s,%s,'ship','approved'
               FROM sys_content_package
               WHERE package_code='cepheus-engine'
               RETURNING rule_id""",
            (
                f"ship.class.armament-{suffix}",
                f"Armament {suffix} Class",
            ),
        ).fetchone()[0]
        connection.execute(
            """INSERT INTO ship_class
               (ship_class_rule_id,class_code,hull_tons,hull_points,
                structure_points,minimum_tech_level,
                construction_cost_minor,jump_rating,maneuver_rating,
                power_rating,cargo_capacity_tons)
               VALUES (%s,%s,300,6,6,%s,100000000,1,2,2,80)""",
            (class_rule, f"armament-{suffix}", tech_level),
        )
        return class_rule

    def test_component_and_armament_catalogues_are_source_governed(self):
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            counts = connection.execute(
                """SELECT
                   (SELECT count(*) FROM ship_component_definition
                    WHERE component_code IN (
                        'stateroom','low-berth','emergency-low-berth',
                        'barracks','armory','briefing-room','cargo-hold',
                        'detention-cell','fuel-scoop','fuel-processor',
                        'laboratory','launch-tube','library','luxuries',
                        'ships-locker','vault'
                    )),
                   (SELECT count(*) FROM rule_ship_hangar_option),
                   (SELECT count(*) FROM rule_ship_weapon_mount),
                   (SELECT count(*) FROM ship_weapon_definition
                    WHERE source_locator_id IS NOT NULL),
                   (SELECT count(*) FROM rule_ship_missile),
                   (SELECT count(*) FROM rule_ship_screen),
                   (SELECT count(*) FROM rule_ship_sand_ammunition)"""
            ).fetchone()
            self.assertEqual(counts, (16, 12, 6, 9, 3, 2, 1))

            beam_laser = connection.execute(
                """SELECT damage_dice_count,damage_die_sides,
                          minimum_tech_level,optimum_range_code,
                          unit_cost_minor,calculation_status,
                          special_effect_code
                   FROM ship_weapon_definition
                   WHERE weapon_code='beam-laser'"""
            ).fetchone()
            self.assertEqual(
                beam_laser,
                (
                    1, 6, 9, "medium", 1000000, "published", None,
                ),
            )
            briefing_room = connection.execute(
                """SELECT unit_tons,unit_cost_minor,tonnage_basis,
                          tonnage_factor,cost_basis,effect_code,
                          calculation_status
                   FROM ship_component_definition
                   WHERE component_code='briefing-room'"""
            ).fetchone()
            self.assertEqual(
                briefing_room,
                (
                    4, 500000, "fixed", 1, "fixed",
                    "tactics-dm-plus-1", "published",
                ),
            )

    def test_component_formulas_mounts_ammunition_and_screens_are_enforced(self):
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            with connection.transaction(force_rollback=True):
                class_rule = self.ship_class(connection, "valid")
                library_rule = connection.execute(
                    """SELECT component_rule_id
                       FROM ship_component_definition
                       WHERE component_code='library'"""
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO ship_class_component
                       (ship_class_rule_id,component_rule_id,quantity,
                        allocated_tons,display_order)
                       VALUES (%s,%s,1,4,1)""",
                    (class_rule, library_rule),
                )
                with self.assertRaisesRegex(
                    CheckViolation, "conflicts with formula",
                ):
                    with connection.transaction():
                        connection.execute(
                            """INSERT INTO ship_class_component
                               (ship_class_rule_id,component_rule_id,
                                quantity,allocated_tons,display_order)
                               VALUES (%s,%s,1,5,2)""",
                            (class_rule, library_rule),
                        )

                connection.execute(
                    """INSERT INTO ship_class_hangar_option
                       (ship_class_rule_id,hangar_identifier,
                        hangar_option_code,installation_count,
                        basis_quantity,allocated_tons,
                        installation_cost_minor)
                       VALUES (%s,'repair','repair-drones',1,1,3,600000)""",
                    (class_rule,),
                )
                with self.assertRaisesRegex(
                    CheckViolation, "conflicts with published formula",
                ):
                    with connection.transaction():
                        connection.execute(
                            """INSERT INTO ship_class_hangar_option
                               (ship_class_rule_id,hangar_identifier,
                                hangar_option_code,installation_count,
                                basis_quantity,allocated_tons,
                                installation_cost_minor)
                               VALUES (%s,'bad-probes','probe-drones',
                                       2,1,3,400000)""",
                            (class_rule,),
                        )

                turret_id = connection.execute(
                    """INSERT INTO ship_class_weapon_mount
                       (ship_class_rule_id,mount_code,mount_identifier,
                        mount_count)
                       VALUES (%s,'triple-turret','turret-bank',2)
                       RETURNING class_weapon_mount_id""",
                    (class_rule,),
                ).fetchone()[0]
                bay_id = connection.execute(
                    """INSERT INTO ship_class_weapon_mount
                       (ship_class_rule_id,mount_code,mount_identifier)
                       VALUES (%s,'bay','particle-bay')
                       RETURNING class_weapon_mount_id""",
                    (class_rule,),
                ).fetchone()[0]
                with self.assertRaisesRegex(
                    CheckViolation, "exceed tech level or hardpoints",
                ):
                    with connection.transaction():
                        connection.execute(
                            """INSERT INTO ship_class_weapon_mount
                               (ship_class_rule_id,mount_code,
                                mount_identifier)
                               VALUES (%s,'single-turret','excess')""",
                            (class_rule,),
                        )

                pulse_laser = connection.execute(
                    """SELECT weapon_rule_id
                       FROM ship_weapon_definition
                       WHERE weapon_code='pulse-laser'"""
                ).fetchone()[0]
                particle_bay = connection.execute(
                    """SELECT weapon_rule_id
                       FROM ship_weapon_definition
                       WHERE weapon_code='particle-beam-bay'"""
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO ship_class_mount_weapon
                       (class_weapon_mount_id,ship_class_rule_id,
                        weapon_slot,weapon_rule_id)
                       VALUES (%s,%s,1,%s),(%s,%s,1,%s)""",
                    (
                        turret_id, class_rule, pulse_laser,
                        bay_id, class_rule, particle_bay,
                    ),
                )
                with self.assertRaisesRegex(
                    CheckViolation, "conflicts with mount capacity",
                ):
                    with connection.transaction():
                        connection.execute(
                            """INSERT INTO ship_class_mount_weapon
                               (class_weapon_mount_id,ship_class_rule_id,
                                weapon_slot,weapon_rule_id)
                               VALUES (%s,%s,2,%s)""",
                            (bay_id, class_rule, pulse_laser),
                        )

                connection.execute(
                    """INSERT INTO ship_class_missile_store
                       (ship_class_rule_id,missile_code,missile_count,
                        allocated_tons)
                       VALUES (%s,'smart',120,10)""",
                    (class_rule,),
                )
                connection.execute(
                    """INSERT INTO ship_class_sand_store
                       (ship_class_rule_id,ammunition_code,barrel_count,
                        allocated_tons)
                       VALUES (%s,'sand-barrel',100,5)""",
                    (class_rule,),
                )
                with self.assertRaisesRegex(
                    CheckViolation, "storage tonnage is inconsistent",
                ):
                    with connection.transaction():
                        connection.execute(
                            """UPDATE ship_class_missile_store
                               SET allocated_tons=9
                               WHERE ship_class_rule_id=%s""",
                            (class_rule,),
                        )

                connection.execute(
                    """INSERT INTO ship_class_screen
                       (ship_class_rule_id,screen_code)
                       VALUES (%s,'meson-screen')""",
                    (class_rule,),
                )
                low_tech_class = self.ship_class(
                    connection, "low-tech", tech_level=11)
                with self.assertRaisesRegex(
                    CheckViolation, "below selected screen",
                ):
                    with connection.transaction():
                        connection.execute(
                            """INSERT INTO ship_class_screen
                               (ship_class_rule_id,screen_code)
                               VALUES (%s,'nuclear-damper')""",
                            (low_tech_class,),
                        )
