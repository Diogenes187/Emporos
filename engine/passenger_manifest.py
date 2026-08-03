"""Finalize the relational accommodation and steward manifest before departure."""
from dataclasses import dataclass
import psycopg
@dataclass(frozen=True)
class PassengerManifestResult:
 command_public_id:str;journey_public_id:str;ship_public_id:str;passenger_count:int;staterooms:int;low_berths:int;steward_quanta:int;required_quanta:int;replayed:bool
def _load(c,cid,pub,replayed):
 r=c.execute("SELECT journey.public_id,ship.public_id,receipt.passenger_count,receipt.stateroom_units_used,receipt.low_berths_used,receipt.steward_level_quanta,receipt.steward_quanta_required FROM cmd_passenger_manifest_receipt receipt JOIN journey_journey journey USING(journey_id) JOIN ship_ship ship USING(ship_id) WHERE receipt.command_id=%s",(cid,)).fetchone();return PassengerManifestResult(str(pub),str(r[0]),str(r[1]),r[2],r[3],r[4],r[5],r[6],replayed)
def finalize_passenger_manifest_command(c:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,journey_public_id:str)->PassengerManifestResult:
 with c.transaction():
  old=c.execute("SELECT command_id,public_id,command_type,command_status FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(initiator_reference,idempotency_key)).fetchone()
  if old:
   if old[2:]!=('finalize_passenger_manifest','completed'):raise RuntimeError('Idempotency key belongs to another command')
   return _load(c,old[0],old[1],True)
  s=c.execute("""SELECT journey.campaign_id,journey.journey_id,journey.ship_id,ship.public_id,
 count(*) FILTER(WHERE passage.passage_class='high'),count(*) FILTER(WHERE passage.passage_class='middle'),count(*) FILTER(WHERE passage.passage_class='low'),
 count(DISTINCT accommodation.unit_identifier) FILTER(WHERE accommodation.accommodation_kind='stateroom'),count(DISTINCT accommodation.unit_identifier) FILTER(WHERE accommodation.accommodation_kind='low-berth'),
 COALESCE((SELECT sum(skill.skill_level+1) FROM ship_crew_assignment assignment JOIN ship_crew_position position USING(ship_crew_position_id,ship_id,campaign_id) JOIN ship_crew_position_definition definition USING(crew_position_rule_id) JOIN actor_skill skill ON skill.actor_id=assignment.actor_id AND skill.skill_rule_id=definition.governing_skill_rule_id WHERE assignment.ship_id=journey.ship_id AND assignment.duty_status='active' AND definition.position_code='steward'),0)
 FROM journey_journey journey JOIN camp_campaign campaign USING(campaign_id) JOIN ship_ship ship USING(ship_id) JOIN journey_passage passage USING(journey_id,campaign_id) JOIN journey_active_passage_accommodation accommodation USING(journey_passage_id,campaign_id,journey_id)
 WHERE journey.public_id=%s AND campaign.owner_reference=%s AND journey.journey_status='planning' AND passage.passage_status='booked' AND NOT EXISTS(SELECT 1 FROM journey_passage_manifest_receipt manifest WHERE manifest.journey_id=journey.journey_id)
 GROUP BY journey.campaign_id,journey.journey_id,journey.ship_id,ship.public_id FOR UPDATE OF journey,ship""",(journey_public_id,initiator_reference)).fetchone()
  if not s:raise ValueError('A planning journey with assigned, booked passengers is required')
  required=(s[4]+1)//2+(s[5]+4)//5
  if s[9]<required:raise ValueError(f'Passenger manifest requires {required} steward skill quanta; ship provides {s[9]}')
  cid,pub=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('finalize_passenger_manifest',%s,%s) RETURNING command_id,public_id",(initiator_reference,idempotency_key)).fetchone();count=s[4]+s[5]+s[6]
  c.execute("INSERT INTO journey_passage_manifest_receipt(journey_id,campaign_id,ship_id,high_passengers,middle_passengers,low_passengers,stateroom_units_used,low_berths_used,steward_level_quanta,steward_quanta_required,source_command_id) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",(s[1],s[0],s[2],s[4],s[5],s[6],s[7],s[8],s[9],required,cid));c.execute("INSERT INTO cmd_passenger_manifest_receipt VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",(cid,s[0],s[1],s[2],count,s[7],s[8],s[9],required));c.execute("INSERT INTO cmd_domain_event(command_id,event_order,event_type) VALUES(%s,1,'passenger_manifest_finalized')",(cid,));c.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(cid,));return _load(c,cid,pub,False)
