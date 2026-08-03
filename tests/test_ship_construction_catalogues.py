import os
import unittest

import psycopg
from psycopg.errors import CheckViolation


@unittest.skipUnless(
    os.environ.get("BASE_CEPHEUS_DATABASE_URL"),
    "requires the project PostgreSQL database",
)
class ShipConstructionCatalogueIntegrationTests(unittest.TestCase):
    def rule(self, connection, code, name):
        return connection.execute(
            """INSERT INTO rule_rule
               (content_package_id,rule_code,name,rule_category,rule_status)
               SELECT content_package_id,%s,%s,'ship','approved'
               FROM sys_content_package
               WHERE package_code='cepheus-engine'
               RETURNING rule_id""",
            (code, name),
        ).fetchone()[0]

    def ship_class(self, connection):
        class_rule = self.rule(
            connection,
            "ship.class.construction-test",
            "Construction Test Class",
        )
        connection.execute(
            """INSERT INTO ship_class
               (ship_class_rule_id,class_code,hull_tons,hull_points,
                structure_points,minimum_tech_level,
                construction_cost_minor,jump_rating,maneuver_rating,
                power_rating,cargo_capacity_tons,hull_configuration,
                construction_weeks)
               VALUES (%s,'construction-test',200,4,4,9,50000000,
                       1,2,2,80,'standard',44)""",
            (class_rule,),
        )
        return class_rule

    def test_source_catalogues_are_complete_and_relational(self):
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            counts = connection.execute(
                """SELECT
                   (SELECT count(*) FROM rule_ship_hull_design),
                   (SELECT count(*) FROM rule_ship_configuration),
                   (SELECT count(*) FROM rule_ship_armor_design),
                   (SELECT count(*) FROM rule_ship_armor_option),
                   (SELECT count(*) FROM rule_ship_bridge_band),
                   (SELECT count(*) FROM rule_ship_computer),
                   (SELECT count(*) FROM rule_ship_computer_option),
                   (SELECT count(*) FROM rule_ship_software),
                   (SELECT count(*) FROM rule_ship_electronics_suite),
                   (SELECT count(*) FROM rule_ship_drive_design),
                   (SELECT count(*) FROM rule_ship_drive_performance),
                   (SELECT count(*) FROM rule_ship_power_plant_fuel)"""
            ).fetchone()
            self.assertEqual(
                counts,
                (36, 3, 3, 3, 4, 7, 2, 5, 5, 45, 449, 48),
            )

            published = connection.execute(
                """SELECT
                   (SELECT performance
                    FROM rule_ship_drive_performance
                    WHERE craft_scale='starship'
                      AND drive_code='A' AND hull_code='2'),
                   (SELECT performance
                    FROM rule_ship_drive_performance
                    WHERE craft_scale='small_craft'
                      AND drive_code='sC' AND hull_code='s3'),
                   (SELECT power_plant_cost_minor
                    FROM rule_ship_drive_design
                    WHERE craft_scale='starship' AND drive_code='Y'),
                   (SELECT minimum_hull_tons
                    FROM rule_ship_bridge_band
                    WHERE bridge_band_code='300-to-1000'),
                   (SELECT minimum_hull_tons
                    FROM rule_ship_bridge_band
                    WHERE bridge_band_code='1100-to-2000')"""
            ).fetchone()
            self.assertEqual(published, (1, 3, 182000000, 300, 1100))

    def test_class_design_enforces_hull_drives_software_and_receipts(self):
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            with connection.transaction(force_rollback=True):
                class_rule = self.ship_class(connection)
                with self.assertRaisesRegex(
                    CheckViolation, "conflicts with published hull",
                ):
                    with connection.transaction():
                        connection.execute(
                            """INSERT INTO ship_class_design_hull
                               (ship_class_rule_id,hull_code,
                                configuration_code)
                               VALUES (%s,'3','standard')""",
                            (class_rule,),
                        )

                connection.execute(
                    """INSERT INTO ship_class_design_hull
                       (ship_class_rule_id,hull_code,configuration_code,
                        armor_code,armor_increments)
                       VALUES (%s,'2','standard','titanium-steel',1)""",
                    (class_rule,),
                )
                connection.execute(
                    """INSERT INTO ship_class_drive
                       (ship_class_rule_id,drive_kind,craft_scale,
                        drive_code,performance)
                       VALUES
                       (%s,'jump','starship','A',1),
                       (%s,'maneuver','starship','B',2),
                       (%s,'power_plant','starship','B',2)""",
                    (class_rule, class_rule, class_rule),
                )
                with self.assertRaisesRegex(
                    CheckViolation, "conflicts with hull performance matrix",
                ):
                    with connection.transaction():
                        connection.execute(
                            """UPDATE ship_class_drive
                               SET drive_code='C'
                               WHERE ship_class_rule_id=%s
                                 AND drive_kind='maneuver'""",
                            (class_rule,),
                        )

                connection.execute(
                    """INSERT INTO ship_class_computer
                       (ship_class_rule_id,computer_code)
                       VALUES (%s,'model-2')""",
                    (class_rule,),
                )
                connection.execute(
                    """INSERT INTO ship_class_computer_option
                       (ship_class_rule_id,computer_option_code)
                       VALUES (%s,'bis')""",
                    (class_rule,),
                )
                connection.execute(
                    """INSERT INTO ship_class_software
                       (ship_class_rule_id,software_code,software_level,
                        allocated_rating)
                       VALUES (%s,'jump-control',2,10),
                              (%s,'evade',1,5)""",
                    (class_rule, class_rule),
                )
                with self.assertRaisesRegex(
                    CheckViolation, "exceeds tech, level, or computer rating",
                ):
                    with connection.transaction():
                        connection.execute(
                            """INSERT INTO ship_class_software
                               (ship_class_rule_id,software_code,
                                software_level,allocated_rating)
                               VALUES (%s,'fire-control',2,10)""",
                            (class_rule,),
                        )
                with self.assertRaisesRegex(
                    CheckViolation, "Cannot remove bis",
                ):
                    with connection.transaction():
                        connection.execute(
                            """DELETE FROM ship_class_computer_option
                               WHERE ship_class_rule_id=%s
                                 AND computer_option_code='bis'""",
                            (class_rule,),
                        )
                with self.assertRaisesRegex(
                    CheckViolation, "conflicts with tech or installed software",
                ):
                    with connection.transaction():
                        connection.execute(
                            """UPDATE ship_class_computer
                               SET computer_code='model-1'
                               WHERE ship_class_rule_id=%s""",
                            (class_rule,),
                        )

                locator_id = connection.execute(
                    """SELECT source_locator_id
                       FROM src_locator
                       WHERE heading_path=
                         'Ship Design and Construction > Ship Hull'
                       LIMIT 1"""
                ).fetchone()[0]
                receipt_id = connection.execute(
                    """INSERT INTO ship_class_construction_receipt
                       (ship_class_rule_id,
                        standard_design_discount_rate,
                        receipt_status,source_locator_id)
                       VALUES (%s,0.10,'complete',%s)
                       RETURNING construction_receipt_id""",
                    (class_rule, locator_id),
                ).fetchone()[0]
                line_id = connection.execute(
                    """INSERT INTO ship_class_construction_line
                       (ship_class_rule_id,line_order,line_kind,
                        reference_code,allocated_tons,cost_minor,
                        calculation_basis,source_locator_id,
                        construction_receipt_id)
                       VALUES (%s,1,'hull','2',0,8000000,
                               'published hull schedule',%s,%s)
                       RETURNING construction_line_id""",
                    (class_rule, locator_id, receipt_id),
                ).fetchone()[0]
                with self.assertRaisesRegex(
                    CheckViolation, "calculation lines are immutable",
                ):
                    with connection.transaction():
                        connection.execute(
                            """UPDATE ship_class_construction_line
                               SET cost_minor=1
                               WHERE construction_line_id=%s""",
                            (line_id,),
                        )
                with self.assertRaisesRegex(
                    CheckViolation, "exceed hull tonnage",
                ):
                    with connection.transaction():
                        connection.execute(
                            """INSERT INTO ship_class_construction_line
                               (ship_class_rule_id,line_order,line_kind,
                                reference_code,allocated_tons,cost_minor,
                                calculation_basis,source_locator_id,
                                construction_receipt_id)
                               VALUES (%s,2,'component','too-large',
                                       201,1,'capacity test',%s,%s)""",
                            (class_rule, locator_id, receipt_id),
                        )
                connection.execute(
                    """UPDATE ship_class_construction_receipt
                       SET finalized=true
                       WHERE construction_receipt_id=%s""",
                    (receipt_id,),
                )
                with self.assertRaisesRegex(
                    CheckViolation, "requires an open matching receipt",
                ):
                    with connection.transaction():
                        connection.execute(
                            """INSERT INTO ship_class_construction_line
                               (ship_class_rule_id,line_order,line_kind,
                                reference_code,allocated_tons,cost_minor,
                                calculation_basis,source_locator_id,
                                construction_receipt_id)
                               VALUES (%s,2,'other','late-line',
                                       0,0,'finalization test',%s,%s)""",
                            (class_rule, locator_id, receipt_id),
                        )
