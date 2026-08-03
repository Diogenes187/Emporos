"""Leadership Coordinating Effort pools and allocations."""
from dataclasses import dataclass
import psycopg
from engine.tasks import resolve_actor_task_command
@dataclass(frozen=True)
class CoordinationResult:
 command_public_id:str; coordination_public_id:str; goal_reference:str; total_points:int; remaining_points:int; replayed:bool
@dataclass(frozen=True)
class AllocationResult:
 command_public_id:str; allocation_public_id:str; recipient_actor_public_id:str; points:int; remaining_points:int; replayed:bool
def _coord(c,cid,pub,replayed):
 r=c.execute("SELECT x.public_id,x.goal_reference,x.pool_points_total,x.pool_points_remaining FROM cmd_leadership_coordination_receipt q JOIN camp_leadership_coordination x USING(coordination_id) WHERE q.command_id=%s",(cid,)).fetchone();return CoordinationResult(str(pub),str(r[0]),r[1],r[2],r[3],replayed)
def begin_leadership_coordination_command(connection:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,leader_actor_public_id:str,goal_reference:str,characteristic_rule_code:str,random_source=None)->CoordinationResult:
 if not goal_reference.strip():raise ValueError('Leadership coordination requires a common goal')
 with connection.transaction():
  old=connection.execute("SELECT command_id,public_id,command_type,command_status FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(initiator_reference,idempotency_key)).fetchone()
  if old:
   if old[2:]!=('begin_leadership_coordination','completed'):raise RuntimeError('Idempotency key belongs to another command')
   return _coord(connection,old[0],old[1],True)
  leader=connection.execute("SELECT actor_id,campaign_id FROM actor_actor WHERE public_id=%s AND controller_reference=%s FOR UPDATE",(leader_actor_public_id,initiator_reference)).fetchone()
  if not leader:raise ValueError('Controlled leader not found')
  task=resolve_actor_task_command(connection,initiator_reference=initiator_reference,idempotency_key=idempotency_key+'-task',actor_public_id=leader_actor_public_id,characteristic_rule_code=characteristic_rule_code,skill_rule_code='skill.leadership',difficulty_rule_code='difficulty.average',random_source=random_source);task_id=connection.execute("SELECT command_id FROM cmd_command WHERE public_id=%s",(task.command_public_id,)).fetchone()[0];points=max(1,task.effect)
  cid,pub=connection.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('begin_leadership_coordination',%s,%s) RETURNING command_id,public_id",(initiator_reference,idempotency_key)).fetchone();coord_id=connection.execute("""INSERT INTO camp_leadership_coordination(campaign_id,leader_actor_id,goal_reference,pool_points_total,pool_points_remaining,coordination_status,source_command_id) VALUES(%s,%s,%s,%s,%s,'active',%s) RETURNING coordination_id""",(leader[1],leader[0],goal_reference.strip(),points,points,cid)).fetchone()[0];connection.execute("INSERT INTO cmd_leadership_coordination_receipt VALUES(%s,%s,%s,%s,%s,%s)",(cid,coord_id,task_id,leader[0],task.effect,points));connection.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(cid,));return _coord(connection,cid,pub,False)
def allocate_leadership_coordination_command(connection:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,coordination_public_id:str,recipient_actor_public_id:str,points:int)->AllocationResult:
 if points<=0:raise ValueError('Leadership allocation points must be positive')
 with connection.transaction():
  old=connection.execute("SELECT command_id,public_id,command_type,command_status FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(initiator_reference,idempotency_key)).fetchone()
  if old:
   if old[2:]!=('allocate_leadership_coordination','completed'):raise RuntimeError('Idempotency key belongs to another command')
   r=connection.execute("""SELECT a.public_id,actor.public_id,a.points,c.pool_points_remaining FROM cmd_leadership_coordination_allocation_receipt q JOIN camp_leadership_coordination_allocation a USING(allocation_id) JOIN camp_leadership_coordination c USING(coordination_id) JOIN actor_actor actor ON actor.actor_id=a.recipient_actor_id WHERE q.command_id=%s""",(old[0],)).fetchone();return AllocationResult(str(old[1]),str(r[0]),str(r[1]),r[2],r[3],True)
  state=connection.execute("""SELECT c.coordination_id,c.campaign_id,c.pool_points_remaining,c.leader_actor_id FROM camp_leadership_coordination c JOIN actor_actor leader ON leader.actor_id=c.leader_actor_id WHERE c.public_id=%s AND c.coordination_status='active' AND leader.controller_reference=%s FOR UPDATE OF c""",(coordination_public_id,initiator_reference)).fetchone();recipient=connection.execute("SELECT actor_id,campaign_id FROM actor_actor WHERE public_id=%s",(recipient_actor_public_id,)).fetchone()
  if not state or not recipient or recipient[1]!=state[1]:raise ValueError('Active coordination and same-campaign recipient required')
  if points>state[2]:raise ValueError('Leadership allocation exceeds remaining pool')
  cid,pub=connection.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('allocate_leadership_coordination',%s,%s) RETURNING command_id,public_id",(initiator_reference,idempotency_key)).fetchone();aid,apub=connection.execute("INSERT INTO camp_leadership_coordination_allocation(coordination_id,recipient_actor_id,points) VALUES(%s,%s,%s) RETURNING allocation_id,public_id",(state[0],recipient[0],points)).fetchone();after=state[2]-points;connection.execute("UPDATE camp_leadership_coordination SET pool_points_remaining=%s,coordination_status=%s WHERE coordination_id=%s",(after,'allocated' if after==0 else 'active',state[0]));connection.execute("INSERT INTO cmd_leadership_coordination_allocation_receipt VALUES(%s,%s,%s,%s,%s,%s,%s)",(cid,aid,state[0],recipient[0],points,state[2],after));connection.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(cid,));return AllocationResult(str(pub),str(apub),recipient_actor_public_id,points,after,False)
