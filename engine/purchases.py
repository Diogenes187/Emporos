"""Atomic trade-good purchase through existing market, ledger, and inventory structures."""
from dataclasses import dataclass
import psycopg
@dataclass(frozen=True)
class PurchaseResult:
 command_public_id:str;execution_public_id:str;actor_public_id:str;ship_public_id:str;good_code:str;quantity_tons:int;unit_price:int;total_price:int;balance_after:int;replayed:bool
def _load(c,cid,pub,replayed):
 r=c.execute("SELECT execution.public_id,actor.public_id,ship.public_id,good.good_code,receipt.quantity_tons,receipt.unit_price_minor,receipt.total_price_minor,balance.balance_minor FROM cmd_trade_goods_purchase_receipt receipt JOIN mkt_execution execution USING(execution_id) JOIN actor_actor actor USING(actor_id) JOIN ship_ship ship USING(ship_id) JOIN rule_trade_good good USING(trade_good_rule_id) JOIN cmd_trading_preparation_receipt setup ON setup.actor_id=receipt.actor_id AND setup.ship_id=receipt.ship_id JOIN fin_account_balance balance ON balance.account_id=setup.trader_account_id WHERE receipt.command_id=%s",(cid,)).fetchone();return PurchaseResult(str(pub),str(r[0]),str(r[1]),str(r[2]),r[3],r[4],r[5],r[6],r[7],replayed)
