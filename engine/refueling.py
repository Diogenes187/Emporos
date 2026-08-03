"""Atomic paid starport refueling using ship resources and the finance ledger."""
from dataclasses import dataclass
from decimal import Decimal
import psycopg

@dataclass(frozen=True)
class RefuelingResult:
 command_public_id:str;actor_public_id:str;ship_public_id:str;fuel_type_code:str
 tons_acquired:Decimal;unit_price:int;total_price:int;quantity_after:Decimal
 balance_after:int;replayed:bool

def _load(c,cid,pub,replayed):
 r=c.execute("""SELECT actor.public_id,ship.public_id,receipt.fuel_type_code,
 receipt.tons_acquired,receipt.unit_price_minor,receipt.total_price_minor,
 receipt.quantity_after,balance.balance_minor
 FROM cmd_ship_refueling_receipt receipt JOIN actor_actor actor USING(actor_id)
 JOIN ship_ship ship USING(ship_id)
 JOIN cmd_trading_preparation_receipt setup ON setup.actor_id=receipt.actor_id AND setup.ship_id=receipt.ship_id
 JOIN fin_account_balance balance ON balance.account_id=setup.trader_account_id
 WHERE receipt.command_id=%s""",(cid,)).fetchone()
 return RefuelingResult(str(pub),str(r[0]),str(r[1]),r[2],r[3],r[4],r[5],r[6],r[7],replayed)

def refuel_ship_command(c:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,
 campaign_public_id:str,actor_public_id:str,ship_public_id:str,fuel_type_code:str,
 tons:Decimal|int|str)->RefuelingResult:
 tons=Decimal(str(tons))
 if tons<=0 or tons.as_tuple().exponent < -3:raise ValueError('Fuel quantity must be positive with no more than three decimal places')
 if fuel_type_code not in ('refined','unrefined'):raise ValueError('Fuel type must be refined or unrefined')
 resource_code=fuel_type_code+'_fuel';cost_code='fuel-'+fuel_type_code
 with c.transaction():
  old=c.execute("SELECT command_id,public_id,command_type,command_status FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(initiator_reference,idempotency_key)).fetchone()
  if old:
   if old[2:]!=('refuel_ship','completed'):raise RuntimeError('Idempotency key belongs to another command')
   return _load(c,old[0],old[1],True)
  s=c.execute("""SELECT campaign.campaign_id,actor.actor_id,ship.ship_id,ship.current_location_id,
 resource.current_quantity,resource.capacity_quantity,setup.trader_account_id,balance.balance_minor,
 cost.amount_minor
 FROM camp_campaign campaign JOIN actor_actor actor USING(campaign_id) JOIN ship_ship ship USING(campaign_id)
 JOIN ship_resource resource ON resource.ship_id=ship.ship_id AND resource.resource_type_code=%s
 JOIN cmd_trading_preparation_receipt setup ON setup.campaign_id=campaign.campaign_id AND setup.actor_id=actor.actor_id AND setup.ship_id=ship.ship_id
 JOIN fin_account_balance balance ON balance.account_id=setup.trader_account_id
 JOIN rule_ship_operating_cost cost ON cost.operating_cost_code=%s
 WHERE campaign.public_id=%s AND campaign.owner_reference=%s AND actor.public_id=%s AND ship.public_id=%s
 FOR UPDATE OF actor,ship,resource""",(resource_code,cost_code,campaign_public_id,initiator_reference,actor_public_id,ship_public_id)).fetchone()
  if not s:raise ValueError('Ship, payer, fuel tank, or trading account is unavailable')
  if s[3] is None:raise ValueError('Ship must be at a known location to refuel')
  if s[4]+tons>s[5]:raise ValueError(f'Fuel tank can accept only {s[5]-s[4]} tons')
  total=int(tons*s[8])
  if s[7]<total:raise ValueError(f'Refueling costs Cr {total}; account holds Cr {s[7]}')
  cid,pub=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('refuel_ship',%s,%s) RETURNING command_id,public_id",(initiator_reference,idempotency_key)).fetchone()
  port=c.execute("SELECT account_id FROM fin_account WHERE campaign_id=%s AND account_code='starport-services'",(s[0],)).fetchone()
  if port:port=port[0]
  else:
   port=c.execute("INSERT INTO fin_account(campaign_id,currency_code,account_code,name,account_kind) VALUES(%s,'CR','starport-services','Starport Services','external') RETURNING account_id",(s[0],)).fetchone()[0]
   c.execute("INSERT INTO fin_external_account VALUES(%s,%s,'Starport services')",(port,s[0]))
  tx=None
  if total:
   tx=c.execute("INSERT INTO fin_transaction(campaign_id,currency_code,description,command_id) VALUES(%s,'CR',%s,%s) RETURNING transaction_id",(s[0],f'{fuel_type_code.title()} fuel: {tons} tons',cid)).fetchone()[0]
   c.execute("INSERT INTO fin_entry(transaction_id,campaign_id,currency_code,account_id,entry_order,amount_minor) VALUES(%s,%s,'CR',%s,1,%s),(%s,%s,'CR',%s,2,%s)",(tx,s[0],s[6],-total,tx,s[0],port,total));c.execute("SELECT fin_post_transaction(%s)",(tx,))
  after=s[4]+tons;c.execute("UPDATE ship_resource SET current_quantity=%s,source_command_id=%s WHERE ship_id=%s AND resource_type_code=%s",(after,cid,s[2],resource_code))
  c.execute("INSERT INTO cmd_ship_refueling_receipt VALUES(%s,%s,%s,%s,%s,%s,%s,'starport',%s,%s,%s,%s,%s)",(cid,s[0],s[1],s[2],s[3],fuel_type_code,resource_code,tons,s[8],total,after,tx))
  c.execute("INSERT INTO cmd_domain_event(command_id,event_order,event_type) VALUES(%s,1,'ship_refueled')",(cid,));c.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(cid,))
  return _load(c,cid,pub,False)
