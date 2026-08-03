import os
import unittest

import psycopg
from psycopg.errors import CheckViolation


@unittest.skipUnless(
    os.environ.get("BASE_CEPHEUS_DATABASE_URL"),
    "requires the project PostgreSQL database",
)
class CommonVesselIntegrationTests(unittest.TestCase):
    def test_all_published_common_vessels_have_relational_profiles(self):
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            counts = connection.execute(
                """SELECT
                   count(*) FILTER (WHERE craft_scale='starship'),
                   count(*) FILTER (WHERE craft_scale='small_craft'),
                   count(*) FILTER (
                       WHERE source_locator_id IS NOT NULL
                         AND standard_design
                   )
                   FROM ship_class"""
            ).fetchone()
            self.assertEqual(counts, (18, 6, 24))

            fighter = connection.execute(
                """SELECT hull_tons,hull_points,structure_points,
                          construction_cost_minor,cargo_capacity_tons
                   FROM ship_class
                   WHERE class_code='fighter'"""
            ).fetchone()
            self.assertEqual(fighter, (10, 0, 1, 10841000, 0))

            raider = connection.execute(
                """SELECT class.hull_points,hardpoints.characteristic_value,
                          jump_drive.drive_code,maneuver_drive.drive_code
                   FROM ship_class class
                   JOIN ship_class_characteristic hardpoints
                     ON hardpoints.ship_class_rule_id=class.ship_class_rule_id
                    AND hardpoints.characteristic_code='hardpoints'
                   JOIN ship_class_drive jump_drive
                     ON jump_drive.ship_class_rule_id=class.ship_class_rule_id
                    AND jump_drive.drive_kind='jump'
                   JOIN ship_class_drive maneuver_drive
                     ON maneuver_drive.ship_class_rule_id=
                        class.ship_class_rule_id
                    AND maneuver_drive.drive_kind='maneuver'
                   WHERE class.class_code='raider'"""
            ).fetchone()
            self.assertEqual(raider, (12, 6, "D", "M"))

    def test_hulls_drives_computers_armor_and_conflicts_are_explicit(self):
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            counts = connection.execute(
                """SELECT
                   (SELECT count(*) FROM ship_class_design_hull),
                   (SELECT count(*) FROM ship_class_drive),
                   (SELECT count(*) FROM ship_class_computer),
                   (SELECT count(*) FROM ship_class_electronics),
                   (SELECT count(*) FROM ship_class_published_armor),
                   (SELECT count(*) FROM ship_class_computer_option),
                   (SELECT count(*) FROM ship_class_source_assertion
                     WHERE assertion_status='unresolved_conflict')"""
            ).fetchone()
            self.assertEqual(counts, (24, 64, 24, 24, 18, 10, 0))

            destroyer = connection.execute(
                """SELECT drive_kind,drive_code,performance,validation_status
                   FROM ship_class_drive drive
                   JOIN ship_class class
                     ON class.ship_class_rule_id=drive.ship_class_rule_id
                   WHERE class.class_code='destroyer'
                     AND drive_kind<>'power_plant'
                   ORDER BY drive_kind"""
            ).fetchall()
            self.assertEqual(
                destroyer,
                [
                    ("jump", "H", 2, "validated"),
                    ("maneuver", "N", 4, "validated"),
                ],
            )

            with connection.transaction(force_rollback=True):
                with self.assertRaises(CheckViolation):
                    connection.execute(
                        """UPDATE ship_class_drive
                           SET drive_code='D'
                           WHERE ship_class_rule_id=(
                               SELECT ship_class_rule_id
                               FROM ship_class
                               WHERE class_code='destroyer'
                           )
                             AND drive_kind='jump'"""
                    )

    def test_published_armaments_ammunition_and_screens_are_normalized(self):
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            counts = connection.execute(
                """SELECT
                   (SELECT count(*) FROM ship_class_weapon_mount),
                   (SELECT count(*) FROM ship_class_mount_weapon),
                   (SELECT count(*) FROM ship_class_missile_store),
                   (SELECT sum(missile_count)
                      FROM ship_class_missile_store),
                   (SELECT sum(barrel_count)
                      FROM ship_class_sand_store),
                   (SELECT count(*) FROM ship_class_screen)"""
            ).fetchone()
            self.assertEqual(counts, (25, 63, 8, 8340, 100, 2))

            dreadnought = connection.execute(
                """SELECT sum(mount_count*mount.hardpoints_used)
                   FROM ship_class_weapon_mount selected
                   JOIN rule_ship_weapon_mount mount
                     ON mount.mount_code=selected.mount_code
                   JOIN ship_class class
                     ON class.ship_class_rule_id=selected.ship_class_rule_id
                   WHERE class.class_code='dreadnought'"""
            ).fetchone()[0]
            self.assertEqual(dreadnought, 50)

            with connection.transaction(force_rollback=True):
                with self.assertRaisesRegex(
                    CheckViolation, "hardpoints",
                ):
                    connection.execute(
                        """INSERT INTO ship_class_weapon_mount
                           (ship_class_rule_id,mount_code,
                            mount_identifier,mount_count)
                           SELECT ship_class_rule_id,'single-turret',
                                  'illegal-second-mount',1
                           FROM ship_class
                           WHERE class_code='fighter'"""
                    )

    def test_accommodation_components_and_source_gaps_are_explicit(self):
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            counts = connection.execute(
                """SELECT
                   (SELECT count(*) FROM ship_component_definition),
                   (SELECT count(*) FROM ship_class_component),
                   (SELECT count(*)
                      FROM ship_class_catalogue_completeness
                     WHERE is_structurally_complete),
                   (SELECT sum(unresolved_source_assertions)
                      FROM ship_class_catalogue_completeness),
                   (SELECT count(*)
                      FROM ship_class_armament_declaration)"""
            ).fetchone()
            self.assertEqual(counts, (23, 122, 24, 0, 24))

            dreadnought = connection.execute(
                """SELECT component.component_code,selected.quantity,
                          selected.rating,selected.allocated_tons
                   FROM ship_class_component selected
                   JOIN ship_class class
                     ON class.ship_class_rule_id=selected.ship_class_rule_id
                   JOIN ship_component_definition component
                     ON component.component_rule_id=
                        selected.component_rule_id
                   WHERE class.class_code='dreadnought'
                     AND component.component_code IN (
                         'stateroom','low-berth',
                         'emergency-low-berth','barracks'
                     )
                   ORDER BY component.component_code"""
            ).fetchall()
            self.assertEqual(
                dreadnought,
                [
                    ("barracks", 1, 60, 120),
                    ("emergency-low-berth", 56, None, 56),
                    ("low-berth", 223, None, 111.5),
                    ("stateroom", 101, None, 404),
                ],
            )

            smelter = connection.execute(
                """SELECT component.calculation_status,
                          assertion.assertion_status,
                          assertion.canonical_value
                   FROM ship_component_definition component
                   JOIN ship_class class
                     ON class.class_code='asteroid-miner'
                   JOIN ship_class_source_assertion assertion
                     ON assertion.ship_class_rule_id=
                        class.ship_class_rule_id
                    AND assertion.field_code='smelter-specification'
                   WHERE component.component_code='smelter'"""
            ).fetchone()
            self.assertEqual(
                smelter,
                (
                    "adjudicated",
                    "reconciled",
                    "4 tons; Cr90,000; capacity unspecified",
                ),
            )

            fighter_control = connection.execute(
                """SELECT component.component_code,
                          selected.allocated_tons
                   FROM ship_class_component selected
                   JOIN ship_class class
                     ON class.ship_class_rule_id=selected.ship_class_rule_id
                   JOIN ship_component_definition component
                     ON component.component_rule_id=
                        selected.component_rule_id
                   WHERE class.class_code='fighter'
                     AND component.effect_code='small-craft-control'"""
            ).fetchone()
            self.assertEqual(
                fighter_control,
                ("one-person-cockpit", 1.5),
            )

    def test_hangars_and_carried_craft_enforce_type_and_capacity(self):
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            counts = connection.execute(
                """SELECT
                   (SELECT count(*) FROM rule_ship_hangar_option),
                   (SELECT count(*) FROM ship_class_hangar_option),
                   (SELECT count(*) FROM ship_class_carried_craft),
                   (SELECT sum(craft_count)
                      FROM ship_class_carried_craft)"""
            ).fetchone()
            self.assertEqual(counts, (12, 23, 14, 60))

            dreadnought = connection.execute(
                """SELECT hangar_option_code,installation_count,
                          allocated_tons,installation_cost_minor
                   FROM ship_class_hangar_option hangar
                   JOIN ship_class class
                     ON class.ship_class_rule_id=hangar.ship_class_rule_id
                   WHERE class.class_code='dreadnought'
                   ORDER BY hangar_option_code"""
            ).fetchall()
            self.assertEqual(
                dreadnought,
                [
                    ("cutter", 2, 130, 26000000),
                    ("escape-pods", 1, 111.5, 22300000),
                    ("fighter", 20, 260, 52000000),
                ],
            )

            with connection.transaction(force_rollback=True):
                with self.assertRaisesRegex(
                    CheckViolation, "hangar type or capacity",
                ):
                    connection.execute(
                        """UPDATE ship_class_carried_craft
                           SET craft_count=craft_count+1
                           WHERE carrier_class_rule_id=(
                               SELECT ship_class_rule_id
                               FROM ship_class
                               WHERE class_code='dreadnought'
                           )
                             AND hangar_identifier='fighter-hangars'"""
                    )

    def test_construction_receipts_preserve_exact_results_and_variances(self):
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            counts = connection.execute(
                """SELECT
                   (SELECT count(*)
                      FROM ship_class_construction_receipt
                     WHERE finalized),
                   (SELECT count(*)
                      FROM ship_class_construction_line),
                   (SELECT count(*)
                      FROM ship_class_construction_total
                     WHERE reconciliation_status='reconciled'),
                   (SELECT count(*)
                      FROM ship_class_construction_total
                     WHERE reconciliation_status='source_gap'),
                   (SELECT count(*)
                      FROM ship_class_construction_total
                     WHERE reconciliation_status='tonnage_variance'),
                   (SELECT count(*)
                      FROM ship_class_construction_total
                     WHERE reconciliation_status='cost_variance')"""
            ).fetchone()
            self.assertEqual(counts, (39, 738, 5, 1, 0, 18))

            launch = connection.execute(
                """SELECT total.allocated_tons,total.unallocated_tons,
                          total.calculated_cost_minor,
                          total.published_cost_minor,
                          total.cost_variance_minor,
                          total.reconciliation_status
                   FROM ship_class_construction_total total
                   JOIN ship_class class USING (ship_class_rule_id)
                   WHERE class.class_code='launch'"""
            ).fetchone()
            self.assertEqual(
                launch,
                (20, 0, 4797000, 4797000, 0, "reconciled"),
            )

            asteroid_miner = connection.execute(
                """SELECT total.unallocated_tons,
                          total.cost_variance_minor,
                          total.unresolved_line_count,
                          total.reconciliation_status
                   FROM ship_class_construction_total total
                   JOIN ship_class class USING (ship_class_rule_id)
                   WHERE class.class_code='asteroid-miner'"""
            ).fetchone()
            self.assertEqual(
                asteroid_miner,
                (0, 0, 0, "reconciled"),
            )

            fighter_mount = connection.execute(
                """SELECT mount.allocated_tons,
                          mount.fire_control_tons,
                          selected.pricing_mount_code
                   FROM ship_class_weapon_mount selected
                   JOIN ship_class class USING (ship_class_rule_id)
                   JOIN rule_ship_weapon_mount mount USING (mount_code)
                   WHERE class.class_code='fighter'"""
            ).fetchone()
            self.assertEqual(
                fighter_mount,
                (0, 1, "single-turret"),
            )

            cutter_versions = connection.execute(
                """SELECT receipt.receipt_version,
                          total.allocated_tons,total.unallocated_tons,
                          total.calculated_cost_minor,
                          total.cost_variance_minor
                   FROM ship_class_construction_receipt_total total
                   JOIN ship_class class USING (ship_class_rule_id)
                   JOIN ship_class_construction_receipt receipt USING (
                       construction_receipt_id,ship_class_rule_id
                   )
                   WHERE class.class_code='cutter'
                   ORDER BY receipt.receipt_version"""
            ).fetchall()
            self.assertEqual(
                cutter_versions,
                [
                    (1, 45.5, 4.5, 18297000, 6008000),
                    (2, 47, 3, 18364500, 5940500),
                    (3, 50, 0, 18364500, 5940500),
                ],
            )

            cabin = connection.execute(
                """SELECT component.unit_tons,
                          component.unit_cost_minor,
                          selected.allocated_tons,
                          selected.rating
                   FROM ship_class_component selected
                   JOIN ship_class class USING (ship_class_rule_id)
                   JOIN ship_component_definition component USING (
                       component_rule_id
                   )
                   WHERE class.class_code='cutter'
                     AND component.component_code='more-cabin-space'"""
            ).fetchone()
            self.assertEqual(cabin, (1.5, 50000, 1.5, 1))

            variance_audit = connection.execute(
                """SELECT explanation_code,audit_status,
                          variance_dimension,count(*)
                   FROM ship_class_construction_variance
                   GROUP BY explanation_code,audit_status,
                            variance_dimension
                   ORDER BY explanation_code,audit_status,
                            variance_dimension"""
            ).fetchall()
            self.assertEqual(
                variance_audit,
                [
                    (
                        "capped-armor-proration",
                        "rule_conflict",
                        "tonnage",
                        4,
                    ),
                    (
                        "published-total-unitemized",
                        "unresolved",
                        "cost",
                        20,
                    ),
                    (
                        "published-total-unitemized",
                        "unresolved",
                        "tonnage",
                        5,
                    ),
                    (
                        "source-unspecified",
                        "source_gap",
                        "cost",
                        2,
                    ),
                    (
                        "source-unspecified",
                        "source_gap",
                        "tonnage",
                        1,
                    ),
                    (
                        "source-unspecified",
                        "unresolved",
                        "cost",
                        1,
                    ),
                    (
                        "source-unspecified",
                        "unresolved",
                        "tonnage",
                        1,
                    ),
                ],
            )

            probe_payloads = connection.execute(
                """SELECT class.class_code,carried.item_count,
                          item.minimum_tech_level,item.cost_credits,
                          carried.relationship_status
                   FROM ship_class_carried_item carried
                   JOIN ship_class class
                     ON class.ship_class_rule_id=
                        carried.carrier_class_rule_id
                   JOIN inv_item_definition item
                     ON item.rule_id=carried.item_rule_id
                   JOIN rule_rule rule
                     ON rule.rule_id=item.rule_id
                   WHERE rule.rule_code='equipment.probe-drone'
                   ORDER BY class.class_code"""
            ).fetchall()
            self.assertEqual(
                probe_payloads,
                [
                    (
                        "research-vessel", 15, 11, 15000,
                        "published_cross_tl_payload",
                    ),
                    ("survey-vessel", 20, 11, 15000, "published"),
                ],
            )

            current_probe_receipts = connection.execute(
                """SELECT class.class_code,receipt.receipt_version,
                          total.calculated_cost_minor,
                          total.cost_variance_minor,
                          total.reconciliation_status
                   FROM ship_class_construction_total total
                   JOIN ship_class class USING (ship_class_rule_id)
                   JOIN ship_class_construction_receipt receipt USING (
                       construction_receipt_id,ship_class_rule_id
                   )
                   WHERE class.class_code IN (
                       'research-vessel','survey-vessel'
                   )
                   ORDER BY class.class_code"""
            ).fetchall()
            self.assertEqual(
                current_probe_receipts,
                [
                    (
                        "research-vessel", 3, 53005500,
                        20803500, "cost_variance",
                    ),
                    (
                        "survey-vessel", 2, 99963000,
                        21006000, "cost_variance",
                    ),
                ],
            )

            with connection.transaction(force_rollback=True):
                with self.assertRaisesRegex(
                    CheckViolation,
                    "exceeds hangar capacity or conflicts with tech level",
                ):
                    connection.execute(
                        """UPDATE ship_class_carried_item
                           SET relationship_status='published'
                           WHERE carrier_class_rule_id=(
                               SELECT ship_class_rule_id
                               FROM ship_class
                               WHERE class_code='research-vessel'
                           )"""
                    )
