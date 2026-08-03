"""Atomic departure and arrival transitions for spacecraft journey legs."""
from dataclasses import dataclass
import psycopg
@dataclass(frozen=True)
class SpacecraftLegExecutionResult:
 command_public_id:str;journey_public_id:str;leg_order:int;status:str;duration_seconds:int;clock_day:int;clock_second:int;journey_completed:bool;replayed:bool
def _load(c,cid,pub,replayed,complete):
 table='cmd_spacecraft_leg_complete_receipt' if complete else 'cmd_spacecraft_leg_start_receipt';r=c.execute(f"SELECT j.public_id,l.leg_order,e.execution_status,e.duration_seconds,COALESCE(e.arrival_day,e.departure_day),COALESCE(e.arrival_second,e.departure_second),j.journey_status='completed' FROM {table} x JOIN journey_leg_execution e USING(journey_leg_id) JOIN journey_leg l USING(journey_leg_id) JOIN journey_journey j USING(journey_id) WHERE x.command_id=%s",(cid,)).fetchone();return SpacecraftLegExecutionResult(str(pub),str(r[0]),r[1],r[2],r[3],r[4],r[5],r[6],replayed)
def start_spacecraft_journey_leg_command(c:psycopg.Connection,*,referee_reference:str,idempotency_key:str,journey_public_id:str,leg_order:int)->SpacecraftLegExecutionResult:
 with c.transaction():
  old=c.execute("SELECT command_id,public_id,command_type,command_status FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(referee_reference,idempotency_key)).fetchone()
  if old:
   if old[2:]!=('start_spacecraft_journey_leg','completed'):raise RuntimeError('Idempotency key belongs to another command')
   return _load(c,old[0],old[1],True,False)
  s=c.execute("SELECT j.journey_id,j.campaign_id,j.ship_id,l.journey_leg_id,l.travel_mode,l.planned_duration_seconds,clock.day_number,clock.second_of_day FROM journey_journey j JOIN journey_leg l ON l.journey_id=j.journey_id AND l.campaign_id=j.campaign_id JOIN camp_campaign camp ON camp.campaign_id=j.campaign_id JOIN camp_clock clock ON clock.campaign_id=j.campaign_id WHERE j.public_id=%s AND l.leg_order=%s AND camp.owner_reference=%s AND j.journey_status='ready' AND l.leg_status IN('planned','committed') AND j.ship_id IS NOT NULL FOR UPDATE OF j,l,clock",(journey_public_id,leg_order,referee_reference)).fetchone()
  if not s:raise ValueError('Ready spacecraft journey leg does not exist')
  if s[4]=='jump':
   jump=c.execute("SELECT a.duration_hours FROM journey_jump_attempt a JOIN journey_navigation_solution n ON n.navigation_solution_id=a.navigation_solution_id AND n.journey_leg_id=a.journey_leg_id AND n.succeeded WHERE a.journey_leg_id=%s",(s[3],)).fetchone()
   if not jump:raise ValueError('Jump departure requires a resolved attempt and successful route')
   duration=jump[0]*3600
  else:
   if s[5] is None:raise ValueError('Normal-space leg requires planned duration')
   duration=s[5]
  plans=c.execute("SELECT journey_ship_resource_plan_id,resource_type_code,planned_quantity FROM journey_ship_resource_plan WHERE journey_leg_id=%s AND ship_id=%s AND campaign_id=%s AND plan_status='reserved' ORDER BY journey_ship_resource_plan_id FOR UPDATE",(s[3],s[2],s[1])).fetchall();cid,pub=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('start_spacecraft_journey_leg',%s,%s) RETURNING command_id,public_id",(referee_reference,idempotency_key)).fetchone()
  for plan,resource,quantity in plans:
   movement=c.execute("INSERT INTO ship_resource_movement(ship_id,campaign_id,resource_type_code,quantity_delta,balance_after,movement_kind,source_command_id) VALUES(%s,%s,%s,-%s,0,'consume',%s) RETURNING resource_movement_id",(s[2],s[1],resource,quantity,cid)).fetchone()[0];c.execute("INSERT INTO journey_ship_resource_use VALUES(%s,%s,%s,%s,%s)",(plan,movement,s[2],s[1],quantity));c.execute("UPDATE journey_ship_resource_plan SET plan_status='consumed' WHERE journey_ship_resource_plan_id=%s",(plan,))
  c.execute("UPDATE journey_journey SET journey_status='underway',current_leg_order=%s,started_at=COALESCE(started_at,clock_timestamp()) WHERE journey_id=%s",(leg_order,s[0]));c.execute("UPDATE journey_leg SET leg_status='underway',started_at=clock_timestamp() WHERE journey_leg_id=%s",(s[3],));c.execute("INSERT INTO journey_leg_execution VALUES(%s,%s,%s,'underway',%s,%s,%s,NULL,NULL,%s,NULL)",(s[3],s[1],s[2],duration,s[6],s[7],cid));order=c.execute("SELECT COALESCE(max(progress_order),0)+1 FROM journey_progress WHERE journey_id=%s",(s[0],)).fetchone()[0];c.execute("INSERT INTO journey_progress(journey_id,journey_leg_id,campaign_id,progress_order,progress_kind,elapsed_seconds,command_id) VALUES(%s,%s,%s,%s,'departed',0,%s)",(s[0],s[3],s[1],order,cid));c.execute("INSERT INTO cmd_spacecraft_leg_start_receipt VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",(cid,s[3],s[1],s[2],duration,len(plans),s[6],s[7]));c.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(cid,));return _load(c,cid,pub,False,False)
