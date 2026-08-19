"""Ship placement and source-constrained jump journey planning."""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
import psycopg

@dataclass(frozen=True)
class ShipPlacementResult:
 command_public_id:str;ship_public_id:str;system_public_id:str
 ship_name:str;system_name:str;replayed:bool

@dataclass(frozen=True)
class JumpPlanningResult:
 command_public_id:str;journey_public_id:str;ship_public_id:str
 origin_name:str;destination_name:str;distance_parsecs:int
 jump_number:int;fuel_quantity:Decimal;crew_count:int;replayed:bool

def _distance(a_col,a_row,b_col,b_row):
    # Traveller sector columns are an offset hex grid; convert to axial coordinates.
    aq=a_col;ar=a_row-(a_col+1)//2;bq=b_col;br=b_row-(b_col+1)//2
    dq=bq-aq;dr=br-ar
    return max(abs(dq),abs(dr),abs(dq+dr))

def _load_place(c,cid,pub,replayed):
    row=c.execute("SELECT ship.public_id,system_location.public_id,ship.name,system_location.name FROM cmd_ship_placement_receipt receipt JOIN ship_ship ship USING(ship_id) JOIN loc_location system_location ON system_location.location_id=receipt.system_location_id WHERE receipt.command_id=%s",(cid,)).fetchone()
    return ShipPlacementResult(str(pub),str(row[0]),str(row[1]),row[2],row[3],replayed)

def place_ship_command(c:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,campaign_public_id:str,ship_public_id:str,system_public_id:str)->ShipPlacementResult:
 with c.transaction():
  old=c.execute("SELECT command_id,public_id,command_type,command_status FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(initiator_reference,idempotency_key)).fetchone()
  if old:
   if old[2:]!=('place_ship','completed'):raise RuntimeError('Idempotency key belongs to another command')
   return _load_place(c,old[0],old[1],True)
  state=c.execute("SELECT ship.ship_id,ship.name,ship.current_location_id,ship.concurrency_version,system.location_id FROM camp_campaign campaign JOIN ship_ship ship USING(campaign_id) JOIN loc_location system ON system.campaign_id=campaign.campaign_id JOIN loc_star_system star ON star.location_id=system.location_id WHERE campaign.public_id=%s AND campaign.owner_reference=%s AND ship.public_id=%s AND system.public_id=%s AND ship.lifecycle_status='active' AND NOT EXISTS(SELECT 1 FROM journey_journey journey WHERE journey.ship_id=ship.ship_id AND journey.journey_status IN('ready','underway')) FOR UPDATE OF ship",(campaign_public_id,initiator_reference,ship_public_id,system_public_id)).fetchone()
  if not state:raise ValueError('Ship and system are not available for placement')
  cid,pub=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('place_ship',%s,%s) RETURNING command_id,public_id",(initiator_reference,idempotency_key)).fetchone()
  c.execute("UPDATE ship_ship SET current_location_id=%s,concurrency_version=concurrency_version+1 WHERE ship_id=%s",(state[4],state[0]))
  crew=c.execute("SELECT actor_id FROM ship_crew_assignment WHERE ship_id=%s AND duty_status='active'",(state[0],)).fetchall()
  for (actor_id,) in crew:
   c.execute("UPDATE loc_actor_position SET position_status='departed',ended_at=clock_timestamp() WHERE campaign_id=(SELECT campaign_id FROM ship_ship WHERE ship_id=%s) AND actor_id=%s AND position_status='current'",(state[0],actor_id))
   c.execute("INSERT INTO loc_actor_position(campaign_id,actor_id,location_id,source_command_id) SELECT campaign_id,%s,%s,%s FROM ship_ship WHERE ship_id=%s",(actor_id,state[4],cid,state[0]))
  c.execute("INSERT INTO cmd_ship_placement_receipt VALUES(%s,(SELECT campaign_id FROM ship_ship WHERE ship_id=%s),%s,%s,%s,%s,%s)",(cid,state[0],state[0],state[4],state[2],state[3],state[3]+1))
  c.execute("INSERT INTO cmd_domain_event(command_id,event_order,event_type) VALUES(%s,1,'ship_placed')",(cid,));c.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(cid,))
  return _load_place(c,cid,pub,False)

