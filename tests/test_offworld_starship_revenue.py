import os
import unittest
import uuid

import psycopg


@unittest.skipUnless(
    os.environ.get("BASE_CEPHEUS_DATABASE_URL"), "requires PostgreSQL"
)
class OffworldStarshipRevenueTests(unittest.TestCase):
    def _campaign_locations(self, connection):
        campaign = connection.execute(
            "INSERT INTO camp_campaign(name) VALUES(%s) RETURNING campaign_id",
            (f"Revenue {uuid.uuid4().hex}",),
        ).fetchone()[0]
        package = connection.execute(
            "SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine'"
        ).fetchone()[0]
        location_rule = connection.execute(
            """INSERT INTO rule_rule
               (content_package_id,rule_code,name,rule_category,rule_status)
               VALUES(%s,%s,'Revenue Port','world','approved') RETURNING rule_id""",
            (package, f"location.revenue-{uuid.uuid4().hex}"),
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO rule_location_type VALUES(%s,%s,true,true)",
            (location_rule, f"revenue-{uuid.uuid4().hex}"),
        )
        origin = connection.execute(
            "INSERT INTO loc_location(campaign_id,location_type_rule_id,name) VALUES(%s,%s,'Origin') RETURNING location_id",
            (campaign, location_rule),
        ).fetchone()[0]
        destination = connection.execute(
            "INSERT INTO loc_location(campaign_id,location_type_rule_id,name) VALUES(%s,%s,'Destination') RETURNING location_id",
            (campaign, location_rule),
        ).fetchone()[0]
        return campaign, package, origin, destination

    def _availability(self, connection, campaign, origin, destination):
        cycle = connection.execute(
            """INSERT INTO journey_revenue_availability_cycle
               (campaign_id,origin_location_id,destination_location_id,
                starport_code,available_day,refresh_number)
               VALUES(%s,%s,%s,'A',100,1)
               RETURNING revenue_availability_cycle_id""",
            (campaign, origin, destination),
        ).fetchone()[0]
        rows = [
            ("freight_tons", 3, 6, 0, 10, 10, 100),
            ("high_passengers", 3, 6, 0, 1, 11, 11),
            ("middle_passengers", 3, 6, 0, 1, 12, 12),
            ("low_passengers", 3, 6, 0, 3, 9, 27),
        ]
        with connection.cursor() as cursor:
            cursor.executemany(
                """INSERT INTO journey_revenue_availability_draw
                   (revenue_availability_cycle_id,campaign_id,traffic_kind,
                    dice_count,die_sides,flat_modifier,multiplier,natural_total,
                    available_quantity)
                   VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                [(cycle, campaign, *row) for row in rows],
            )
        connection.execute(
            """INSERT INTO journey_revenue_availability_receipt
               (revenue_availability_cycle_id,campaign_id,draw_count)
               VALUES(%s,%s,4)""",
            (cycle, campaign),
        )
        return cycle

    def test_published_revenue_rules_and_simultaneous_availability(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            self.assertEqual(
                connection.execute(
                    """SELECT availability_refresh_days,
                              freight_payment_per_ton_credits,
                              postal_reserved_tons,postal_payment_credits
                       FROM rule_ship_revenue_system"""
                ).fetchone(),
                (3, 1000, 5, 25000),
            )
            self.assertEqual(
                connection.execute(
                    """SELECT count(DISTINCT work.work_code)
                       FROM src_record_provenance provenance
                       JOIN rule_rule rule USING(rule_id)
                       JOIN src_locator locator USING(source_locator_id)
                       JOIN src_work work ON work.source_work_id=locator.source_work_id
                       WHERE rule.rule_code='travel.starship-revenue'"""
                ).fetchone()[0],
                2,
            )
            with connection.transaction(force_rollback=True):
                campaign, _, origin, destination = self._campaign_locations(connection)
                cycle = self._availability(
                    connection, campaign, origin, destination
                )
                self.assertEqual(
                    connection.execute(
                        """SELECT cycle_status,concurrency_version
                           FROM journey_revenue_availability_cycle
                           WHERE revenue_availability_cycle_id=%s""",
                        (cycle,),
                    ).fetchone(),
                    ("finalized", 2),
                )
                with self.assertRaisesRegex(
                    psycopg.errors.CheckViolation, "open campaign cycle|immutable"
                ):
                    with connection.transaction():
                        connection.execute(
                            """UPDATE journey_revenue_availability_draw
                               SET available_quantity=99
                               WHERE revenue_availability_cycle_id=%s
                                 AND traffic_kind='freight_tons'""",
                            (cycle,),
                        )
                with self.assertRaisesRegex(
                    psycopg.errors.CheckViolation, "three campaign days"
                ):
                    with connection.transaction():
                        connection.execute(
                            """INSERT INTO journey_revenue_availability_cycle
                               (campaign_id,origin_location_id,destination_location_id,
                                starport_code,available_day,refresh_number)
                               VALUES(%s,%s,%s,'A',102,2)""",
                            (campaign, origin, destination),
                        )

    def test_freight_postal_and_charter_contract_invariants(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                campaign, package, origin, destination = self._campaign_locations(connection)
                cycle = self._availability(
                    connection, campaign, origin, destination
                )
                item_rule = connection.execute(
                    """INSERT INTO rule_rule
                       (content_package_id,rule_code,name,rule_category,rule_status)
                       VALUES(%s,%s,'Revenue Hull','equipment','approved') RETURNING rule_id""",
                    (package, f"item.revenue-{uuid.uuid4().hex}"),
                ).fetchone()[0]
                connection.execute(
                    "INSERT INTO inv_item_definition(rule_id,item_kind,minimum_tech_level,cost_credits) VALUES(%s,'equipment',9,1)",
                    (item_rule,),
                )
                item = connection.execute(
                    "INSERT INTO inv_item_instance(campaign_id,item_rule_id,instance_name) VALUES(%s,%s,'Revenue Hull') RETURNING item_instance_id",
                    (campaign, item_rule),
                ).fetchone()[0]
                class_rule = connection.execute(
                    """INSERT INTO rule_rule
                       (content_package_id,rule_code,name,rule_category,rule_status)
                       VALUES(%s,%s,'Revenue Ship','ship','approved') RETURNING rule_id""",
                    (package, f"ship.revenue-{uuid.uuid4().hex}"),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO ship_class
                       (ship_class_rule_id,class_code,hull_tons,hull_points,
                        structure_points,minimum_tech_level,
                        construction_cost_minor,cargo_capacity_tons)
                       VALUES(%s,%s,100,2,2,9,1,20)""",
                    (class_rule, f"revenue-{uuid.uuid4().hex}"),
                )
                connection.execute(
                    "INSERT INTO ship_class_characteristic VALUES(%s,'staterooms',2),(%s,'low_berths',1)",
                    (class_rule, class_rule),
                )
                weapon_rule = connection.execute(
                    """INSERT INTO rule_rule
                       (content_package_id,rule_code,name,rule_category,rule_status)
                       VALUES(%s,%s,'Revenue Laser','ship','approved') RETURNING rule_id""",
                    (package, f"ship.weapon.revenue-{uuid.uuid4().hex}"),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO ship_weapon_definition
                       (weapon_rule_id,weapon_code,weapon_kind,damage_dice_count,
                        damage_die_sides)
                       VALUES(%s,%s,'laser',1,6)""",
                    (weapon_rule, f"revenue-{uuid.uuid4().hex}"),
                )
                connection.execute(
                    """INSERT INTO ship_class_weapon
                       (ship_class_rule_id,weapon_rule_id,mount_identifier,quantity)
                       VALUES(%s,%s,'Turret 1',1)""",
                    (class_rule, weapon_rule),
                )
                ship = connection.execute(
                    """INSERT INTO ship_ship
                       (campaign_id,ship_class_rule_id,inventory_item_instance_id,
                        name,current_location_id,hull_current,structure_current)
                       VALUES(%s,%s,%s,'Revenue Ship',%s,2,2) RETURNING ship_id""",
                    (campaign, class_rule, item, origin),
                ).fetchone()[0]
                gunner_actor = connection.execute(
                    "INSERT INTO actor_actor(campaign_id,name,controller_reference) VALUES(%s,'Gunner','test') RETURNING actor_id",
                    (campaign,),
                ).fetchone()[0]
                gunner_rule = connection.execute(
                    "SELECT crew_position_rule_id FROM ship_crew_position_definition WHERE position_code='gunner'"
                ).fetchone()[0]
                gunner_position = connection.execute(
                    """INSERT INTO ship_crew_position
                       (ship_id,campaign_id,crew_position_rule_id,position_identifier)
                       VALUES(%s,%s,%s,'Gunner 1') RETURNING ship_crew_position_id""",
                    (ship, campaign, gunner_rule),
                ).fetchone()[0]
                gunner_assignment = connection.execute(
                    """INSERT INTO ship_crew_assignment
                       (ship_crew_position_id,ship_id,campaign_id,actor_id)
                       VALUES(%s,%s,%s,%s) RETURNING crew_assignment_id""",
                    (gunner_position, ship, campaign, gunner_actor),
                ).fetchone()[0]
                journey = connection.execute(
                    """INSERT INTO journey_journey
                       (campaign_id,journey_kind,name,ship_id)
                       VALUES(%s,'commercial','Revenue Run',%s) RETURNING journey_id""",
                    (campaign, ship),
                ).fetchone()[0]
                leg = connection.execute(
                    """INSERT INTO journey_leg
                       (journey_id,campaign_id,leg_order,origin_location_id,
                        destination_location_id,travel_mode)
                       VALUES(%s,%s,1,%s,%s,'jump') RETURNING journey_leg_id""",
                    (journey, campaign, origin, destination),
                ).fetchone()[0]
                freight_reservation = connection.execute(
                    """INSERT INTO ship_cargo_reservation
                       (ship_id,campaign_id,journey_id,reservation_kind,reserved_tons)
                       VALUES(%s,%s,%s,'bulk-freight',10)
                       RETURNING cargo_reservation_id""",
                    (ship, campaign, journey),
                ).fetchone()[0]
                freight = connection.execute(
                    """INSERT INTO journey_freight_contract
                       (campaign_id,revenue_availability_cycle_id,journey_id,
                        journey_leg_id,ship_id,cargo_reservation_id,accepted_tons,
                        payment_per_ton_credits,promised_payment_credits)
                       VALUES(%s,%s,%s,%s,%s,%s,10,1000,10000)
                       RETURNING freight_contract_id""",
                    (
                        campaign,
                        cycle,
                        journey,
                        leg,
                        ship,
                        freight_reservation,
                    ),
                ).fetchone()[0]
                transaction = connection.execute(
                    """INSERT INTO fin_transaction
                       (campaign_id,currency_code,transaction_status,description,
                        occurred_day,occurred_second,finalized_at)
                       VALUES(%s,'CR','posted','Freight delivery',110,0,clock_timestamp())
                       RETURNING transaction_id""",
                    (campaign,),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO journey_freight_delivery_receipt
                       (freight_contract_id,campaign_id,delivered_location_id,
                        delivered_tons,paid_credits,financial_transaction_id,
                        delivered_day)
                       VALUES(%s,%s,%s,10,10000,%s,110)""",
                    (freight, campaign, destination, transaction),
                )
                postal_reservation = connection.execute(
                    """INSERT INTO ship_cargo_reservation
                       (ship_id,campaign_id,journey_id,reservation_kind,reserved_tons)
                       VALUES(%s,%s,%s,'postal-duty',5)
                       RETURNING cargo_reservation_id""",
                    (ship, campaign, journey),
                ).fetchone()[0]
                postal = connection.execute(
                    """INSERT INTO journey_postal_contract
                       (campaign_id,journey_id,journey_leg_id,ship_id,
                        cargo_reservation_id,gunner_crew_assignment_id,
                        actual_mail_natural_roll,actual_mail_tons,
                        reserved_mail_tons,promised_payment_credits)
                       VALUES(%s,%s,%s,%s,%s,%s,1,0,5,25000)
                       RETURNING postal_contract_id""",
                    (
                        campaign,
                        journey,
                        leg,
                        ship,
                        postal_reservation,
                        gunner_assignment,
                    ),
                ).fetchone()[0]
                self.assertIsNotNone(postal)
                quote = connection.execute(
                    """INSERT INTO journey_starship_charter_quote_receipt
                       (campaign_id,ship_id,ship_class_rule_id,
                        cargo_capacity_tons_snapshot,high_berths_snapshot,
                        low_berths_snapshot,billing_blocks,cargo_rate_credits,
                        high_berth_rate_credits,low_berth_rate_credits,
                        quoted_price_credits,owner_pays_overhead,
                        owner_supplies_crew)
                       VALUES(%s,%s,%s,20,2,1,1,900,9000,900,36900,true,true)
                       RETURNING charter_quote_id""",
                    (campaign, ship, class_rule),
                ).fetchone()[0]
                contract = connection.execute(
                    """INSERT INTO journey_starship_charter_contract
                       (campaign_id,charter_quote_id,journey_id,ship_id,
                        promised_payment_credits,accepted_day)
                       VALUES(%s,%s,%s,%s,36900,100)
                       RETURNING charter_contract_id""",
                    (campaign, quote, journey, ship),
                ).fetchone()[0]
                self.assertIsNotNone(contract)
                with self.assertRaisesRegex(
                    psycopg.errors.RaiseException, "immutable"
                ):
                    with connection.transaction():
                        connection.execute(
                            "DELETE FROM journey_postal_contract WHERE postal_contract_id=%s",
                            (postal,),
                        )


if __name__ == "__main__":
    unittest.main()
