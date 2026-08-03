"""Task-backed, immutable Navigation solutions for journey legs."""
from dataclasses import dataclass
import psycopg
from engine.tasks import resolve_actor_task_command

@dataclass(frozen=True)
class NavigationResult:
    command_public_id:str;solution_public_id:str;journey_public_id:str;leg_order:int;actor_public_id:str;operation_kind:str;check_total:int;effect:int;succeeded:bool;replayed:bool

def resolve_navigation_command(c:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,journey_public_id:str,leg_order:int,actor_public_id:str,operation_kind:str,characteristic_rule_code:str,difficulty_rule_code:str,random_source=None)->NavigationResult:
 if operation_kind not in ('post_jump_fix','normal_course','jump_route'):raise ValueError('Unknown Navigation operation')
 with c.transaction():
  old=c.execute("SELECT command_id,public_id,command_type,command_status FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(initiator_reference,idempotency_key)).fetchone()
  if old:
   if old[2:]!=('resolve_navigation','completed'):raise RuntimeError('Idempotency key belongs to another command')
   r=c.execute("SELECT s.public_id,j.public_id,l.leg_order,a.public_id,s.operation_kind,s.check_total,s.effect,s.succeeded FROM cmd_navigation_receipt x JOIN journey_navigation_solution s USING(navigation_solution_id) JOIN journey_leg l ON l.journey_leg_id=s.journey_leg_id JOIN journey_journey j ON j.journey_id=l.journey_id JOIN actor_actor a ON a.actor_id=s.navigator_actor_id WHERE x.command_id=%s",(old[0],)).fetchone();return NavigationResult(str(old[1]),str(r[0]),str(r[1]),r[2],str(r[3]),r[4],r[5],r[6],r[7],True)
  state=c.execute("SELECT l.journey_leg_id,l.campaign_id,l.travel_mode,a.actor_id,l.leg_status FROM journey_journey j JOIN journey_leg l USING(journey_id) JOIN actor_actor a ON a.campaign_id=l.campaign_id WHERE j.public_id=%s AND l.leg_order=%s AND a.public_id=%s AND a.controller_reference=%s FOR UPDATE OF l,a",(journey_public_id,leg_order,actor_public_id,initiator_reference)).fetchone()
  if not state:raise ValueError('Navigation context is not legal')
  if operation_kind=='jump_route' and state[2]!='jump':raise ValueError('Jump routes require a Jump journey leg')
  if operation_kind=='normal_course' and state[2]=='jump':raise ValueError('Normal-space courses cannot target a Jump leg')
  if operation_kind in ('jump_route','normal_course') and state[4] not in ('planned','committed'):raise ValueError('Courses must be plotted before travel begins')
  if operation_kind=='post_jump_fix' and (state[2]!='jump' or state[4]!='completed'):raise ValueError('Post-Jump position fixing requires a completed Jump leg')
  task=resolve_actor_task_command(c,initiator_reference=initiator_reference,idempotency_key=f'navigation:{idempotency_key}',actor_public_id=actor_public_id,characteristic_rule_code=characteristic_rule_code,skill_rule_code='skill.navigation',difficulty_rule_code=difficulty_rule_code,random_source=random_source)
  task_id=c.execute("SELECT command_id FROM cmd_command WHERE public_id=%s",(task.command_public_id,)).fetchone()[0]
  cid,pub=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('resolve_navigation',%s,%s) RETURNING command_id,public_id",(initiator_reference,idempotency_key)).fetchone()
  sid,spub=c.execute("INSERT INTO journey_navigation_solution(journey_leg_id,campaign_id,navigator_actor_id,operation_kind,task_command_id,check_total,effect,succeeded,source_command_id) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING navigation_solution_id,public_id",(state[0],state[1],state[3],operation_kind,task_id,task.total,task.effect,task.succeeded,cid)).fetchone()
  c.execute("INSERT INTO cmd_navigation_receipt VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",(cid,sid,state[0],state[3],operation_kind,task_id,task.total,task.effect,task.succeeded));c.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(cid,))
  return NavigationResult(str(pub),str(spub),journey_public_id,leg_order,actor_public_id,operation_kind,task.total,task.effect,task.succeeded,False)
