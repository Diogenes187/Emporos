import os,unittest,uuid,psycopg
from engine.campaigns import create_campaign_command
from engine.character_creation import initialize_character_command
from engine.ships import acquire_ship_command
from engine.sectors import import_sector_command
from engine.markets import open_trade_market_command
from engine.commerce_setup import prepare_trading_command
from engine.broker_carousing import resolve_broker_operation_command
from engine.purchases import purchase_trade_goods_command
from engine.sales import sell_trade_goods_command
class Fixed:
 def randint(self,a,b):return min(3,b)
@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class PurchaseTests(unittest.TestCase):
 def test_purchase_posts_money_moves_stock_and_places_cargo(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    x=str(uuid.uuid4());owner='purchase-test';camp=create_campaign_command(c,initiator_reference=owner,idempotency_key='c'+x,name='Purchase');actor=initialize_character_command(c,initiator_reference=owner,idempotency_key='a'+x,campaign_public_id=camp.campaign_public_id,character_name='Trader',random_source=Fixed());ship=acquire_ship_command(c,initiator_reference=owner,idempotency_key='s'+x,campaign_public_id=camp.campaign_public_id,owner_actor_public_id=actor.actor_public_id,class_code='merchant-trader',ship_name='Ledger');prepare_trading_command(c,initiator_reference=owner,idempotency_key='setup'+x,campaign_public_id=camp.campaign_public_id,actor_public_id=actor.actor_public_id,ship_public_id=ship.ship_public_id,opening_balance=1000000)
    import_sector_command(c,initiator_reference=owner,idempotency_key='sector'+x,campaign_public_id=camp.campaign_public_id,sector_name='Test',sector_x=0,sector_y=0,source_filename='x.tab',content=b'Name\tHex\tUWP\nAlpha\t0101\tA788899-C\n');system=c.execute("SELECT location.public_id FROM loc_star_system star JOIN loc_location location ON location.location_id=star.location_id WHERE star.campaign_id=(SELECT campaign_id FROM camp_campaign WHERE public_id=%s)",(camp.campaign_public_id,)).fetchone()[0];market=open_trade_market_command(c,initiator_reference=owner,idempotency_key='market'+x,campaign_public_id=camp.campaign_public_id,system_public_id=system,random_source=Fixed());stock=c.execute("SELECT stock.stock_id,good.good_code FROM mkt_stock stock JOIN rule_trade_good good USING(trade_good_rule_id) WHERE stock.market_session_id=(SELECT market_session_id FROM cmd_trade_market_opening_receipt WHERE command_id=(SELECT command_id FROM cmd_command WHERE public_id=%s)) ORDER BY good.base_price_credits LIMIT 1",(market.command_public_id,)).fetchone();session=c.execute("SELECT market_session_id FROM mkt_stock WHERE stock_id=%s",(stock[0],)).fetchone()[0]
    broker=resolve_broker_operation_command(c,initiator_reference=owner,idempotency_key='broker'+x,actor_public_id=actor.actor_public_id,market_session_id=session,operation_code='determine-purchase-price',objective_reference='buy',characteristic_rule_code='characteristic.intelligence',trade_good_code=stock[1],random_source=Fixed());result=purchase_trade_goods_command(c,initiator_reference=owner,idempotency_key='buy'+x,campaign_public_id=camp.campaign_public_id,actor_public_id=actor.actor_public_id,ship_public_id=ship.ship_public_id,stock_id=stock[0],broker_command_public_id=broker.command_public_id,quantity_tons=1)
    self.assertEqual(result.quantity_tons,1);self.assertLess(result.balance_after,1000000)
    lot=c.execute("SELECT lot_id FROM cmd_trade_goods_purchase_receipt WHERE command_id=(SELECT command_id FROM cmd_command WHERE public_id=%s)",(result.command_public_id,)).fetchone()[0]
    sale_quote=resolve_broker_operation_command(c,initiator_reference=owner,idempotency_key='sale-broker'+x,actor_public_id=actor.actor_public_id,market_session_id=session,operation_code='determine-sale-price',objective_reference='sell',characteristic_rule_code='characteristic.intelligence',trade_good_code=stock[1],random_source=Fixed())
    sale=sell_trade_goods_command(c,initiator_reference=owner,idempotency_key='sell'+x,campaign_public_id=camp.campaign_public_id,actor_public_id=actor.actor_public_id,ship_public_id=ship.ship_public_id,lot_id=lot,market_session_id=session,broker_command_public_id=sale_quote.command_public_id,quantity_tons=1)
    self.assertEqual(sale.quantity_tons,1);self.assertGreater(sale.balance_after,result.balance_after)
if __name__=='__main__':unittest.main()