def _load_plan(c,cid,pub,replayed):
 row=c.execute("SELECT journey.public_id,ship.public_id,origin.name,destination.name,receipt.distance_parsecs,receipt.jump_number,receipt.fuel_quantity,receipt.crew_count FROM cmd_jump_journey_planning_receipt receipt JOIN journey_journey journey ON journey.journey_id=receipt.journey_id JOIN ship_ship ship ON ship.ship_id=receipt.ship_id JOIN loc_location origin ON origin.location_id=receipt.origin_location_id JOIN loc_location destination ON destination.location_id=receipt.destination_location_id WHERE receipt.command_id=%s",(cid,)).fetchone()
 return JumpPlanningResult(str(pub),str(row[0]),str(row[1]),row[2],row[3],row[4],row[5],row[6],row[7],replayed)

def plan_jump_journey_command(c:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,campaign_public_id:str,ship_public_id:str,destination_system_public_id:str,journey_name:str)->JumpPlanningResult:
 name=journey_name.strip()
 if not name:raise ValueError('Journey name cannot be blank')
 with c.transaction():
  old=c.execute("SELECT command_id,public_id,command_type,command_status FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(initiator_reference,idempotency_key)).fetchone()
  if old:
   if old[2:]!=('plan_jump_journey','completed'):raise RuntimeError('Idempotency key belongs to another command')
   return _load_plan(c,old[0],old[1],True)
  state=c.execute("""SELECT campaign.campaign_id,ship.ship_id,ship.current_location_id,class.hull_tons,class.jump_rating,
  origin.hex_column,origin.hex_row,destination.location_id,destination.hex_column,destination.hex_row,
  fuel.current_quantity,item.item_instance_id
  FROM camp_campaign campaign JOIN ship_ship ship USING(campaign_id) JOIN ship_class class ON class.ship_class_rule_id=ship.ship_class_rule_id
  JOIN inv_item_instance item ON item.item_instance_id=ship.inventory_item_instance_id
  JOIN loc_star_system origin ON origin.location_id=ship.current_location_id
  JOIN loc_location destination_location ON destination_location.campaign_id=campaign.campaign_id
  JOIN loc_star_system destination ON destination.location_id=destination_location.location_id
  JOIN ship_resource fuel ON fuel.ship_id=ship.ship_id AND fuel.resource_type_code='refined_fuel'
  WHERE campaign.public_id=%s AND campaign.owner_reference=%s AND ship.public_id=%s AND destination_location.public_id=%s
  AND ship.lifecycle_status='active' AND NOT EXISTS(SELECT 1 FROM journey_journey active WHERE active.ship_id=ship.ship_id AND active.journey_status IN('ready','underway'))
  FOR UPDATE OF ship,fuel""",(campaign_public_id,initiator_reference,ship_public_id,destination_system_public_id)).fetchone()
  if not state:raise ValueError('Ship must be placed at a system and available for travel')
  if state[2]==state[7]:raise ValueError('Destination must differ from the current system')
  distance=_distance(state[5],state[6],state[8],state[9])
  if distance>state[4]:raise ValueError(f'Destination is {distance} parsecs away; ship is Jump-{state[4]}')
  fuel=(Decimal(state[3])*Decimal(distance)/Decimal(10)).quantize(Decimal('0.001')).normalize()
  if Decimal(state[10])<fuel:raise ValueError(f'Jump requires {fuel:f} tons of refined fuel; only {state[10]} available')
  cid,pub=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('plan_jump_journey',%s,%s) RETURNING command_id,public_id",(initiator_reference,idempotency_key)).fetchone()
  jid,jpub=c.execute("INSERT INTO journey_journey(campaign_id,journey_kind,name,ship_id,conveyance_item_instance_id) VALUES(%s,'jump',%s,%s,%s) RETURNING journey_id,public_id",(state[0],name,state[1],state[11])).fetchone()
  leg=c.execute("INSERT INTO journey_leg(journey_id,campaign_id,leg_order,origin_location_id,destination_location_id,travel_mode,distance_value,distance_unit) VALUES(%s,%s,1,%s,%s,'jump',%s,'parsec') RETURNING journey_leg_id",(jid,state[0],state[2],state[7],distance)).fetchone()[0]
  c.execute("INSERT INTO journey_ship_resource_plan(journey_leg_id,campaign_id,ship_id,resource_type_code,planned_quantity,plan_status) VALUES(%s,%s,%s,'refined_fuel',%s,'reserved')",(leg,state[0],state[1],fuel))
  crew=0
  for assignment,actor in c.execute("SELECT crew_assignment_id,actor_id FROM ship_crew_assignment WHERE ship_id=%s AND duty_status='active' ORDER BY crew_assignment_id",(state[1],)).fetchall():
   participant=c.execute("INSERT INTO journey_participant(journey_id,campaign_id,actor_id,participant_role) VALUES(%s,%s,%s,'crew') RETURNING journey_participant_id",(jid,state[0],actor)).fetchone()[0]
   c.execute("INSERT INTO journey_ship_crew_commitment(journey_participant_id,journey_id,campaign_id,ship_id,crew_assignment_id) VALUES(%s,%s,%s,%s,%s)",(participant,jid,state[0],state[1],assignment));crew+=1
  c.execute("INSERT INTO cmd_jump_journey_planning_receipt VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",(cid,state[0],jid,leg,state[1],state[2],state[7],distance,state[4],fuel,crew))
  c.execute("INSERT INTO cmd_domain_event(command_id,event_order,event_type) VALUES(%s,1,'jump_journey_planned')",(cid,));c.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(cid,))
  return _load_plan(c,cid,pub,False)

