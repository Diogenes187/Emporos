"""Audited ship berthing and maintenance payments."""
from dataclasses import dataclass
from decimal import Decimal
import psycopg

@dataclass(frozen=True)
class ShipExpenseResult:
 command_public_id:str;ship_public_id:str;operating_cost_code:str
 amount:int;balance_after:int;maintenance_cycle_id:int|None;replayed:bool

def _load(c,cid,pub,replayed):
 r=c.execute("""SELECT ship.public_id,receipt.operating_cost_code,receipt.amount_minor,
 balance.balance_minor,receipt.maintenance_cycle_id
 FROM cmd_ship_operating_expense_receipt receipt JOIN ship_ship ship USING(ship_id)
 JOIN cmd_trading_preparation_receipt setup ON setup.actor_id=receipt.actor_id AND setup.ship_id=receipt.ship_id
 JOIN fin_account_balance balance ON balance.account_id=setup.trader_account_id
 WHERE receipt.command_id=%s""",(cid,)).fetchone()
 return ShipExpenseResult(str(pub),str(r[0]),r[1],r[2],r[3],r[4],replayed)

def pay_ship_operating_expense_command(c:psycopg.Connection,*,initiator_reference:str,
 idempotency_key:str,campaign_public_id:str,actor_public_id:str,ship_public_id:str,
 operating_cost_code:str,quantity:Decimal|int|str=1)->ShipExpenseResult:
 quantity=Decimal(str(quantity))
 if quantity<=0:raise ValueError('Expense quantity must be positive')
 if operating_cost_code not in ('berthing-first-six-days','berthing-additional-day','maintenance-annual','life-support-stateroom','life-support-low-berth'):
  raise ValueError('Unsupported ship expense')
 with c.transaction():
  old=c.execute("SELECT command_id,public_id,command_type,command_status FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(initiator_reference,idempotency_key)).fetchone()
  if old:
   if old[2:]!=('pay_ship_operating_expense','completed'):raise RuntimeError('Idempotency key belongs to another command')
   return _load(c,old[0],old[1],True)
  s=c.execute("""SELECT campaign.campaign_id,actor.actor_id,ship.ship_id,ship.current_location_id,
 setup.trader_account_id,balance.balance_minor,clock.day_number,cost.amount_minor,
 cost.rate_numerator,cost.rate_denominator,class.construction_cost_minor,ship.name
 FROM camp_campaign campaign JOIN camp_clock clock USING(campaign_id)
 JOIN actor_actor actor USING(campaign_id) JOIN ship_ship ship USING(campaign_id)
 JOIN ship_class class ON class.ship_class_rule_id=ship.ship_class_rule_id
 JOIN cmd_trading_preparation_receipt setup ON setup.campaign_id=campaign.campaign_id AND setup.actor_id=actor.actor_id AND setup.ship_id=ship.ship_id
 JOIN fin_account_balance balance ON balance.account_id=setup.trader_account_id
 JOIN rule_ship_operating_cost cost ON cost.operating_cost_code=%s
 WHERE campaign.public_id=%s AND campaign.owner_reference=%s AND actor.public_id=%s AND ship.public_id=%s
 FOR UPDATE OF actor,ship,clock""",(operating_cost_code,campaign_public_id,initiator_reference,actor_public_id,ship_public_id)).fetchone()
  if not s:raise ValueError('Ship, payer, or operating-cost account is unavailable')
  if s[3] is None:raise ValueError('Ship must be at a known location for this service')
  unit=s[7] if s[7] is not None else s[10]*s[8]//s[9]
  amount=int(Decimal(unit)*quantity)
  if amount<=0:raise ValueError('Calculated expense must be positive')
  if s[5]<amount:raise ValueError(f'Expense costs Cr {amount}; account holds Cr {s[5]}')
  cid,pub=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('pay_ship_operating_expense',%s,%s) RETURNING command_id,public_id",(initiator_reference,idempotency_key)).fetchone()
  vendor=c.execute("SELECT account_id FROM fin_account WHERE campaign_id=%s AND account_code='starport-services'",(s[0],)).fetchone()
  if vendor:vendor=vendor[0]
  else:
   vendor=c.execute("INSERT INTO fin_account(campaign_id,currency_code,account_code,name,account_kind) VALUES(%s,'CR','starport-services','Starport Services','external') RETURNING account_id",(s[0],)).fetchone()[0]
   c.execute("INSERT INTO fin_external_account VALUES(%s,%s,'Starport services')",(vendor,s[0]))
  descriptions={'maintenance-annual':'Annual maintenance for ','berthing-first-six-days':'Berthing for ','berthing-additional-day':'Berthing for ','life-support-stateroom':'Stateroom life support for ','life-support-low-berth':'Low-berth life support for '}
  description=descriptions[operating_cost_code]+s[11]
  tx=c.execute("INSERT INTO fin_transaction(campaign_id,currency_code,description,command_id) VALUES(%s,'CR',%s,%s) RETURNING transaction_id",(s[0],description,cid)).fetchone()[0]
  c.execute("INSERT INTO fin_entry(transaction_id,campaign_id,currency_code,account_id,entry_order,amount_minor) VALUES(%s,%s,'CR',%s,1,%s),(%s,%s,'CR',%s,2,%s)",(tx,s[0],s[4],-amount,tx,s[0],vendor,amount));c.execute("SELECT fin_post_transaction(%s)",(tx,))
  expense=c.execute("INSERT INTO ship_operating_expense(ship_id,campaign_id,operating_cost_code,financial_transaction_id,quantity,amount_minor,expense_day,description) VALUES(%s,%s,%s,%s,%s,%s,%s,%s) RETURNING operating_expense_id",(s[2],s[0],operating_cost_code,tx,quantity,amount,s[6],description)).fetchone()[0]
  cycle=None
  if operating_cost_code=='maintenance-annual':
   cycle_number=c.execute("SELECT COALESCE(max(cycle_number),0)+1 FROM ship_maintenance_cycle WHERE ship_id=%s",(s[2],)).fetchone()[0]
   cycle=c.execute("INSERT INTO ship_maintenance_cycle(ship_id,campaign_id,cycle_number,scheduled_day,completed_day,maintenance_cost_minor,maintenance_status,location_id,financial_transaction_id,source_command_id) VALUES(%s,%s,%s,%s,%s,%s,'completed',%s,%s,%s) RETURNING maintenance_cycle_id",(s[2],s[0],cycle_number,s[6],s[6],amount,s[3],tx,cid)).fetchone()[0]
  c.execute("INSERT INTO cmd_ship_operating_expense_receipt VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",(cid,s[0],s[1],s[2],operating_cost_code,quantity,amount,expense,cycle,tx))
  c.execute("INSERT INTO cmd_domain_event(command_id,event_order,event_type) VALUES(%s,1,'ship_operating_expense_paid')",(cid,));c.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(cid,))
  return _load(c,cid,pub,False)
