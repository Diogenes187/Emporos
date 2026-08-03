import os
import unittest

import psycopg
from psycopg.errors import CheckViolation, ForeignKeyViolation, UniqueViolation


@unittest.skipUnless(
    os.environ.get("BASE_CEPHEUS_DATABASE_URL"),
    "requires the project PostgreSQL database",
)
class WorldJourneyMarketIntegrationTests(unittest.TestCase):
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

    def location_type(self, connection, code):
        rule_id = connection.execute(
            """INSERT INTO rule_rule
               (content_package_id,rule_code,name,rule_category,rule_status)
               SELECT content_package_id,%s,%s,'world','approved'
               FROM sys_content_package
               WHERE package_code='cepheus-engine'
               RETURNING rule_id""",
            (f"location.type.{code}", code.title()),
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO rule_location_type VALUES (%s,%s,true,true)",
            (rule_id, code),
        )
        return rule_id

    def location(self, connection, campaign_id, type_id, name):
        return connection.execute(
            """INSERT INTO loc_location
               (campaign_id,location_type_rule_id,name)
               VALUES (%s,%s,%s) RETURNING location_id""",
            (campaign_id, type_id, name),
        ).fetchone()[0]

    def account(self, connection, campaign_id, actor_id, code):
        account_id = connection.execute(
            """INSERT INTO fin_account
               (campaign_id,currency_code,account_code,name,account_kind)
               VALUES (%s,'CR',%s,%s,'asset') RETURNING account_id""",
            (campaign_id, code, code.title()),
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO fin_actor_account VALUES (%s,%s,%s)",
            (account_id, campaign_id, actor_id),
        )
        return account_id

    def test_world_and_trade_catalogues_are_relational(self):
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            counts = connection.execute(
                """SELECT
                   (SELECT count(*) FROM rule_world_size),
                   (SELECT count(*) FROM rule_world_atmosphere),
                   (SELECT count(*) FROM loc_trade_code),
                   (SELECT count(*) FROM rule_trade_good),
                   (SELECT count(*) FROM rule_trade_good_modifier),
                   (SELECT count(*) FROM rule_modified_price_band),
                   (SELECT count(*) FROM rule_starport_traffic_expression)"""
            ).fetchone()
            self.assertEqual(counts, (11, 16, 18, 42, 140, 15, 24))

            with connection.transaction(force_rollback=True):
                campaign_id = self.campaign(connection, "World")
                world_type = self.location_type(connection, "profile-world")
                world = self.location(
                    connection, campaign_id, world_type, "New World")
                with self.assertRaises(CheckViolation):
                    with connection.transaction():
                        connection.execute(
                            """INSERT INTO loc_world_profile
                               (location_id,campaign_id,revision_number,
                                starport_code,size_code,atmosphere_code,
                                hydrographics_code,population_code,
                                government_code,law_level_code,
                                technology_level)
                               VALUES (%s,%s,1,'Z',8,6,7,8,5,4,10)""",
                            (world, campaign_id),
                        )

    def test_journeys_require_continuous_legs_origin_and_free_actor(self):
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            with connection.transaction(force_rollback=True):
                campaign_id = self.campaign(connection, "Journey")
                location_type = self.location_type(connection, "journey")
                origin = self.location(
                    connection, campaign_id, location_type, "Origin")
                middle = self.location(
                    connection, campaign_id, location_type, "Middle")
                destination = self.location(
                    connection, campaign_id, location_type, "Destination")
                actor_id = self.actor(connection, campaign_id, "Traveller")
                connection.execute(
                    """INSERT INTO loc_actor_position
                       (campaign_id,actor_id,location_id)
                       VALUES (%s,%s,%s)""",
                    (campaign_id, actor_id, origin),
                )

                first = connection.execute(
                    """INSERT INTO journey_journey
                       (campaign_id,journey_kind,name)
                       VALUES (%s,'multi_leg','First')
                       RETURNING journey_id""",
                    (campaign_id,),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO journey_leg
                       (journey_id,campaign_id,leg_order,
                        origin_location_id,destination_location_id,
                        travel_mode)
                       VALUES (%s,%s,1,%s,%s,'interplanetary')""",
                    (first, campaign_id, origin, middle),
                )
                with self.assertRaisesRegex(
                    CheckViolation, "continue",
                ):
                    with connection.transaction():
                        connection.execute(
                            """INSERT INTO journey_leg
                               (journey_id,campaign_id,leg_order,
                                origin_location_id,
                                destination_location_id,travel_mode)
                               VALUES (%s,%s,2,%s,%s,'jump')""",
                            (
                                first,
                                campaign_id,
                                origin,
                                destination,
                            ),
                        )
                connection.execute(
                    """INSERT INTO journey_participant
                       (journey_id,campaign_id,actor_id,participant_role)
                       VALUES (%s,%s,%s,'traveller')""",
                    (first, campaign_id, actor_id),
                )
                connection.execute(
                    """UPDATE journey_journey
                       SET journey_status='ready'
                       WHERE journey_id=%s""",
                    (first,),
                )

                second = connection.execute(
                    """INSERT INTO journey_journey
                       (campaign_id,journey_kind,name)
                       VALUES (%s,'jump','Second') RETURNING journey_id""",
                    (campaign_id,),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO journey_leg
                       (journey_id,campaign_id,leg_order,
                        origin_location_id,destination_location_id,
                        travel_mode)
                       VALUES (%s,%s,1,%s,%s,'jump')""",
                    (second, campaign_id, origin, destination),
                )
                with self.assertRaisesRegex(
                    UniqueViolation, "another active journey",
                ):
                    with connection.transaction():
                        connection.execute(
                            """INSERT INTO journey_participant
                               (journey_id,campaign_id,actor_id,
                                participant_role)
                               VALUES (%s,%s,%s,'traveller')""",
                            (second, campaign_id, actor_id),
                        )

    def test_market_execution_requires_linked_transfers_and_reduces_stock(self):
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            with connection.transaction(force_rollback=True):
                campaign_id = self.campaign(connection, "Market")
                location_type = self.location_type(connection, "market")
                location_id = self.location(
                    connection, campaign_id, location_type, "Port")
                seller = self.actor(connection, campaign_id, "Seller")
                buyer = self.actor(connection, campaign_id, "Buyer")
                seller_account = self.account(
                    connection, campaign_id, seller, "seller")
                buyer_account = self.account(
                    connection, campaign_id, buyer, "buyer")
                transaction_id = connection.execute(
                    """INSERT INTO fin_transaction
                       (campaign_id,currency_code,description)
                       VALUES (%s,'CR','Cargo purchase')
                       RETURNING transaction_id""",
                    (campaign_id,),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO fin_entry
                       (transaction_id,campaign_id,currency_code,
                        account_id,entry_order,amount_minor)
                       VALUES (%s,%s,'CR',%s,1,-1000),
                              (%s,%s,'CR',%s,2,1000)""",
                    (
                        transaction_id, campaign_id, buyer_account,
                        transaction_id, campaign_id, seller_account,
                    ),
                )
                connection.execute(
                    "SELECT fin_post_transaction(%s)", (transaction_id,))
                transfer_id = connection.execute(
                    """INSERT INTO inv_transfer
                       (campaign_id,transfer_kind,transfer_status,
                        completed_at)
                       VALUES (%s,'ownership','completed',
                               clock_timestamp())
                       RETURNING transfer_id""",
                    (campaign_id,),
                ).fetchone()[0]
                market_id = connection.execute(
                    """INSERT INTO mkt_market
                       (campaign_id,location_id,name,market_kind)
                       VALUES (%s,%s,'Port Market','legal')
                       RETURNING market_id""",
                    (campaign_id, location_id),
                ).fetchone()[0]
                session = connection.execute(
                    """INSERT INTO mkt_session
                       (market_id,campaign_id,opened_day,opened_second,
                        expires_day,expires_second)
                       VALUES (%s,%s,1,0,2,0)
                       RETURNING market_session_id""",
                    (market_id, campaign_id),
                ).fetchone()[0]
                supplier = connection.execute(
                    """INSERT INTO mkt_supplier
                       (market_session_id,campaign_id,actor_id,
                        supplier_kind)
                       VALUES (%s,%s,%s,'supplier')
                       RETURNING supplier_id""",
                    (session, campaign_id, seller),
                ).fetchone()[0]
                good = connection.execute(
                    """SELECT trade_good_rule_id FROM rule_trade_good
                       WHERE good_code='basic-consumables'"""
                ).fetchone()[0]
                stock = connection.execute(
                    """INSERT INTO mkt_stock
                       (market_session_id,campaign_id,supplier_id,
                        trade_good_rule_id,quantity_tons)
                       VALUES (%s,%s,%s,%s,5) RETURNING stock_id""",
                    (session, campaign_id, supplier, good),
                ).fetchone()[0]
                quote = connection.execute(
                    """INSERT INTO mkt_quote
                       (market_session_id,campaign_id,stock_id,
                        trade_good_rule_id,quote_side,quoted_actor_id,
                        unit_price_minor,maximum_quantity_tons)
                       VALUES (%s,%s,%s,%s,'sell',%s,1000,2)
                       RETURNING quote_id""",
                    (session, campaign_id, stock, good, buyer),
                ).fetchone()[0]
                order = connection.execute(
                    """INSERT INTO mkt_order
                       (market_session_id,campaign_id,actor_id,
                        settlement_account_id,trade_good_rule_id,
                        order_side,quantity_tons,limit_price_minor)
                       VALUES (%s,%s,%s,%s,%s,'buy',1,1000)
                       RETURNING order_id""",
                    (
                        session, campaign_id, buyer, buyer_account, good,
                    ),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO mkt_execution
                       (market_session_id,campaign_id,order_id,quote_id,
                        stock_id,quantity_tons,unit_price_minor,
                        inventory_transfer_id,financial_transaction_id)
                       VALUES (%s,%s,%s,%s,%s,1,1000,%s,%s)""",
                    (
                        session, campaign_id, order, quote, stock,
                        transfer_id, transaction_id,
                    ),
                )
                state = connection.execute(
                    """SELECT stock.quantity_tons,orders.order_status,
                              quote.quote_status
                       FROM mkt_stock stock
                       JOIN mkt_order orders ON orders.order_id=%s
                       JOIN mkt_quote quote ON quote.quote_id=%s
                       WHERE stock.stock_id=%s""",
                    (order, quote, stock),
                ).fetchone()
                self.assertEqual(state, (4, "filled", "accepted"))


if __name__ == "__main__":
    unittest.main()