@dataclass(frozen=True)
class JumpCancellationResult:
 command_public_id:str;journey_public_id:str;journey_name:str
 ship_name:str;released_resource_plans:int;relieved_crew:int;replayed:bool

def _load_cancel(c,cid,pub,replayed):
 row=c.execute("SELECT journey.public_id,journey.name,ship.name,receipt.released_resource_plans,receipt.relieved_crew_commitments FROM cmd_jump_journey_cancellation_receipt receipt JOIN journey_journey journey ON journey.journey_id=receipt.journey_id JOIN ship_ship ship ON ship.ship_id=receipt.ship_id WHERE receipt.command_id=%s",(cid,)).fetchone()
 return JumpCancellationResult(str(pub),str(row[0]),row[1],row[2],row[3],row[4],replayed)

def cancel_jump_journey_command(c:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,journey_public_id:str)->JumpCancellationResult:
 """Stand down a drafted jump order.

 Only a journey still in 'planning' can be cancelled: once the drive has
 been resolved the outcome stands, so a resolved misjump cannot be dodged
 by cancelling. Fuel was only reserved, never spent — the reservation is
 released and the crew commitments are relieved.
 """
 with c.transaction():
  old=c.execute("SELECT command_id,public_id,command_type,command_status FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(initiator_reference,idempotency_key)).fetchone()
  if old:
   if old[2:]!=('cancel_jump_journey','completed'):raise RuntimeError('Idempotency key belongs to another command')
   return _load_cancel(c,old[0],old[1],True)
  state=c.execute("""SELECT journey.journey_id,journey.campaign_id,journey.ship_id,journey.journey_status,journey.concurrency_version
  FROM journey_journey journey JOIN camp_campaign campaign USING(campaign_id)
  WHERE journey.public_id=%s AND campaign.owner_reference=%s AND campaign.campaign_status='active'
  FOR UPDATE OF journey""",(journey_public_id,initiator_reference)).fetchone()
  if not state:raise ValueError('Journey is absent or not controlled by this player')
  if state[3]!='planning':raise ValueError(f"Only a jump order still in planning can be stood down; this one is {state[3]}")
  cid,pub=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('cancel_jump_journey',%s,%s) RETURNING command_id,public_id",(initiator_reference,idempotency_key)).fetchone()
  released=c.execute("""UPDATE journey_ship_resource_plan SET plan_status='released'
  WHERE plan_status IN ('planned','reserved') AND journey_leg_id IN
  (SELECT journey_leg_id FROM journey_leg WHERE journey_id=%s)""",(state[0],)).rowcount
  relieved=c.execute("""UPDATE journey_ship_crew_commitment SET commitment_status='relieved',ended_at=clock_timestamp()
  WHERE journey_id=%s AND commitment_status='assigned'""",(state[0],)).rowcount
  c.execute("UPDATE journey_journey SET journey_status='cancelled',ended_at=clock_timestamp(),concurrency_version=concurrency_version+1 WHERE journey_id=%s",(state[0],))
  c.execute("INSERT INTO cmd_jump_journey_cancellation_receipt VALUES(%s,%s,%s,%s,'planning',%s,%s)",(cid,state[1],state[0],state[2],released,relieved))
  c.execute("INSERT INTO cmd_domain_event(command_id,event_order,event_type) VALUES(%s,1,'jump_journey_cancelled')",(cid,))
  c.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(cid,))
  return _load_cancel(c,cid,pub,False)