def purchase_trade_goods_command(c:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,campaign_public_id:str,actor_public_id:str,ship_public_id:str,stock_id:int,broker_command_public_id:str,quantity_tons:int)->PurchaseResult:
 if quantity_tons<=0:raise ValueError('Purchase quantity must be positive whole tons')
 with c.transaction():
  old=c.execute("SELECT command_id,public_id,command_type,command_status FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(initiator_reference,idempotency_key)).fetchone()
  if old:
   if old[2:]!=('purchase_trade_goods','completed'):raise RuntimeError('Idempotency key belongs to another command')
   return _load(c,old[0],old[1],True)
  s=c.execute("""SELECT campaign.campaign_id,actor.actor_id,ship.ship_id,setup.trader_account_id,setup.cargo_container_id,
  stock.market_session_id,stock.trade_good_rule_id,stock.quantity_tons,good.good_code,good.base_price_credits,
  broker.command_id,broker.price_percent,balance.balance_minor,container.capacity_mass_grams,
  COALESCE((SELECT sum(placement.quantity*definition.mass_grams) FROM inv_container_lot placement JOIN inv_lot lot USING(lot_id) JOIN inv_item_definition definition ON definition.rule_id=lot.item_rule_id WHERE placement.container_id=setup.cargo_container_id),0),market.market_id,market.settlement_account_id
  FROM camp_campaign campaign JOIN actor_actor actor USING(campaign_id) JOIN ship_ship ship USING(campaign_id)
  JOIN cmd_trading_preparation_receipt setup ON setup.campaign_id=campaign.campaign_id AND setup.actor_id=actor.actor_id AND setup.ship_id=ship.ship_id
  JOIN fin_account_balance balance ON balance.account_id=setup.trader_account_id JOIN inv_container container ON container.container_id=setup.cargo_container_id
  JOIN mkt_stock stock ON stock.stock_id=%s AND stock.campaign_id=campaign.campaign_id JOIN rule_trade_good good ON good.trade_good_rule_id=stock.trade_good_rule_id
  JOIN mkt_session session ON session.market_session_id=stock.market_session_id AND session.campaign_id=stock.campaign_id JOIN mkt_market market ON market.market_id=session.market_id AND market.campaign_id=session.campaign_id
  JOIN cmd_command broker_command ON broker_command.public_id=%s JOIN cmd_broker_operation_receipt broker ON broker.command_id=broker_command.command_id AND broker.actor_id=actor.actor_id AND broker.market_session_id=stock.market_session_id AND broker.trade_good_rule_id=stock.trade_good_rule_id AND broker.operation_code='determine-purchase-price'
  WHERE campaign.public_id=%s AND campaign.owner_reference=%s AND actor.public_id=%s AND ship.public_id=%s AND stock.stock_status='available' AND session.session_status='open'
  FOR UPDATE OF stock,actor,ship,container,market""",(stock_id,broker_command_public_id,campaign_public_id,initiator_reference,actor_public_id,ship_public_id)).fetchone()
  if not s:raise ValueError('Purchase context or negotiated price is not valid')
  unit=s[9]*s[11]//100;total=unit*quantity_tons
  if s[7]<quantity_tons:raise ValueError('Market stock is insufficient')
  if s[12]<total:raise ValueError(f'Purchase costs Cr {total}; account holds Cr {s[12]}')
  if s[13] is None or s[14]+quantity_tons*1000000>s[13]:raise ValueError('Ship cargo capacity would be exceeded')
  cid,pub=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('purchase_trade_goods',%s,%s) RETURNING command_id,public_id",(initiator_reference,idempotency_key)).fetchone()
  market_account=s[16]
  if market_account is None:
   market_account=c.execute("INSERT INTO fin_account(campaign_id,currency_code,account_code,name,account_kind) VALUES(%s,'CR',%s,%s,'external') RETURNING account_id",(s[0],'market-'+str(s[15]),'Market Settlement')).fetchone()[0];c.execute("INSERT INTO fin_external_account VALUES(%s,%s,%s)",(market_account,s[0],'Local market'));c.execute("UPDATE mkt_market SET settlement_account_id=%s WHERE market_id=%s",(market_account,s[15]))
  tx=c.execute("INSERT INTO fin_transaction(campaign_id,currency_code,description,command_id) VALUES(%s,'CR',%s,%s) RETURNING transaction_id",(s[0],'Purchase '+s[8],cid)).fetchone()[0]
  c.execute("INSERT INTO fin_entry(transaction_id,campaign_id,currency_code,account_id,entry_order,amount_minor) VALUES(%s,%s,'CR',%s,1,%s),(%s,%s,'CR',%s,2,%s)",(tx,s[0],s[3],-total,tx,s[0],market_account,total));c.execute("SELECT fin_post_transaction(%s)",(tx,))
  transfer=c.execute("INSERT INTO inv_transfer(campaign_id,transfer_kind,transfer_status,command_id,description,completed_at) VALUES(%s,'custody_and_ownership','completed',%s,%s,clock_timestamp()) RETURNING transfer_id",(s[0],cid,'Purchase '+s[8])).fetchone()[0]
  lot=c.execute("INSERT INTO inv_lot(campaign_id,item_rule_id,lot_identifier,quantity,source_command_id) VALUES(%s,%s,%s,%s,%s) RETURNING lot_id",(s[0],s[6],'purchase-'+str(cid),quantity_tons,cid)).fetchone()[0];c.execute("INSERT INTO inv_container_lot(campaign_id,container_id,lot_id,quantity,source_transfer_id) VALUES(%s,%s,%s,%s,%s)",(s[0],s[4],lot,quantity_tons,transfer))
  quote=c.execute("INSERT INTO mkt_quote(market_session_id,campaign_id,stock_id,trade_good_rule_id,quote_side,quoted_actor_id,unit_price_minor,maximum_quantity_tons,price_result,price_percent,source_command_id) VALUES(%s,%s,%s,%s,'sell',%s,%s,%s,NULL,%s,%s) RETURNING quote_id",(s[5],s[0],stock_id,s[6],s[1],unit,quantity_tons,s[11],cid)).fetchone()[0]
  order=c.execute("INSERT INTO mkt_order(market_session_id,campaign_id,actor_id,settlement_account_id,trade_good_rule_id,order_side,quantity_tons,limit_price_minor,source_command_id) VALUES(%s,%s,%s,%s,%s,'buy',%s,%s,%s) RETURNING order_id",(s[5],s[0],s[1],s[3],s[6],quantity_tons,unit,cid)).fetchone()[0]
  execution,execution_pub=c.execute("INSERT INTO mkt_execution(market_session_id,campaign_id,order_id,quote_id,stock_id,quantity_tons,unit_price_minor,inventory_transfer_id,financial_transaction_id,source_command_id) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING execution_id,public_id",(s[5],s[0],order,quote,stock_id,quantity_tons,unit,transfer,tx,cid)).fetchone()
  c.execute("INSERT INTO cmd_trade_goods_purchase_receipt VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",(cid,s[0],s[10],execution,s[1],s[2],s[6],quantity_tons,unit,total,lot,s[4],tx,transfer))
  c.execute("INSERT INTO cmd_domain_event(command_id,event_order,event_type) VALUES(%s,1,'trade_goods_purchased')",(cid,));c.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(cid,));return _load(c,cid,pub,False)
