"""Simultaneous freight and passenger availability for a commercial route."""
from dataclasses import dataclass
import random
import psycopg
@dataclass(frozen=True)
class RouteRevenueResult:
 command_public_id:str;cycle_public_id:str;ship_public_id:str;origin_name:str;destination_name:str;freight_tons:int;high_passengers:int;middle_passengers:int;low_passengers:int;replayed:bool
def _load(c,cid,pub,replayed):
 r=c.execute("""SELECT cycle.public_id,ship.public_id,origin.name,destination.name,
 max(draw.available_quantity) FILTER(WHERE draw.traffic_kind='freight_tons'),max(draw.available_quantity) FILTER(WHERE draw.traffic_kind='high_passengers'),max(draw.available_quantity) FILTER(WHERE draw.traffic_kind='middle_passengers'),max(draw.available_quantity) FILTER(WHERE draw.traffic_kind='low_passengers')
 FROM cmd_route_revenue_availability_receipt receipt JOIN journey_revenue_availability_cycle cycle USING(revenue_availability_cycle_id) JOIN ship_ship ship USING(ship_id) JOIN loc_location origin ON origin.location_id=cycle.origin_location_id JOIN loc_location destination ON destination.location_id=cycle.destination_location_id JOIN journey_revenue_availability_draw draw USING(revenue_availability_cycle_id) WHERE receipt.command_id=%s GROUP BY cycle.public_id,ship.public_id,origin.name,destination.name""",(cid,)).fetchone();return RouteRevenueResult(str(pub),str(r[0]),str(r[1]),r[2],r[3],r[4],r[5],r[6],r[7],replayed)
def open_route_revenue_command(c:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,campaign_public_id:str,ship_public_id:str,destination_system_public_id:str,random_source=None)->RouteRevenueResult:
 rng=random_source or random.SystemRandom()
 with c.transaction():
  old=c.execute("SELECT command_id,public_id,command_type,command_status FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(initiator_reference,idempotency_key)).fetchone()
  if old:
   if old[2:]!=('open_route_revenue','completed'):raise RuntimeError('Idempotency key belongs to another command')
   return _load(c,old[0],old[1],True)
  s=c.execute("""SELECT campaign.campaign_id,ship.ship_id,origin_system.location_id,destination_system.location_id,origin_world.location_id,destination_world.location_id,origin_world.name,destination_world.name,origin_profile.starport_code,clock.day_number
 FROM camp_campaign campaign JOIN camp_clock clock USING(campaign_id) JOIN ship_ship ship USING(campaign_id)
 JOIN loc_location origin_system ON origin_system.location_id=ship.current_location_id JOIN loc_star_system origin_star ON origin_star.location_id=origin_system.location_id
 JOIN loc_location destination_system ON destination_system.public_id=%s JOIN loc_star_system destination_star ON destination_star.location_id=destination_system.location_id AND destination_star.campaign_id=campaign.campaign_id
 JOIN LATERAL(SELECT world.location_id,world.name,profile.starport_code FROM loc_celestial_body body JOIN loc_location world ON world.location_id=body.location_id JOIN loc_world_profile profile ON profile.location_id=world.location_id AND profile.profile_status='current' WHERE body.system_location_id=origin_system.location_id ORDER BY body.orbit_order NULLS LAST,body.location_id LIMIT 1) origin_world ON true
 JOIN LATERAL(SELECT world.location_id,world.name FROM loc_celestial_body body JOIN loc_location world ON world.location_id=body.location_id JOIN loc_world_profile profile ON profile.location_id=world.location_id AND profile.profile_status='current' WHERE body.system_location_id=destination_system.location_id ORDER BY body.orbit_order NULLS LAST,body.location_id LIMIT 1) destination_world ON true
 JOIN loc_world_profile origin_profile ON origin_profile.location_id=origin_world.location_id AND origin_profile.profile_status='current'
 WHERE campaign.public_id=%s AND campaign.owner_reference=%s AND ship.public_id=%s AND origin_system.location_id<>destination_system.location_id FOR UPDATE OF ship,clock""",(destination_system_public_id,campaign_public_id,initiator_reference,ship_public_id)).fetchone()
  if not s:raise ValueError('Ship must be at a charted world and destination must be another charted system')
  prior=c.execute("SELECT available_day,refresh_number FROM journey_revenue_availability_cycle WHERE campaign_id=%s AND origin_location_id=%s AND destination_location_id=%s ORDER BY refresh_number DESC LIMIT 1",(s[0],s[2],s[3])).fetchone()
  if prior and s[9]<prior[0]+3:raise ValueError(f'Route opportunities refresh on campaign day {prior[0]+3}')
  refresh=1 if not prior else prior[1]+1
  cid,pub=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('open_route_revenue',%s,%s) RETURNING command_id,public_id",(initiator_reference,idempotency_key)).fetchone()
  cycle,cycle_pub=c.execute("INSERT INTO journey_revenue_availability_cycle(campaign_id,origin_location_id,destination_location_id,starport_code,available_day,refresh_number,source_command_id) VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING revenue_availability_cycle_id,public_id",(s[0],s[2],s[3],s[8],s[9],refresh,cid)).fetchone()
  rules=c.execute("SELECT traffic_kind,dice_count,die_sides,flat_modifier,multiplier FROM rule_starport_traffic_expression WHERE starport_code=%s ORDER BY traffic_kind",(s[8],)).fetchall()
  for kind,dice,sides,modifier,multiplier in rules:
   natural=sum(rng.randint(1,sides) for _ in range(dice)) if dice else 0;available=max(0,natural+modifier)*multiplier
   c.execute("INSERT INTO journey_revenue_availability_draw VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",(cycle,s[0],kind,dice,sides,modifier,multiplier,natural,available))
  c.execute("INSERT INTO journey_revenue_availability_receipt VALUES(%s,%s,4,clock_timestamp())",(cycle,s[0]));c.execute("INSERT INTO cmd_route_revenue_availability_receipt VALUES(%s,%s,%s,%s,%s,%s)",(cid,s[0],s[1],cycle,s[2],s[3]));c.execute("INSERT INTO cmd_domain_event(command_id,event_order,event_type) VALUES(%s,1,'route_revenue_opened')",(cid,));c.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(cid,));return _load(c,cid,pub,False)
