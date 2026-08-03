"""Freight delivery, reservation release, and posted payment."""
from dataclasses import dataclass
import psycopg
@dataclass(frozen=True)
class FreightDeliveryResult:
 command_public_id:str;contract_public_id:str;ship_public_id:str;delivered_tons:int|float;paid_credits:int;balance_after:int;replayed:bool
def _load(c,cid,pub,replayed):
 r=c.execute("""SELECT contract.public_id,ship.public_id,contract.accepted_tons,delivery.paid_credits,receipt.balance_after_minor FROM cmd_freight_delivery_receipt receipt JOIN journey_freight_contract contract ON contract.freight_contract_id=receipt.freight_contract_id JOIN ship_ship ship ON ship.ship_id=contract.ship_id JOIN journey_freight_delivery_receipt delivery ON delivery.freight_contract_id=contract.freight_contract_id WHERE receipt.command_id=%s""",(cid,)).fetchone();return FreightDeliveryResult(str(pub),str(r[0]),str(r[1]),r[2],r[3],r[4],replayed)
def deliver_freight_contract_command(c:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,contract_public_id:str,actor_public_id:str)->FreightDeliveryResult:
 with c.transaction():
  old=c.execute("SELECT command_id,public_id,command_type,command_status FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(initiator_reference,idempotency_key)).fetchone()
  if old:
   if old[2:]!=('deliver_freight_contract','completed'):raise RuntimeError('Idempotency key belongs to another command')
   return _load(c,old[0],old[1],True)
  s=c.execute("""SELECT contract.campaign_id,contract.freight_contract_id,contract.ship_id,ship.public_id,contract.accepted_tons,contract.promised_payment_credits,leg.destination_location_id,clock.day_number,actor.actor_id,setup.trader_account_id,balance.balance_minor
 FROM journey_freight_contract contract JOIN camp_campaign campaign USING(campaign_id) JOIN camp_clock clock USING(campaign_id)
 JOIN journey_journey journey ON journey.journey_id=contract.journey_id JOIN journey_leg leg ON leg.journey_leg_id=contract.journey_leg_id
 JOIN ship_ship ship ON ship.ship_id=contract.ship_id AND ship.current_location_id=leg.destination_location_id
 JOIN actor_actor actor ON actor.campaign_id=contract.campaign_id AND actor.public_id=%s
 JOIN cmd_trading_preparation_receipt setup ON setup.campaign_id=contract.campaign_id AND setup.actor_id=actor.actor_id AND setup.ship_id=ship.ship_id
 JOIN fin_account_balance balance ON balance.account_id=setup.trader_account_id
 WHERE contract.public_id=%s AND campaign.owner_reference=%s AND journey.journey_status='completed'
 AND NOT EXISTS(SELECT 1 FROM journey_freight_delivery_receipt delivery WHERE delivery.freight_contract_id=contract.freight_contract_id)
 AND NOT EXISTS(SELECT 1 FROM journey_freight_cancellation_receipt cancellation WHERE cancellation.freight_contract_id=contract.freight_contract_id)
 FOR UPDATE OF contract,journey,ship,actor""",(actor_public_id,contract_public_id,initiator_reference)).fetchone()
  if not s:raise ValueError('Freight can only be delivered by its ship after arrival at the contracted destination')
  cid,pub=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('deliver_freight_contract',%s,%s) RETURNING command_id,public_id",(initiator_reference,idempotency_key)).fetchone()
  customer=c.execute("SELECT account_id FROM fin_account WHERE campaign_id=%s AND account_code='freight-customers'",(s[0],)).fetchone()
  if customer:customer=customer[0]
  else:
   customer=c.execute("INSERT INTO fin_account(campaign_id,currency_code,account_code,name,account_kind) VALUES(%s,'CR','freight-customers','Freight Customers','external') RETURNING account_id",(s[0],)).fetchone()[0];c.execute("INSERT INTO fin_external_account VALUES(%s,%s,'Freight customers')",(customer,s[0]))
  tx=c.execute("INSERT INTO fin_transaction(campaign_id,currency_code,description,command_id) VALUES(%s,'CR',%s,%s) RETURNING transaction_id",(s[0],f'Freight delivery: {s[4]} tons',cid)).fetchone()[0]
  c.execute("INSERT INTO fin_entry(transaction_id,campaign_id,currency_code,account_id,entry_order,amount_minor) VALUES(%s,%s,'CR',%s,1,%s),(%s,%s,'CR',%s,2,%s)",(tx,s[0],s[9],s[5],tx,s[0],customer,-s[5]));c.execute("SELECT fin_post_transaction(%s)",(tx,))
  c.execute("INSERT INTO journey_freight_delivery_receipt(freight_contract_id,campaign_id,delivered_location_id,delivered_tons,paid_credits,financial_transaction_id,delivered_day,source_command_id) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",(s[1],s[0],s[6],s[4],s[5],tx,s[7],cid))
  after=s[10]+s[5];c.execute("INSERT INTO cmd_freight_delivery_receipt VALUES(%s,%s,%s,%s,%s,%s)",(cid,s[0],s[1],s[8],tx,after));c.execute("INSERT INTO cmd_domain_event(command_id,event_order,event_type) VALUES(%s,1,'freight_contract_delivered')",(cid,));c.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(cid,));return _load(c,cid,pub,False)
