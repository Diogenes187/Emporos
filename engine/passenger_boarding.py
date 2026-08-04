"""Passenger boarding and source-timed fare collection."""
from dataclasses import dataclass
import psycopg
@dataclass(frozen=True)
class PassengerBoardingResult:
 command_public_id:str;journey_public_id:str;ship_public_id:str;passenger_count:int;total_fare:int;balance_after:int;replayed:bool
def _load(c,cid,pub,replayed):
 r=c.execute("SELECT journey.public_id,ship.public_id,receipt.passenger_count,receipt.total_fare_minor,receipt.balance_after_minor FROM cmd_passenger_boarding_receipt receipt JOIN journey_journey journey ON journey.journey_id=receipt.journey_id JOIN ship_ship ship ON ship.ship_id=receipt.ship_id WHERE receipt.command_id=%s",(cid,)).fetchone();return PassengerBoardingResult(str(pub),str(r[0]),str(r[1]),r[2],r[3],r[4],replayed)
def board_route_passengers_command(c:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,journey_public_id:str,actor_public_id:str)->PassengerBoardingResult:
 with c.transaction():
  old=c.execute("SELECT command_id,public_id,command_type,command_status FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(initiator_reference,idempotency_key)).fetchone()
  if old:
   if old[2:]!=('board_route_passengers','completed'):raise RuntimeError('Idempotency key belongs to another command')
   return _load(c,old[0],old[1],True)
  s=c.execute("SELECT journey.campaign_id,journey.journey_id,journey.ship_id,ship.public_id,actor.actor_id,setup.trader_account_id,balance.balance_minor FROM journey_journey journey JOIN camp_campaign campaign USING(campaign_id) JOIN ship_ship ship USING(ship_id) JOIN actor_actor actor ON actor.campaign_id=journey.campaign_id AND actor.public_id=%s JOIN cmd_trading_preparation_receipt setup ON setup.campaign_id=journey.campaign_id AND setup.ship_id=journey.ship_id AND setup.actor_id=actor.actor_id JOIN fin_account_balance balance ON balance.account_id=setup.trader_account_id WHERE journey.public_id=%s AND campaign.owner_reference=%s AND journey.journey_status IN('planning','ready') FOR UPDATE OF journey,ship,actor",(actor_public_id,journey_public_id,initiator_reference)).fetchone()
  if not s:raise ValueError('Passengers can only board a controlled, prepared ship before departure')
  passages=c.execute("SELECT journey_passage_id,fare_minor FROM journey_passage WHERE journey_id=%s AND passage_status='booked' ORDER BY journey_passage_id FOR UPDATE",(s[1],)).fetchall()
  if not passages:raise ValueError('This journey has no booked passengers awaiting boarding')
  total=sum(row[1] for row in passages);cid,pub=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('board_route_passengers',%s,%s) RETURNING command_id,public_id",(initiator_reference,idempotency_key)).fetchone();customer=c.execute("SELECT account_id FROM fin_account WHERE campaign_id=%s AND account_code='passenger-fares'",(s[0],)).fetchone()
  if customer:customer=customer[0]
  else:customer=c.execute("INSERT INTO fin_account(campaign_id,currency_code,account_code,name,account_kind) VALUES(%s,'CR','passenger-fares','Passenger Fares','external') RETURNING account_id",(s[0],)).fetchone()[0];c.execute("INSERT INTO fin_external_account VALUES(%s,%s,'Passenger customers')",(customer,s[0]))
  tx=c.execute("INSERT INTO fin_transaction(campaign_id,currency_code,description,command_id) VALUES(%s,'CR',%s,%s) RETURNING transaction_id",(s[0],f'Passenger fares: {len(passages)} aboard',cid)).fetchone()[0];c.execute("INSERT INTO fin_entry(transaction_id,campaign_id,currency_code,account_id,entry_order,amount_minor) VALUES(%s,%s,'CR',%s,1,%s),(%s,%s,'CR',%s,2,%s)",(tx,s[0],s[5],total,tx,s[0],customer,-total));c.execute("SELECT fin_post_transaction(%s)",(tx,));after=s[6]+total;c.execute("INSERT INTO cmd_passenger_boarding_receipt VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",(cid,s[0],s[1],s[2],s[4],len(passages),total,tx,after))
  for order,(passage,fare) in enumerate(passages,1):c.execute("INSERT INTO cmd_passenger_boarding_line VALUES(%s,%s,%s,%s,%s)",(cid,order,s[0],passage,fare))
  c.execute("UPDATE journey_passage SET passage_status='boarded',financial_transaction_id=%s,concurrency_version=concurrency_version+1 WHERE journey_id=%s AND passage_status='booked'",(tx,s[1]));c.execute("INSERT INTO cmd_domain_event(command_id,event_order,event_type) VALUES(%s,1,'route_passengers_boarded')",(cid,));c.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(cid,));return _load(c,cid,pub,False)
