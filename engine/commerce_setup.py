"""Audited trader ledger and ship cargo-hold preparation."""
from dataclasses import dataclass
import re
import psycopg
@dataclass(frozen=True)
class TradingPreparationResult:
 command_public_id:str;actor_public_id:str;ship_public_id:str;account_public_id:str;opening_balance:int;cargo_container_id:int;replayed:bool
def _load(c,cid,pub,replayed):
 r=c.execute("SELECT actor.public_id,ship.public_id,account.public_id,receipt.opening_balance_minor,receipt.cargo_container_id FROM cmd_trading_preparation_receipt receipt JOIN actor_actor actor USING(actor_id) JOIN ship_ship ship USING(ship_id) JOIN fin_account account ON account.account_id=receipt.trader_account_id WHERE receipt.command_id=%s",(cid,)).fetchone();return TradingPreparationResult(str(pub),str(r[0]),str(r[1]),str(r[2]),r[3],r[4],replayed)
def prepare_trading_command(c:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,campaign_public_id:str,actor_public_id:str,ship_public_id:str,opening_balance:int=0)->TradingPreparationResult:
 if opening_balance<0:raise ValueError('Opening balance cannot be negative')
 with c.transaction():
  old=c.execute("SELECT command_id,public_id,command_type,command_status FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(initiator_reference,idempotency_key)).fetchone()
  if old:
   if old[2:]!=('prepare_trading','completed'):raise RuntimeError('Idempotency key belongs to another command')
   return _load(c,old[0],old[1],True)
  s=c.execute("SELECT campaign.campaign_id,actor.actor_id,actor.name,ship.ship_id,ship.name,ship.inventory_item_instance_id FROM camp_campaign campaign JOIN actor_actor actor USING(campaign_id) JOIN ship_ship ship USING(campaign_id) WHERE campaign.public_id=%s AND campaign.owner_reference=%s AND actor.public_id=%s AND ship.public_id=%s FOR UPDATE OF actor,ship",(campaign_public_id,initiator_reference,actor_public_id,ship_public_id)).fetchone()
  if not s:raise PermissionError('Trader or ship is outside this campaign')
  if c.execute("SELECT 1 FROM fin_actor_account owner JOIN fin_account account USING(account_id) WHERE owner.actor_id=%s AND account.account_status='open'",(s[1],)).fetchone():raise ValueError('Trader already has an open account')
  if c.execute("SELECT 1 FROM inv_item_container WHERE owner_item_instance_id=%s",(s[5],)).fetchone():raise ValueError('Ship already has a cargo hold')
  cid,pub=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('prepare_trading',%s,%s) RETURNING command_id,public_id",(initiator_reference,idempotency_key)).fetchone()
  code='trader-'+str(s[1]);account,account_pub=c.execute("INSERT INTO fin_account(campaign_id,currency_code,account_code,name,account_kind) VALUES(%s,'CR',%s,%s,'asset') RETURNING account_id,public_id",(s[0],code,s[2]+' Trading Account')).fetchone();c.execute("INSERT INTO fin_actor_account VALUES(%s,%s,%s)",(account,s[0],s[1]))
  equity=c.execute("SELECT account_id FROM fin_account WHERE campaign_id=%s AND account_code='campaign-opening-equity'",(s[0],)).fetchone()
  if equity:equity=equity[0]
  else:
   equity=c.execute("INSERT INTO fin_account(campaign_id,currency_code,account_code,name,account_kind) VALUES(%s,'CR','campaign-opening-equity','Campaign Opening Equity','equity') RETURNING account_id",(s[0],)).fetchone()[0];c.execute("INSERT INTO fin_campaign_account VALUES(%s,%s)",(equity,s[0]))
  cargo=c.execute("INSERT INTO inv_container(campaign_id,name,capacity_mass_grams) SELECT %s,%s,(class.cargo_capacity_tons*1000000)::bigint FROM ship_ship ship JOIN ship_class class ON class.ship_class_rule_id=ship.ship_class_rule_id WHERE ship.ship_id=%s RETURNING container_id",(s[0],s[4]+' Cargo Hold',s[3])).fetchone()[0];c.execute("INSERT INTO inv_item_container VALUES(%s,%s,%s)",(cargo,s[0],s[5]))
  transaction=None
  if opening_balance:
   transaction=c.execute("INSERT INTO fin_transaction(campaign_id,currency_code,description,command_id) VALUES(%s,'CR',%s,%s) RETURNING transaction_id",(s[0],'Opening trading funds for '+s[2],cid)).fetchone()[0]
   c.execute("INSERT INTO fin_entry(transaction_id,campaign_id,currency_code,account_id,entry_order,amount_minor) VALUES(%s,%s,'CR',%s,1,%s),(%s,%s,'CR',%s,2,%s)",(transaction,s[0],account,opening_balance,transaction,s[0],equity,-opening_balance));c.execute("SELECT fin_post_transaction(%s)",(transaction,))
  c.execute("INSERT INTO cmd_trading_preparation_receipt VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",(cid,s[0],s[1],s[3],account,equity,cargo,opening_balance,transaction))
  c.execute("INSERT INTO cmd_domain_event(command_id,event_order,event_type) VALUES(%s,1,'trading_prepared')",(cid,));c.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(cid,));return _load(c,cid,pub,False)
