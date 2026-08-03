"""Accept available bulk freight against a planned commercial route."""
from dataclasses import dataclass
from decimal import Decimal
import psycopg
@dataclass(frozen=True)
class FreightContractResult:
 command_public_id:str;contract_public_id:str;journey_public_id:str;ship_public_id:str;accepted_tons:Decimal;promised_payment:int;replayed:bool
def _load(c,cid,pub,replayed):
 r=c.execute("""SELECT contract.public_id,journey.public_id,ship.public_id,receipt.accepted_tons,receipt.promised_payment_credits FROM cmd_freight_contract_acceptance_receipt receipt JOIN journey_freight_contract contract ON contract.freight_contract_id=receipt.freight_contract_id JOIN journey_journey journey ON journey.journey_id=receipt.journey_id JOIN ship_ship ship ON ship.ship_id=receipt.ship_id WHERE receipt.command_id=%s""",(cid,)).fetchone();return FreightContractResult(str(pub),str(r[0]),str(r[1]),str(r[2]),r[3],r[4],replayed)
def accept_freight_contract_command(c:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,cycle_public_id:str,journey_public_id:str,accepted_tons:Decimal|int|str)->FreightContractResult:
 tons=Decimal(str(accepted_tons))
 if tons<=0 or tons.as_tuple().exponent<0:raise ValueError('Freight must be accepted in positive whole tons')
 with c.transaction():
  old=c.execute("SELECT command_id,public_id,command_type,command_status FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(initiator_reference,idempotency_key)).fetchone()
  if old:
   if old[2:]!=('accept_freight_contract','completed'):raise RuntimeError('Idempotency key belongs to another command')
   return _load(c,old[0],old[1],True)
  s=c.execute("""SELECT cycle.campaign_id,cycle.revenue_availability_cycle_id,journey.journey_id,leg.journey_leg_id,journey.ship_id,ship.public_id,draw.available_quantity,class.cargo_capacity_tons,setup.cargo_container_id
 FROM journey_revenue_availability_cycle cycle JOIN camp_campaign campaign USING(campaign_id)
 JOIN journey_journey journey ON journey.public_id=%s AND journey.campaign_id=cycle.campaign_id
 JOIN journey_leg leg ON leg.journey_id=journey.journey_id AND leg.leg_order=1 AND leg.origin_location_id=cycle.origin_location_id AND leg.destination_location_id=cycle.destination_location_id
 JOIN ship_ship ship ON ship.ship_id=journey.ship_id JOIN ship_class class ON class.ship_class_rule_id=ship.ship_class_rule_id
 JOIN cmd_trading_preparation_receipt setup ON setup.campaign_id=cycle.campaign_id AND setup.ship_id=ship.ship_id
 JOIN journey_revenue_availability_draw draw ON draw.revenue_availability_cycle_id=cycle.revenue_availability_cycle_id AND draw.traffic_kind='freight_tons'
 WHERE cycle.public_id=%s AND campaign.owner_reference=%s AND cycle.cycle_status='finalized' AND journey.journey_status IN('planning','ready') FOR UPDATE OF cycle,journey,leg,ship""",(journey_public_id,cycle_public_id,initiator_reference)).fetchone()
  if not s:raise ValueError('Freight opportunity and planned journey do not share the same route and ship')
  accepted=c.execute("SELECT COALESCE(sum(accepted_tons),0) FROM journey_freight_contract WHERE revenue_availability_cycle_id=%s",(s[1],)).fetchone()[0]
  if accepted+tons>s[6]:raise ValueError(f'Only {s[6]-accepted} tons of freight remain available')
  loaded=c.execute("SELECT COALESCE(sum(placement.quantity*definition.mass_grams),0)/1000000.0 FROM inv_container_lot placement JOIN inv_lot lot USING(lot_id) JOIN inv_item_definition definition ON definition.rule_id=lot.item_rule_id WHERE placement.container_id=%s",(s[8],)).fetchone()[0]
  reserved=c.execute("SELECT COALESCE(sum(reserved_tons),0) FROM ship_cargo_reservation WHERE ship_id=%s AND reservation_status='reserved'",(s[4],)).fetchone()[0]
  if loaded+reserved+tons>s[7]:raise ValueError(f'Only {s[7]-loaded-reserved} tons of hold capacity remain')
  cid,pub=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('accept_freight_contract',%s,%s) RETURNING command_id,public_id",(initiator_reference,idempotency_key)).fetchone()
  reservation=c.execute("INSERT INTO ship_cargo_reservation(ship_id,campaign_id,journey_id,reservation_kind,reserved_tons) VALUES(%s,%s,%s,'bulk-freight',%s) RETURNING cargo_reservation_id",(s[4],s[0],s[2],tons)).fetchone()[0]
  promised=int(tons*1000);contract,contract_pub=c.execute("INSERT INTO journey_freight_contract(campaign_id,revenue_availability_cycle_id,journey_id,journey_leg_id,ship_id,cargo_reservation_id,accepted_tons,payment_per_ton_credits,promised_payment_credits,source_command_id) VALUES(%s,%s,%s,%s,%s,%s,%s,1000,%s,%s) RETURNING freight_contract_id,public_id",(s[0],s[1],s[2],s[3],s[4],reservation,tons,promised,cid)).fetchone()
  c.execute("INSERT INTO cmd_freight_contract_acceptance_receipt VALUES(%s,%s,%s,%s,%s,%s,%s)",(cid,s[0],contract,s[2],s[4],tons,promised));c.execute("INSERT INTO cmd_domain_event(command_id,event_order,event_type) VALUES(%s,1,'freight_contract_accepted')",(cid,));c.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(cid,));return _load(c,cid,pub,False)
