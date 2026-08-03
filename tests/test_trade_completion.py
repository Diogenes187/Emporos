import os
import unittest
import uuid

import psycopg

from engine.broker_carousing import resolve_broker_operation_command


class FixedRandom:
    def randint(self, minimum, maximum):
        return 5


@unittest.skipUnless(os.environ.get("BASE_CEPHEUS_DATABASE_URL"), "requires PostgreSQL")
class TradeCompletionTests(unittest.TestCase):
    def _context(self, connection, market_kind="legal"):
        campaign = connection.execute(
            "INSERT INTO camp_campaign(name) VALUES(%s) RETURNING campaign_id",
            (f"Trade {uuid.uuid4().hex}",),
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO camp_clock(campaign_id,day_number,second_of_day) VALUES(%s,10,100) ON CONFLICT(campaign_id) DO UPDATE SET day_number=10,second_of_day=100",
            (campaign,),
        )
        package = connection.execute(
            "SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine'"
        ).fetchone()[0]
        types = {}
        for code in ("trade-sector", "trade-subsector", "trade-system", "trade-world"):
            rule = connection.execute(
                """INSERT INTO rule_rule(content_package_id,rule_code,name,rule_category,rule_status)
                   VALUES(%s,%s,%s,'world','approved') RETURNING rule_id""",
                (package, f"location.{code}-{uuid.uuid4().hex}", code),
            ).fetchone()[0]
            connection.execute("INSERT INTO rule_location_type VALUES(%s,%s,true,true)", (rule, f"{code}-{uuid.uuid4().hex}"))
            types[code] = rule
        locations = {}
        for code in types:
            locations[code] = connection.execute(
                "INSERT INTO loc_location(campaign_id,location_type_rule_id,name) VALUES(%s,%s,%s) RETURNING location_id",
                (campaign, types[code], code),
            ).fetchone()[0]
        connection.execute("INSERT INTO loc_sector VALUES(%s,%s,0,0)", (locations["trade-sector"], campaign))
        connection.execute(
            "INSERT INTO loc_subsector VALUES(%s,%s,%s,1,1)",
            (locations["trade-subsector"], campaign, locations["trade-sector"]),
        )
        connection.execute(
            """INSERT INTO loc_star_system(location_id,campaign_id,sector_location_id,
                       subsector_location_id,hex_column,hex_row) VALUES(%s,%s,%s,%s,1,1)""",
            (locations["trade-system"], campaign, locations["trade-sector"], locations["trade-subsector"]),
        )
        connection.execute(
            """INSERT INTO loc_celestial_body(location_id,campaign_id,system_location_id,body_kind,orbit_order)
               VALUES(%s,%s,%s,'planet',1)""",
            (locations["trade-world"], campaign, locations["trade-system"]),
        )
        profile = connection.execute(
            """INSERT INTO loc_world_profile(location_id,campaign_id,revision_number,starport_code,
                       size_code,atmosphere_code,hydrographics_code,population_code,government_code,
                       law_level_code,technology_level)
               VALUES(%s,%s,1,'A',8,6,7,8,5,4,10) RETURNING world_profile_id""",
            (locations["trade-world"], campaign),
        ).fetchone()[0]
        market = connection.execute(
            "INSERT INTO mkt_market(campaign_id,location_id,name,market_kind) VALUES(%s,%s,'Trade Market',%s) RETURNING market_id",
            (campaign, locations["trade-world"], market_kind),
        ).fetchone()[0]
        session = connection.execute(
            """INSERT INTO mkt_session(market_id,campaign_id,opened_day,opened_second,expires_day,expires_second)
               VALUES(%s,%s,10,100,30,100) RETURNING market_session_id""",
            (market, campaign),
        ).fetchone()[0]
        return campaign, profile, session

    def _actor(self, connection, campaign, name):
        return connection.execute(
            "INSERT INTO actor_actor(campaign_id,name,controller_reference) VALUES(%s,%s,'test') RETURNING actor_id",
            (campaign, name),
        ).fetchone()[0]

    def _account(self, connection, campaign, actor, code):
        account = connection.execute(
            """INSERT INTO fin_account(campaign_id,currency_code,account_code,name,account_kind)
               VALUES(%s,'CR',%s,%s,'asset') RETURNING account_id""",
            (campaign, f"{code}-{uuid.uuid4().hex}", code),
        ).fetchone()[0]
        connection.execute("INSERT INTO fin_actor_account VALUES(%s,%s,%s)", (account, campaign, actor))
        return account

    def test_supplier_stock_draws_are_complete_aggregated_and_immutable(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                campaign, profile, session = self._context(connection)
                supplier_actor = self._actor(connection, campaign, "Supplier")
                supplier = connection.execute(
                    "INSERT INTO mkt_supplier(market_session_id,campaign_id,actor_id,supplier_kind) VALUES(%s,%s,%s,'supplier') RETURNING supplier_id",
                    (session, campaign, supplier_actor),
                ).fetchone()[0]
                generation = connection.execute(
                    """INSERT INTO mkt_supplier_stock_generation(campaign_id,market_session_id,supplier_id,
                               world_profile_id,market_kind_snapshot,random_good_count_roll)
                       VALUES(%s,%s,%s,%s,'legal',2) RETURNING supplier_stock_generation_id""",
                    (campaign, session, supplier, profile),
                ).fetchone()[0]
                advanced = connection.execute(
                    "SELECT trade_good_rule_id FROM rule_trade_good WHERE d66_result=11"
                ).fetchone()[0]
                illegal = connection.execute(
                    "SELECT trade_good_rule_id FROM rule_trade_good WHERE d66_result=61"
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO mkt_supplier_stock_selection_draw VALUES
                       (%s,1,1,1,11,%s,'included'),(%s,2,6,1,61,%s,'ignored-illegal')""",
                    (generation, advanced, generation, illegal),
                )
                goods = connection.execute(
                    """SELECT trade_good_rule_id,good_code,availability_dice_count,availability_die_sides,
                              availability_multiplier FROM rule_trade_good WHERE good_kind='common' ORDER BY good_code"""
                ).fetchall()
                for source_order, (good, _, dice, sides, multiplier) in enumerate(goods, 1):
                    for die_order in range(1, dice + 1):
                        connection.execute(
                            "INSERT INTO mkt_supplier_stock_quantity_draw VALUES(%s,'common',%s,%s,%s,%s,1,%s)",
                            (generation, source_order, good, die_order, sides, multiplier),
                        )
                connection.execute(
                    "INSERT INTO mkt_supplier_stock_quantity_draw VALUES(%s,'random',1,%s,1,6,1,5)",
                    (generation, advanced),
                )
                for good, _, _, _, multiplier in goods + [(advanced, "advanced", 1, 6, 5)]:
                    quantity = connection.execute(
                        "SELECT sum(result*multiplier) FROM mkt_supplier_stock_quantity_draw WHERE supplier_stock_generation_id=%s AND trade_good_rule_id=%s",
                        (generation, good),
                    ).fetchone()[0]
                    stock = connection.execute(
                        """INSERT INTO mkt_stock(market_session_id,campaign_id,supplier_id,trade_good_rule_id,quantity_tons)
                           VALUES(%s,%s,%s,%s,%s) RETURNING stock_id""",
                        (session, campaign, supplier, good, quantity),
                    ).fetchone()[0]
                    connection.execute(
                        "INSERT INTO mkt_supplier_stock_result VALUES(%s,%s,%s,%s,1,%s)",
                        (generation, good, stock, campaign, quantity),
                    )
                connection.execute(
                    "INSERT INTO mkt_supplier_stock_final_receipt VALUES(%s,2,1,1,7,65,clock_timestamp(),NULL)",
                    (generation,),
                )
                with self.assertRaisesRegex(psycopg.Error, "immutable"):
                    with connection.transaction():
                        connection.execute(
                            "UPDATE mkt_supplier_stock_selection_draw SET tens_die=2 WHERE supplier_stock_generation_id=%s AND selection_order=1",
                            (generation,),
                        )

    def test_rejected_quote_locks_only_same_counterparty_for_seven_days(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                campaign, _, session = self._context(connection)
                merchant = self._actor(connection, campaign, "Merchant")
                supplier_actor = self._actor(connection, campaign, "Supplier")
                supplier = connection.execute(
                    "INSERT INTO mkt_supplier(market_session_id,campaign_id,actor_id,supplier_kind) VALUES(%s,%s,%s,'supplier') RETURNING supplier_id",
                    (session, campaign, supplier_actor),
                ).fetchone()[0]
                good = connection.execute(
                    "SELECT trade_good_rule_id FROM rule_trade_good WHERE good_code='basic-consumables'"
                ).fetchone()[0]
                stock = connection.execute(
                    "INSERT INTO mkt_stock(market_session_id,campaign_id,supplier_id,trade_good_rule_id,quantity_tons) VALUES(%s,%s,%s,%s,10) RETURNING stock_id",
                    (session, campaign, supplier, good),
                ).fetchone()[0]
                quote = connection.execute(
                    """INSERT INTO mkt_quote(market_session_id,campaign_id,stock_id,trade_good_rule_id,
                               quote_side,quoted_actor_id,counterparty_supplier_id,unit_price_minor,maximum_quantity_tons)
                       VALUES(%s,%s,%s,%s,'sell',%s,%s,1000,5) RETURNING quote_id""",
                    (session, campaign, stock, good, merchant, supplier),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO mkt_quote_rejection_receipt(quote_id,campaign_id,market_session_id,
                               rejecting_actor_id,counterparty_supplier_id,trade_good_rule_id,quote_side,
                               rejected_day,rejected_second,eligible_again_day,eligible_again_second,
                               quote_version_before,quote_version_after)
                       VALUES(%s,%s,%s,%s,%s,%s,'sell',10,100,17,100,1,2)""",
                    (quote, campaign, session, merchant, supplier, good),
                )
                with self.assertRaisesRegex(psycopg.errors.CheckViolation, "one week"):
                    with connection.transaction():
                        connection.execute(
                            """INSERT INTO mkt_quote(market_session_id,campaign_id,stock_id,trade_good_rule_id,
                                       quote_side,quoted_actor_id,counterparty_supplier_id,unit_price_minor)
                               VALUES(%s,%s,%s,%s,'sell',%s,%s,1000)""",
                            (session, campaign, stock, good, merchant, supplier),
                        )
                connection.execute("UPDATE camp_clock SET day_number=17 WHERE campaign_id=%s", (campaign,))
                connection.execute(
                    """INSERT INTO mkt_quote(market_session_id,campaign_id,stock_id,trade_good_rule_id,
                               quote_side,quoted_actor_id,counterparty_supplier_id,unit_price_minor)
                       VALUES(%s,%s,%s,%s,'sell',%s,%s,1000)""",
                    (session, campaign, stock, good, merchant, supplier),
                )

    def test_local_broker_commission_is_paid_and_rounded_up_before_rejection(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                campaign, _, session = self._context(connection)
                merchant = self._actor(connection, campaign, "Merchant")
                broker, broker_public = connection.execute(
                    "INSERT INTO actor_actor(campaign_id,name,controller_reference) VALUES(%s,'Local Broker','broker') RETURNING actor_id,public_id",
                    (campaign,),
                ).fetchone()
                seller = self._actor(connection, campaign, "Seller")
                education = connection.execute(
                    "SELECT rule_id FROM rule_rule WHERE rule_code='characteristic.education'"
                ).fetchone()[0]
                broker_skill = connection.execute(
                    "SELECT rule_id FROM rule_rule WHERE rule_code='skill.broker'"
                ).fetchone()[0]
                connection.execute("INSERT INTO actor_characteristic VALUES(%s,%s,7,7)", (broker, education))
                connection.execute("INSERT INTO actor_skill VALUES(%s,%s,1)", (broker, broker_skill))
                local_broker = connection.execute(
                    """INSERT INTO mkt_supplier(market_session_id,campaign_id,actor_id,supplier_kind,broker_skill_level)
                       VALUES(%s,%s,%s,'broker',1) RETURNING supplier_id""",
                    (session, campaign, broker),
                ).fetchone()[0]
                supplier = connection.execute(
                    "INSERT INTO mkt_supplier(market_session_id,campaign_id,actor_id,supplier_kind) VALUES(%s,%s,%s,'supplier') RETURNING supplier_id",
                    (session, campaign, seller),
                ).fetchone()[0]
                merchant_account = self._account(connection, campaign, merchant, "merchant")
                broker_account = self._account(connection, campaign, broker, "broker")
                engagement = connection.execute(
                    """INSERT INTO mkt_local_broker_engagement(campaign_id,market_session_id,merchant_actor_id,
                               broker_supplier_id,broker_skill_level,commission_percent,starport_code_snapshot,
                               merchant_settlement_account_id,broker_settlement_account_id)
                       VALUES(%s,%s,%s,%s,1,5,'A',%s,%s) RETURNING local_broker_engagement_id""",
                    (campaign, session, merchant, local_broker, merchant_account, broker_account),
                ).fetchone()[0]
                good = connection.execute(
                    "SELECT trade_good_rule_id FROM rule_trade_good WHERE good_code='animal-products'"
                ).fetchone()[0]
                stock = connection.execute(
                    "INSERT INTO mkt_stock(market_session_id,campaign_id,supplier_id,trade_good_rule_id,quantity_tons) VALUES(%s,%s,%s,%s,10) RETURNING stock_id",
                    (session, campaign, supplier, good),
                ).fetchone()[0]
                operation = resolve_broker_operation_command(
                    connection, initiator_reference="broker", idempotency_key=uuid.uuid4().hex,
                    actor_public_id=str(broker_public), market_session_id=session,
                    operation_code="determine-purchase-price", objective_reference="animal products",
                    characteristic_rule_code="characteristic.education", trade_good_code="animal-products",
                    random_source=FixedRandom(),
                )
                self.assertEqual(operation.price_percent, 70)
                operation_id = connection.execute(
                    "SELECT command_id FROM cmd_command WHERE public_id=%s", (operation.command_public_id,)
                ).fetchone()[0]
                quote = connection.execute(
                    """INSERT INTO mkt_quote(market_session_id,campaign_id,stock_id,trade_good_rule_id,
                               quote_side,quoted_actor_id,counterparty_supplier_id,unit_price_minor,
                               maximum_quantity_tons,price_result,price_percent,local_broker_engagement_id)
                       VALUES(%s,%s,%s,%s,'sell',%s,%s,1050,1,%s,70,%s) RETURNING quote_id""",
                    (session, campaign, stock, good, merchant, supplier, operation.check_total, engagement),
                ).fetchone()[0]
                transaction = connection.execute(
                    """INSERT INTO fin_transaction(campaign_id,currency_code,description,occurred_day,occurred_second)
                       VALUES(%s,'CR','Local broker commission',10,100) RETURNING transaction_id""",
                    (campaign,),
                ).fetchone()[0]
                connection.execute(
                    "INSERT INTO fin_entry(transaction_id,campaign_id,currency_code,account_id,entry_order,amount_minor) VALUES(%s,%s,'CR',%s,1,-53),(%s,%s,'CR',%s,2,53)",
                    (transaction, campaign, merchant_account, transaction, campaign, broker_account),
                )
                connection.execute(
                    "UPDATE fin_transaction SET transaction_status='posted',finalized_at=clock_timestamp() WHERE transaction_id=%s",
                    (transaction,),
                )
                connection.execute(
                    """INSERT INTO mkt_local_broker_negotiation_receipt
                       (quote_id,campaign_id,local_broker_engagement_id,broker_operation_command_id,
                        negotiated_quantity_tons,negotiated_total_credits,commission_percent,
                        exact_commission_credits,settled_commission_credits,rounding_method,
                        commission_due_if_quote_rejected,financial_transaction_id)
                       VALUES(%s,%s,%s,%s,1,1050,5,52.5,53,'ceiling-credit',true,%s)""",
                    (quote, campaign, engagement, operation_id, transaction),
                )
                connection.execute("SET CONSTRAINTS ALL IMMEDIATE")
                connection.execute(
                    """INSERT INTO mkt_quote_rejection_receipt(quote_id,campaign_id,market_session_id,
                               rejecting_actor_id,counterparty_supplier_id,trade_good_rule_id,quote_side,
                               rejected_day,rejected_second,eligible_again_day,eligible_again_second,
                               quote_version_before,quote_version_after)
                       VALUES(%s,%s,%s,%s,%s,%s,'sell',10,100,17,100,1,2)""",
                    (quote, campaign, session, merchant, supplier, good),
                )
                self.assertEqual(connection.execute(
                    """SELECT receipt.settled_commission_credits,quote.quote_status
                       FROM mkt_local_broker_negotiation_receipt receipt JOIN mkt_quote quote USING(quote_id)
                       WHERE receipt.quote_id=%s""", (quote,),
                ).fetchone(), (53, "rejected"))
