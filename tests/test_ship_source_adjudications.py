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
class ShipSourceAdjudicationTests(unittest.TestCase):
    def test_adjudicated_definitions_are_normalized(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            smelter = connection.execute(
                """SELECT unit_tons,unit_cost_minor,capacity_kind,
                          calculation_status
                     FROM ship_component_definition
                    WHERE component_code='smelter'"""
            ).fetchone()
            drives = connection.execute(
                """SELECT drive_kind,drive_code,performance,validation_status
                     FROM ship_class_drive drive
                     JOIN ship_class class USING(ship_class_rule_id)
                    WHERE class.class_code='destroyer'
                      AND drive_kind IN ('jump','maneuver')
                    ORDER BY drive_kind"""
            ).fetchall()
            payload = connection.execute(
                """SELECT class.minimum_tech_level,item.minimum_tech_level,
                          carried.item_count,carried.relationship_status
                     FROM ship_class_carried_item carried
                     JOIN ship_class class
                       ON class.ship_class_rule_id=
                          carried.carrier_class_rule_id
                     JOIN inv_item_definition item
                       ON item.rule_id=carried.item_rule_id
                    WHERE class.class_code='research-vessel'"""
            ).fetchone()
        self.assertEqual(smelter, (4, 90000, None, "adjudicated"))
        self.assertEqual(
            drives,
            [
                ("jump", "H", 2, "validated"),
                ("maneuver", "N", 4, "validated"),
            ],
        )
        self.assertEqual(payload, (9, 11, 15, "published_cross_tl_payload"))

    def test_new_receipts_preserve_prior_versions(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            totals = connection.execute(
                """SELECT class.class_code,receipt.receipt_version,
                          total.allocated_tons,total.calculated_cost_minor,
                          total.cost_variance_minor,receipt.receipt_status
                     FROM ship_class class
                     JOIN ship_class_construction_receipt receipt
                       USING(ship_class_rule_id)
                     JOIN ship_class_construction_receipt_total total
                       USING(construction_receipt_id,ship_class_rule_id)
                    WHERE class.class_code IN (
                        'asteroid-miner','destroyer','research-vessel')
                    ORDER BY class.class_code,receipt.receipt_version"""
            ).fetchall()
        self.assertEqual(
            totals,
            [
                ("asteroid-miner", 1, 196, 33129000, 90000, "source_gap"),
                ("asteroid-miner", 2, 200, 33219000, 0, "complete"),
                ("destroyer", 1, 810, 423162000, -387000, "source_gap"),
                ("destroyer", 2, 832, 462762000, -39987000, "source_gap"),
                ("destroyer", 3, 800, 459162000, -36387000, "source_gap"),
                ("research-vessel", 1, 200, 52803000, 21006000, "complete"),
                ("research-vessel", 2, 200, 53005500, 20803500, "source_gap"),
                ("research-vessel", 3, 200, 53005500, 20803500, "complete"),
            ],
        )

    def test_resolutions_and_new_destroyer_gap_are_auditable(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            statuses = dict(
                connection.execute(
                    """SELECT issue_code,issue_status
                         FROM src_issue
                        WHERE issue_code IN (
                          'ship.asteroid-miner.construction.cost',
                          'ship.asteroid-miner.construction.tonnage',
                          'ship.asteroid-miner.source.smelter-specification',
                          'ship.destroyer.source.jump-drive-performance',
                          'ship.destroyer.source.maneuver-drive-performance',
                          'ship.research-vessel.source.probe-drone-tech-level',
                          'ship.destroyer.construction.tonnage-adjudicated-drives'
                        )"""
                ).fetchall()
            )
            decisions = connection.execute(
                """SELECT DISTINCT decision_register_entry
                     FROM rule_interpretation
                    WHERE decision_register_entry LIKE 'CE-SHIP-%'
                    ORDER BY decision_register_entry"""
            ).fetchall()
        self.assertEqual(
            statuses,
            {
                "ship.asteroid-miner.construction.cost": "resolved",
                "ship.asteroid-miner.construction.tonnage": "resolved",
                "ship.asteroid-miner.source.smelter-specification": "resolved",
                "ship.destroyer.source.jump-drive-performance": "resolved",
                "ship.destroyer.source.maneuver-drive-performance": "resolved",
                "ship.research-vessel.source.probe-drone-tech-level":
                    "accepted_as_published",
                "ship.destroyer.construction.tonnage-adjudicated-drives":
                    "resolved",
            },
        )
        self.assertEqual(
            decisions,
            [
                ("CE-SHIP-001",), ("CE-SHIP-002",),
                ("CE-SHIP-003",), ("CE-SHIP-004",),
                ("CE-SHIP-005",), ("CE-SHIP-006",),
                ("CE-SHIP-007",),
                ("CE-SHIP-008",),
            ],
        )

    def test_tonnage_adjudications_balance_latest_receipts(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            totals = connection.execute(
                """SELECT class.class_code,total.allocated_tons,
                          total.unallocated_tons
                     FROM ship_class class
                     JOIN ship_class_construction_total total
                       USING(ship_class_rule_id)
                    WHERE class.class_code IN (
                        'corvette','cutter','destroyer','dreadnought',
                        'heavy-cruiser','light-cruiser','patrol-frigate',
                        'system-defense-boat','system-monitor')
                    ORDER BY class.class_code"""
            ).fetchall()
            adjusted_lines = connection.execute(
                """SELECT class.class_code,line.line_kind,
                          line.allocated_tons
                     FROM ship_class class
                     JOIN ship_class_construction_total total
                       USING(ship_class_rule_id)
                     JOIN ship_class_construction_line line
                       USING(construction_receipt_id)
                    WHERE (line.line_kind='armor' AND class.class_code IN (
                              'destroyer','heavy-cruiser','light-cruiser',
                              'system-monitor'))
                       OR (line.line_kind='component'
                           AND line.reference_code='cargo-hold'
                           AND class.class_code IN (
                              'corvette','cutter','destroyer','dreadnought',
                              'patrol-frigate','system-defense-boat'))
                    ORDER BY class.class_code,line.line_kind"""
            ).fetchall()
            statuses = dict(connection.execute(
                """SELECT issue_code,issue_status
                     FROM src_issue
                    WHERE issue_code IN (
                        'ship.corvette.construction.tonnage',
                        'ship.cutter.construction.tonnage',
                        'ship.destroyer.construction.tonnage',
                        'ship.dreadnought.construction.tonnage',
                        'ship.heavy-cruiser.construction.tonnage',
                        'ship.light-cruiser.construction.tonnage',
                        'ship.patrol-frigate.construction.tonnage',
                        'ship.system-defense-boat.construction.tonnage',
                        'ship.system-monitor.construction.tonnage')"""
            ).fetchall())
        self.assertEqual(
            totals,
            [
                ('corvette', 300, 0), ('cutter', 50, 0),
                ('destroyer', 800, 0), ('dreadnought', 5000, 0),
                ('heavy-cruiser', 2000, 0), ('light-cruiser', 1000, 0),
                ('patrol-frigate', 300, 0),
                ('system-defense-boat', 400, 0),
                ('system-monitor', 1000, 0),
            ],
        )
        self.assertEqual(
            adjusted_lines,
            [
                ('corvette', 'component', 17),
                ('cutter', 'component', Decimal('4.3')),
                ('destroyer', 'armor', 110),
                ('destroyer', 'component', Decimal('28.5')),
                ('dreadnought', 'component', 385),
                ('heavy-cruiser', 'armor', 275),
                ('light-cruiser', 'armor', Decimal('137.5')),
                ('patrol-frigate', 'component', 22),
                ('system-defense-boat', 'component', 107),
                ('system-monitor', 'armor', 225),
            ],
        )
        self.assertEqual(set(statuses.values()), {'resolved'})

    def test_adjudicated_state_rejects_silent_changes(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            for statement in (
                "UPDATE ship_component_definition SET unit_tons=5 "
                "WHERE component_code='smelter'",
                "UPDATE ship_class_drive SET drive_code='D' "
                "WHERE ship_class_rule_id=(SELECT ship_class_rule_id "
                "FROM ship_class WHERE class_code='destroyer') "
                "AND drive_kind='jump'",
                "UPDATE ship_class_carried_item "
                "SET relationship_status='published_tl_conflict' "
                "WHERE carrier_class_rule_id=(SELECT ship_class_rule_id "
                "FROM ship_class WHERE class_code='research-vessel')",
            ):
                with self.assertRaises(CheckViolation):
                    with connection.transaction():
                        connection.execute(statement)
                connection.rollback()


if __name__ == "__main__":
    unittest.main()