def complete_spacecraft_journey_leg_command(c:psycopg.Connection,*,referee_reference:str,idempotency_key:str,journey_public_id:str,leg_order:int)->SpacecraftLegExecutionResult:
 with c.transaction():
  old=c.execute("SELECT command_id,public_id,command_type,command_status FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(referee_reference,idempotency_key)).fetchone()
  if old:
   if old[2:]!=('complete_spacecraft_journey_leg','completed'):raise RuntimeError('Idempotency key belongs to another command')
   return _load(c,old[0],old[1],True,True)
  s=c.execute("SELECT j.journey_id,j.campaign_id,j.ship_id,l.journey_leg_id,l.destination_location_id,e.duration_seconds,clock.day_number,clock.second_of_day,l.travel_mode FROM journey_journey j JOIN journey_leg l ON l.journey_id=j.journey_id AND l.campaign_id=j.campaign_id JOIN journey_leg_execution e ON e.journey_leg_id=l.journey_leg_id AND e.campaign_id=l.campaign_id JOIN camp_campaign camp ON camp.campaign_id=j.campaign_id JOIN camp_clock clock ON clock.campaign_id=j.campaign_id WHERE j.public_id=%s AND l.leg_order=%s AND camp.owner_reference=%s AND j.journey_status='underway' AND l.leg_status='underway' AND e.execution_status='underway' FOR UPDATE OF j,l,e,clock",(journey_public_id,leg_order,referee_reference)).fetchone()
  if not s:raise ValueError('Underway spacecraft journey leg does not exist')
  attempt=c.execute("SELECT jump_outcome FROM journey_jump_attempt WHERE journey_leg_id=%s",(s[3],)).fetchone() if s[8]=='jump' else None
  misjump=bool(attempt and attempt[0]=='misjump')
  total=s[7]+s[5];after_day=s[6]+total//86400;after_second=total%86400
  final=c.execute("SELECT NOT EXISTS(SELECT 1 FROM journey_leg WHERE journey_id=%s AND leg_order>%s AND leg_status NOT IN('skipped','completed'))",(s[0],leg_order)).fetchone()[0]
  cid,pub=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('complete_spacecraft_journey_leg',%s,%s) RETURNING command_id,public_id",(referee_reference,idempotency_key)).fetchone()
  c.execute("UPDATE camp_clock SET day_number=%s,second_of_day=%s,concurrency_version=concurrency_version+1,advanced_at=clock_timestamp() WHERE campaign_id=%s",(after_day,after_second,s[1]));c.execute("INSERT INTO camp_clock_change(campaign_id,command_id,day_number_before,second_of_day_before,day_number_after,second_of_day_after,reason) VALUES(%s,%s,%s,%s,%s,%s,%s)",(s[1],cid,s[6],s[7],after_day,after_second,'misjump completed' if misjump else 'spacecraft journey leg completed'))
  c.execute("UPDATE ship_ship SET current_location_id=%s,concurrency_version=concurrency_version+1 WHERE ship_id=%s",(None if misjump else s[4],s[2]));c.execute("UPDATE journey_leg SET leg_status=%s,ended_at=clock_timestamp() WHERE journey_leg_id=%s",('failed' if misjump else 'completed',s[3]));c.execute("UPDATE journey_leg_execution SET execution_status='completed',arrival_day=%s,arrival_second=%s,complete_command_id=%s WHERE journey_leg_id=%s",(after_day,after_second,cid,s[3]))
  actors=c.execute("SELECT actor_id FROM journey_participant WHERE journey_id=%s AND commitment_status IN('planned','committed')",(s[0],)).fetchall()
  for (actor_id,) in actors:
   c.execute("UPDATE loc_actor_position SET position_status='departed',ended_at=clock_timestamp() WHERE campaign_id=%s AND actor_id=%s AND position_status='current'",(s[1],actor_id))
   if not misjump:c.execute("INSERT INTO loc_actor_position(campaign_id,actor_id,location_id,source_command_id) VALUES(%s,%s,%s,%s)",(s[1],actor_id,s[4],cid))
  order=c.execute("SELECT COALESCE(max(progress_order),0)+1 FROM journey_progress WHERE journey_id=%s",(s[0],)).fetchone()[0];c.execute("INSERT INTO journey_progress(journey_id,journey_leg_id,campaign_id,progress_order,progress_kind,elapsed_seconds,location_id,command_id) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",(s[0],s[3],s[1],order,'diverted' if misjump else 'arrived',s[5],None if misjump else s[4],cid))
  if misjump:c.execute("UPDATE journey_journey SET journey_status='failed',ended_at=clock_timestamp() WHERE journey_id=%s",(s[0],))
  elif final:c.execute("UPDATE journey_journey SET journey_status='completed',ended_at=clock_timestamp() WHERE journey_id=%s",(s[0],));c.execute("UPDATE journey_participant SET commitment_status='completed',released_at=clock_timestamp() WHERE journey_id=%s AND commitment_status IN('planned','committed')",(s[0],));c.execute("UPDATE journey_passage SET passage_status='completed' WHERE journey_id=%s AND passage_status IN('booked','boarded')",(s[0],))
  else:c.execute("UPDATE journey_journey SET current_leg_order=%s WHERE journey_id=%s",(leg_order+1,s[0],));c.execute("UPDATE journey_leg SET leg_status='committed' WHERE journey_id=%s AND leg_order=%s AND leg_status='planned'",(s[0],leg_order+1))
  c.execute("INSERT INTO cmd_spacecraft_leg_complete_receipt VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",(cid,s[3],s[1],s[2],s[6],s[7],after_day,after_second,final and not misjump));c.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(cid,));return _load(c,cid,pub,False,True)
