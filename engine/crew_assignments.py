"""Authoritative assignment of campaign actors to vacant ship stations."""
from dataclasses import dataclass
import psycopg
@dataclass(frozen=True)
class CrewAssignmentResult:
 command_public_id:str;actor_public_id:str;ship_public_id:str;position_name:str;assignment_id:int;replayed:bool
def _load(c,cid,pub,replayed):
 r=c.execute("""SELECT actor.public_id,ship.public_id,definition.position_name,receipt.crew_assignment_id FROM cmd_ship_crew_assignment_receipt receipt JOIN actor_actor actor USING(actor_id) JOIN ship_ship ship USING(ship_id) JOIN ship_crew_position position USING(ship_crew_position_id) JOIN ship_crew_position_definition definition ON definition.crew_position_rule_id=position.crew_position_rule_id WHERE receipt.command_id=%s""",(cid,)).fetchone();return CrewAssignmentResult(str(pub),str(r[0]),str(r[1]),r[2],r[3],replayed)
def assign_ship_crew_command(c:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,campaign_public_id:str,actor_public_id:str,ship_public_id:str,ship_crew_position_id:int)->CrewAssignmentResult:
 with c.transaction():
  old=c.execute("SELECT command_id,public_id,command_type,command_status FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(initiator_reference,idempotency_key)).fetchone()
  if old:
   if old[2:]!=('assign_ship_crew','completed'):raise RuntimeError('Idempotency key belongs to another command')
   return _load(c,old[0],old[1],True)
  s=c.execute("""SELECT campaign.campaign_id,actor.actor_id,ship.ship_id,position.ship_crew_position_id,definition.position_name FROM camp_campaign campaign JOIN actor_actor actor USING(campaign_id) JOIN ship_ship ship USING(campaign_id) JOIN ship_crew_position position ON position.ship_id=ship.ship_id AND position.ship_crew_position_id=%s JOIN ship_crew_position_definition definition ON definition.crew_position_rule_id=position.crew_position_rule_id WHERE campaign.public_id=%s AND campaign.owner_reference=%s AND actor.public_id=%s AND ship.public_id=%s AND position.position_status='available' FOR UPDATE OF actor,ship,position""",(ship_crew_position_id,campaign_public_id,initiator_reference,actor_public_id,ship_public_id)).fetchone()
  if not s:raise ValueError('Actor or vacant ship position is unavailable')
  if c.execute("SELECT 1 FROM ship_crew_assignment WHERE ship_crew_position_id=%s AND duty_status='active'",(s[3],)).fetchone():raise ValueError('Ship position is already assigned')
  if c.execute("SELECT 1 FROM ship_crew_assignment WHERE actor_id=%s AND ship_id=%s AND duty_status='active'",(s[1],s[2])).fetchone():raise ValueError('Actor already holds a position aboard this ship')
  cid,pub=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('assign_ship_crew',%s,%s) RETURNING command_id,public_id",(initiator_reference,idempotency_key)).fetchone()
  assignment=c.execute("INSERT INTO ship_crew_assignment(ship_crew_position_id,ship_id,campaign_id,actor_id,source_command_id) VALUES(%s,%s,%s,%s,%s) RETURNING crew_assignment_id",(s[3],s[2],s[0],s[1],cid)).fetchone()[0]
  c.execute("INSERT INTO cmd_ship_crew_assignment_receipt VALUES(%s,%s,%s,%s,%s,%s)",(cid,s[0],s[1],s[2],s[3],assignment));c.execute("INSERT INTO cmd_domain_event(command_id,event_order,event_type) VALUES(%s,1,'ship_crew_assigned')",(cid,));c.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(cid,));return _load(c,cid,pub,False)
