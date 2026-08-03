"""Book actual passenger actors into available ship accommodations."""
from dataclasses import dataclass
import secrets
import psycopg
@dataclass(frozen=True)
class PassengerBookingResult:
 command_public_id:str;journey_public_id:str;ship_public_id:str;passage_class:str;passenger_count:int;total_fare:int;replayed:bool
def _load(c,cid,pub,replayed):
 r=c.execute("""SELECT journey.public_id,ship.public_id,receipt.passage_class,receipt.passenger_count,receipt.total_fare_minor FROM cmd_passenger_booking_receipt receipt JOIN journey_journey journey ON journey.journey_id=receipt.journey_id JOIN ship_ship ship ON ship.ship_id=receipt.ship_id WHERE receipt.command_id=%s""",(cid,)).fetchone();return PassengerBookingResult(str(pub),str(r[0]),str(r[1]),r[2],r[3],r[4],replayed)
def book_route_passengers_command(c:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,cycle_public_id:str,journey_public_id:str,passage_class:str,passenger_count:int,random_source=None)->PassengerBookingResult:
 if passage_class not in ('high','middle','low'):raise ValueError('Only high, middle, or low passage may be booked from route availability')
 if passenger_count<=0:raise ValueError('Passenger count must be positive')
 traffic=passage_class+'_passengers'
 with c.transaction():
  old=c.execute("SELECT command_id,public_id,command_type,command_status FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(initiator_reference,idempotency_key)).fetchone()
  if old:
   if old[2:]!=('book_route_passengers','completed'):raise RuntimeError('Idempotency key belongs to another command')
   return _load(c,old[0],old[1],True)
  s=c.execute("""SELECT cycle.campaign_id,cycle.revenue_availability_cycle_id,journey.journey_id,leg.journey_leg_id,journey.ship_id,ship.public_id,class.ship_class_rule_id,draw.available_quantity,passage.price_credits,passage.baggage_allowance_kg,
 COALESCE((SELECT characteristic_value::integer FROM ship_class_characteristic WHERE ship_class_rule_id=class.ship_class_rule_id AND characteristic_code='staterooms'),0),COALESCE((SELECT characteristic_value::integer FROM ship_class_characteristic WHERE ship_class_rule_id=class.ship_class_rule_id AND characteristic_code='low_berths'),0)
 FROM journey_revenue_availability_cycle cycle JOIN camp_campaign campaign USING(campaign_id) JOIN journey_journey journey ON journey.public_id=%s AND journey.campaign_id=cycle.campaign_id JOIN journey_leg leg ON leg.journey_id=journey.journey_id AND leg.leg_order=1 AND leg.origin_location_id=cycle.origin_location_id AND leg.destination_location_id=cycle.destination_location_id JOIN ship_ship ship ON ship.ship_id=journey.ship_id JOIN ship_class class ON class.ship_class_rule_id=ship.ship_class_rule_id JOIN journey_revenue_availability_draw draw ON draw.revenue_availability_cycle_id=cycle.revenue_availability_cycle_id AND draw.traffic_kind=%s JOIN rule_passage_class passage ON passage.passage_class=%s WHERE cycle.public_id=%s AND campaign.owner_reference=%s AND cycle.cycle_status='finalized' AND journey.journey_status IN('planning','ready') FOR UPDATE OF cycle,journey,leg,ship""",(journey_public_id,traffic,passage_class,cycle_public_id,initiator_reference)).fetchone()
  if not s:raise ValueError('Passenger opportunity and planned journey do not share the same route and ship')
  accepted=c.execute("SELECT count(*) FROM journey_passage_availability_receipt WHERE revenue_availability_cycle_id=%s AND traffic_kind=%s",(s[1],traffic)).fetchone()[0]
  if accepted+passenger_count>s[7]:raise ValueError(f'Only {s[7]-accepted} {passage_class} passengers remain available')
  existing=c.execute("SELECT count(*) FILTER(WHERE passage_class IN('high','middle') AND passage_status IN('booked','boarded')),count(*) FILTER(WHERE passage_class='low' AND passage_status IN('booked','boarded')) FROM journey_passage WHERE journey_id=%s",(s[2],)).fetchone()
  if passage_class=='low':capacity=s[11]-existing[1]
  else:
   crew=c.execute("SELECT count(*) FROM ship_crew_assignment WHERE ship_id=%s AND duty_status='active'",(s[4],)).fetchone()[0];capacity=s[10]-((crew+1)//2)-existing[0]
  if passenger_count>capacity:raise ValueError(f'Only {max(0,capacity)} suitable passenger berths remain')
  cid,pub=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('book_route_passengers',%s,%s) RETURNING command_id,public_id",(initiator_reference,idempotency_key)).fetchone();total=s[8]*passenger_count;c.execute("INSERT INTO cmd_passenger_booking_receipt VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",(cid,s[0],s[2],s[4],s[1],passage_class,passenger_count,total));rng=random_source or secrets.SystemRandom();draw_order=0
  for order in range(1,passenger_count+1):
   ordinal=accepted+order;actor=c.execute("INSERT INTO actor_actor(campaign_id,name,controller_reference) VALUES(%s,%s,'emporos-passenger') RETURNING actor_id",(s[0],f'{passage_class.title()} Passenger {ordinal}')).fetchone()[0]
   for characteristic in ('strength','dexterity','endurance','intelligence','education','social-standing'):
    dice=[rng.randint(1,6),rng.randint(1,6)]
    for die in dice:draw_order+=1;c.execute("INSERT INTO cmd_random_draw(command_id,draw_group,draw_order,die_sides,result) VALUES(%s,'passenger_creation',%s,6,%s)",(cid,draw_order,die))
    c.execute("INSERT INTO actor_characteristic(actor_id,characteristic_rule_id,maximum_value,current_value) SELECT %s,rule_id,%s,%s FROM rule_rule WHERE rule_code=%s",(actor,sum(dice),sum(dice),'characteristic.'+characteristic))
   c.execute("INSERT INTO journey_participant(journey_id,campaign_id,actor_id,participant_role) VALUES(%s,%s,%s,'passenger')",(s[2],s[0],actor));passage=c.execute("INSERT INTO journey_passage(journey_id,campaign_id,actor_id,passage_class,fare_minor,baggage_mass_kg) VALUES(%s,%s,%s,%s,%s,%s) RETURNING journey_passage_id",(s[2],s[0],actor,passage_class,s[8],s[9])).fetchone()[0];c.execute("INSERT INTO journey_passage_availability_receipt VALUES(%s,%s,%s,%s,%s,%s,%s,clock_timestamp(),%s)",(passage,s[0],s[2],s[3],s[1],traffic,ordinal,cid));c.execute("INSERT INTO cmd_passenger_booking_line VALUES(%s,%s,%s,%s,%s)",(cid,order,s[0],actor,passage))
  c.execute("INSERT INTO cmd_domain_event(command_id,event_order,event_type) VALUES(%s,1,'route_passengers_booked')",(cid,));c.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(cid,));return _load(c,cid,pub,False)
